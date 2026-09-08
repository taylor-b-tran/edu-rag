<#
.SYNOPSIS
Wait for Docker Desktop and Tailscale, then recover the existing Paedia stack.
.DESCRIPTION
Never provisions data, builds/pulls images, or recreates backing containers.
CheckOnly is read-only apart from local logs. StartDockerDesktop is intended
for the current user's at-logon task; Windows sign-in is still required.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot,
    [string]$DockerContext = 'desktop-linux',
    [ValidateRange(1, 1800)][int]$StartupTimeoutSeconds = 600,
    [ValidateRange(1, 600)][int]$HealthTimeoutSeconds = 180,
    [ValidateRange(1, 30)][int]$PollSeconds = 5,
    [string]$LogDirectory = (Join-Path $env:LOCALAPPDATA 'Paedia\HostRecovery'),
    [switch]$StartDockerDesktop,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'

# $PSScriptRoot is not populated in every invocation form - running this with
# powershell.exe -File left it empty and the script died on its own parameter
# default before doing anything. Resolved here instead, with MyInvocation as
# the fallback, so the script works however it is launched.
$scriptRoot = $PSScriptRoot
if (-not $scriptRoot) { $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $scriptRoot) { throw 'Could not determine the directory this script lives in.' }
if (-not $RepositoryRoot) { $RepositoryRoot = Split-Path -Parent $scriptRoot }

Import-Module (Join-Path $scriptRoot 'host_recovery.psm1') -Force
$lock = $null
$context = $null
try {
    $root = (Resolve-Path -LiteralPath $RepositoryRoot).Path
    $composeFile = Join-Path $root 'docker-compose.yml'
    if (-not (Test-Path -LiteralPath $composeFile)) { throw 'Repository has no docker-compose.yml.' }
    $null = New-Item -ItemType Directory -Path $LogDirectory -Force
    try {
        $lock = [System.IO.File]::Open((Join-Path $LogDirectory 'recovery.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch [System.IO.IOException] {
        Write-Host 'A host recovery process is already running; no second process was started.'
        exit 0
    }
    $docker = (Get-Command docker.exe -ErrorAction Stop).Source
    $tailscale = (Get-Command tailscale.exe -ErrorAction Stop).Source
    $context = [pscustomobject]@{
        RepositoryRoot = $root; DockerContext = $DockerContext
        Docker = $docker; Tailscale = $tailscale
        ComposeArguments = @('compose', '--project-directory', $root, '-f', $composeFile)
        LogPath = (Join-Path $LogDirectory ('recovery-{0}.log' -f (Get-Date -Format 'yyyy-MM-dd')))
    }
    Write-RecoveryLog $context "Starting host recovery (check only: $([bool]$CheckOnly)); repository $root; Docker context $DockerContext."
    # Do not allow a global DOCKER_HOST or a remote Docker context to direct
    # host recovery at another machine. Every Docker call uses this context.
    $rawContext = Invoke-RecoveryDocker $context @('context', 'inspect', $DockerContext, '--format', '{{json .Endpoints.docker.Host}}')
    $endpoint = $rawContext | ConvertFrom-Json
    if ($endpoint -notlike 'npipe://*') { throw 'Recovery requires a local Windows Docker Desktop named-pipe context.' }
    if (-not $CheckOnly -and $StartDockerDesktop -and -not (Test-RecoveryDocker $context)) {
        if (-not (Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue)) {
            $desktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
            if (-not (Test-Path -LiteralPath $desktop)) { throw 'Docker Desktop executable was not found.' }
            Write-RecoveryLog $context 'Starting Docker Desktop in the signed-in user session.'
            Start-Process -FilePath $desktop -WindowStyle Hidden
        }
    }
    Write-RecoveryLog $context 'Waiting for the Docker Linux engine.'
    Wait-RecoveryCondition { Test-RecoveryDocker $context } $StartupTimeoutSeconds $PollSeconds 'Docker Linux engine'
    $expected = Get-RecoveryConfiguration $context
    $address = $expected.api.Address
    Write-RecoveryLog $context "Waiting for Tailscale to own $address and for Windows to assign it."
    Wait-RecoveryCondition { Test-RecoveryTailnetAddress $context $address } $StartupTimeoutSeconds $PollSeconds 'the configured Tailscale IPv4 address'
    Invoke-RecoveryServices $context $expected -CheckOnly:$CheckOnly -HealthTimeoutSeconds $HealthTimeoutSeconds -PollSeconds $PollSeconds
    Write-RecoveryLog $context 'SUCCESS: API and UI are reachable from this host through the Tailscale address. A second-device check is still required after a physical reboot.'
    exit 0
} catch {
    # All native-command errors are deliberately sanitised by the module.
    $message = 'FAILED: ' + $_.Exception.Message
    if ($null -ne $context) { Write-RecoveryLog $context $message } else { Write-Host $message }
    exit 1
} finally {
    if ($null -ne $lock) { $lock.Dispose() }
}
