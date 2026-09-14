<#
.SYNOPSIS
Check the recovery module's pure decisions without touching Docker, Tailscale or the stack.
.DESCRIPTION
Runs on Windows PowerShell 5.1, the engine the at-logon task uses, with no Pester
dependency. Exit code 0 when every check passes.
.EXAMPLE
powershell.exe -NoProfile -File .\scripts\test_host_recovery.ps1
#>
$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $scriptRoot) { $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition }
Import-Module (Join-Path $scriptRoot 'host_recovery.psm1') -Force

$script:failures = New-Object System.Collections.Generic.List[string]
$script:checks = 0
function Assert-Recovery([string]$Name, [bool]$Actual, [bool]$Expected) {
    $script:checks++
    if ($Actual -ne $Expected) {
        $script:failures.Add("${Name}: expected $Expected, got $Actual")
    } else {
        Write-Host "ok   $Name"
    }
}

# The API's own verdict on whether the worker that answered has its database.
Assert-Recovery 'health: connected is usable' (Test-RecoveryHealthBody '{"status":"ok","database":"connected"}') $true
Assert-Recovery 'health: a worker without Postgres is not usable' (Test-RecoveryHealthBody '{"status":"ok","database":"unavailable"}') $false
Assert-Recovery 'health: an API too old to report it is not trusted' (Test-RecoveryHealthBody '{"status":"ok"}') $false
Assert-Recovery 'health: a non-JSON body is not trusted' (Test-RecoveryHealthBody '<html>ok</html>') $false
Assert-Recovery 'health: an empty body is not trusted' (Test-RecoveryHealthBody '') $false

# Actual published ports, in the shape `docker inspect` returns them.
$expected = [pscustomobject]@{ Address = '100.64.0.10'; Published = '5000'; Target = '5000/tcp' }
function ConvertTo-RecoveryPorts([string]$Json) { return ($Json | ConvertFrom-Json) }
Assert-Recovery 'ports: the configured tailnet binding' (Test-RecoveryPorts (ConvertTo-RecoveryPorts '{"5000/tcp":[{"HostIp":"100.64.0.10","HostPort":"5000"}]}') $expected) $true
Assert-Recovery 'ports: no binding because Docker started before Tailscale' (Test-RecoveryPorts (ConvertTo-RecoveryPorts '{"5000/tcp":null}') $expected) $false
Assert-Recovery 'ports: bound to every interface' (Test-RecoveryPorts (ConvertTo-RecoveryPorts '{"5000/tcp":[{"HostIp":"0.0.0.0","HostPort":"5000"}]}') $expected) $false
Assert-Recovery 'ports: an extra loopback binding' (Test-RecoveryPorts (ConvertTo-RecoveryPorts '{"5000/tcp":[{"HostIp":"100.64.0.10","HostPort":"5000"},{"HostIp":"127.0.0.1","HostPort":"5000"}]}') $expected) $false
Assert-Recovery 'ports: the wrong published port' (Test-RecoveryPorts (ConvertTo-RecoveryPorts '{"5000/tcp":[{"HostIp":"100.64.0.10","HostPort":"5001"}]}') $expected) $false
Assert-Recovery 'ports: nothing inspected' (Test-RecoveryPorts $null $expected) $false

if ($script:failures.Count -gt 0) {
    $script:failures | ForEach-Object { Write-Host "FAIL $_" }
    exit 1
}
Write-Host "All $($script:checks) recovery checks passed."
exit 0
