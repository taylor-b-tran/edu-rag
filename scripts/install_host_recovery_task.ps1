<#
.SYNOPSIS
Install or update an at-logon recovery task for the current Windows user.
.EXAMPLE
.\scripts\install_host_recovery_task.ps1 -WhatIf
.EXAMPLE
.\scripts\install_host_recovery_task.ps1
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$RepositoryRoot,
    [string]$DockerContext = 'desktop-linux',
    [ValidatePattern('^[a-zA-Z0-9 ._-]+$')][string]$TaskName = 'Paedia Host Recovery'
)
$ErrorActionPreference = 'Stop'

# Same reason as recover_host.ps1: $PSScriptRoot is empty in some invocation
# forms, and a parameter default that reads it fails before the script runs.
$scriptRoot = $PSScriptRoot
if (-not $scriptRoot) { $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $scriptRoot) { throw 'Could not determine the directory this script lives in.' }
if (-not $RepositoryRoot) { $RepositoryRoot = Split-Path -Parent $scriptRoot }

$root = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$script = Join-Path $root 'scripts\recover_host.ps1'
if (-not (Test-Path -LiteralPath $script)) { throw 'Recovery script was not found in the selected repository.' }
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
# Encode a PowerShell command rather than embedding unescaped paths inside
# Task Scheduler's command-line parser. No credentials are stored in the task.
$command = "& '$($script.Replace("'", "''"))' -RepositoryRoot '$($root.Replace("'", "''"))' -DockerContext '$($DockerContext.Replace("'", "''"))' -StartDockerDesktop"
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
$powershell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$action = New-ScheduledTaskAction -Execute $powershell -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand $encoded" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.User.Value
$principal = New-ScheduledTaskPrincipal -UserId $identity.User.Value -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 35) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
$description = 'After Windows sign-in, start Docker Desktop if needed; wait for Tailscale; restore Paedia API/UI bindings and verify host HTTP health. Logs: %LOCALAPPDATA%\Paedia\HostRecovery. Sign-in remains required.'
Write-Host "Task: $TaskName; account: $($identity.Name); trigger: this user's Windows sign-in; privileges: limited."
Write-Host "Repository: $root; Docker context: $DockerContext."
Write-Host 'This does not enable automatic Windows sign-in or provide unattended pre-login recovery.'
if ($PSCmdlet.ShouldProcess($TaskName, 'Register or update the Paedia host recovery task')) {
    $null = Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description $description -Force
    Write-Host "Installed. To run now: Start-ScheduledTask -TaskName '$TaskName'"
}
