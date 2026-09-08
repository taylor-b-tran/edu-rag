# Windows PowerShell 5.1 compatible. Native output is deliberately never logged:
# `docker compose config` and `docker inspect` may contain environment secrets.
Set-StrictMode -Version Latest

function Invoke-RecoveryNative {
    param([string]$Executable, [string[]]$Arguments, [int]$TimeoutSeconds = 30)
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $Executable
    # Windows CommandLineToArgvW quoting, including trailing backslashes.
    $start.Arguments = (($Arguments | ForEach-Object {
        '"' + ([regex]::Replace($_, '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
    }) -join ' ')
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $start
    try {
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill()
            throw "Native command timed out after $TimeoutSeconds seconds."
        }
        $process.WaitForExit()
        return [pscustomobject]@{ ExitCode = $process.ExitCode; Output = $stdout.Result }
    } finally {
        $process.Dispose()
    }
}

function Invoke-RecoveryDocker {
    param($Context, [string[]]$Arguments, [int]$TimeoutSeconds = 30)
    $result = Invoke-RecoveryNative $Context.Docker (@('--context', $Context.DockerContext) + $Arguments) $TimeoutSeconds
    if ($result.ExitCode -ne 0) {
        throw "Docker command failed (exit $($result.ExitCode)); inspect Docker Desktop locally."
    }
    return $result.Output
}

function Write-RecoveryLog {
    param($Context, [string]$Message)
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK'), $Message
    Add-Content -LiteralPath $Context.LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Wait-RecoveryCondition {
    param([scriptblock]$Condition, [int]$TimeoutSeconds, [int]$PollSeconds, [string]$Description)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        if (& $Condition) { return }
        if ([DateTime]::UtcNow -ge $deadline) { break }
        Start-Sleep -Seconds $PollSeconds
    } while ($true)
    throw "Timed out waiting for $Description."
}

function Test-RecoveryDocker {
    param($Context)
    try {
        $type = Invoke-RecoveryDocker $Context @('info', '--format', '{{.OSType}}') 10
        return $type.Trim() -eq 'linux'
    } catch { return $false }
}

function Test-RecoveryTailnetAddress {
    param($Context, [string]$Address)
    try {
        $result = Invoke-RecoveryNative $Context.Tailscale @('ip', '-4') 10
        if ($result.ExitCode -ne 0 -or $Address -notin ($result.Output -split '\s+')) { return $false }
        $assigned = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | Where-Object {
            $_.IPAddress -eq $Address -and $_.AddressState -eq 'Preferred'
        })
        return $assigned.Count -gt 0
    } catch { return $false }
}

function Get-RecoveryConfiguration {
    param($Context)
    $raw = Invoke-RecoveryDocker $Context ($Context.ComposeArguments + @('config', '--format', 'json'))
    try { $config = $raw | ConvertFrom-Json } catch { throw 'Cannot parse the Compose configuration.' }
    $expected = @{}
    foreach ($service in @('api', 'streamlit', 'postgres', 'chromadb', 'ollama')) {
        $definition = $config.services.PSObject.Properties[$service]
        if ($null -eq $definition) { throw "Compose service $service is missing." }
        $ports = @($definition.Value.ports)
        if ($ports.Count -ne 1) { throw "Expected exactly one published port for $service." }
        $port = $ports[0]
        if ($port.protocol -ne 'tcp') { throw "Expected a TCP port for $service." }
        if ($service -in @('api', 'streamlit')) {
            $bytes = $null
            $ip = $null
            if ([System.Net.IPAddress]::TryParse($port.host_ip, [ref]$ip)) { $bytes = $ip.GetAddressBytes() }
            if ($null -eq $bytes -or $bytes.Length -ne 4 -or $bytes[0] -ne 100 -or $bytes[1] -lt 64 -or $bytes[1] -gt 127) {
                throw "$service must bind only to a Tailscale IPv4 address (100.64.0.0/10)."
            }
        } elseif ($port.host_ip -ne '127.0.0.1') {
            throw "$service must remain bound to 127.0.0.1."
        }
        $expected[$service] = [pscustomobject]@{
            Address = [string]$port.host_ip
            Published = [string]$port.published
            Target = [string]$port.target + '/tcp'
        }
    }
    if ($expected.api.Address -ne $expected.streamlit.Address) { throw 'API and UI must share the same Tailscale address.' }
    if ($expected.api.Target -ne '5000/tcp' -or $expected.streamlit.Target -ne '8501/tcp') {
        throw 'Unexpected API/UI container port; update recovery health checks before continuing.'
    }
    return $expected
}

function Get-RecoveryContainer {
    param($Context, [string]$Service)
    $ids = (Invoke-RecoveryDocker $Context ($Context.ComposeArguments + @('ps', '--all', '--quiet', $Service))).Trim()
    if (-not $ids) { throw "$Service has no existing container; provision the stack before enabling recovery." }
    if (($ids -split '\s+').Count -ne 1) { throw "Expected one $Service container." }
    # Inspect only the fields needed for recovery, never container environment.
    $template = '{"Id":{{json .Id}},"State":{{json .State.Status}},"Ports":{{json .NetworkSettings.Ports}},"ConfiguredPorts":{{json .HostConfig.PortBindings}},"WorkingDir":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}}}'
    $raw = Invoke-RecoveryDocker $Context @('inspect', '--format', $template, $ids)
    try { $container = $raw | ConvertFrom-Json } catch { throw "Cannot inspect $Service." }
    if (-not $container.WorkingDir -or [System.IO.Path]::GetFullPath($container.WorkingDir).TrimEnd('\', '/') -ne $Context.RepositoryRoot.TrimEnd('\', '/')) {
        throw "$Service belongs to a different checkout; refusing to change it."
    }
    return $container
}

function Test-RecoveryPorts {
    param($Ports, $Expected)
    if ($null -eq $Ports) { return $false }
    $active = @($Ports.PSObject.Properties | Where-Object { $null -ne $_.Value -and @($_.Value).Count -gt 0 })
    if ($active.Count -ne 1 -or $active[0].Name -ne $Expected.Target) { return $false }
    $bindings = @($active[0].Value)
    return ($bindings.Count -eq 1 -and $bindings[0].HostIp -eq $Expected.Address -and [string]$bindings[0].HostPort -eq $Expected.Published)
}

function Test-RecoveryHttp {
    param([string]$Uri)
    $response = $null
    try {
        $request = [System.Net.HttpWebRequest]::Create($Uri)
        $request.Proxy = $null
        $request.Timeout = 5000
        $request.ReadWriteTimeout = 5000
        $request.AllowAutoRedirect = $false
        $response = $request.GetResponse()
        return [int]$response.StatusCode -eq 200
    } catch { return $false } finally {
        if ($null -ne $response) { $response.Dispose() }
    }
}

function Get-RecoveryHealthUri {
    param([string]$Service, $Expected)
    $path = if ($Service -eq 'api') { '/api/health' } else { '/_stcore/health' }
    return "http://$($Expected.Address):$($Expected.Published)$path"
}

function Invoke-RecoveryServices {
    param($Context, $Expected, [switch]$CheckOnly, [int]$HealthTimeoutSeconds = 180, [int]$PollSeconds = 5)
    # Read every container before any mutation, so a wrong checkout or missing
    # dependency cannot leave a partially changed stack.
    $containers = @{}
    foreach ($service in @('postgres', 'chromadb', 'ollama', 'api', 'streamlit')) {
        $containers[$service] = Get-RecoveryContainer $Context $service
    }
    foreach ($service in @('postgres', 'chromadb', 'ollama')) {
        $container = $containers[$service]
        if (-not (Test-RecoveryPorts $container.ConfiguredPorts $Expected[$service])) {
            throw "$service has an unsafe or unexpected configured binding; manual review is required."
        }
        if ($container.State -ne 'running') {
            if ($CheckOnly) { throw "$service is not running." }
            Write-RecoveryLog $Context "Starting existing $service container (preserving its image, GPU configuration and volumes)."
            $null = Invoke-RecoveryDocker $Context @('start', $container.Id) 60
            $container = Get-RecoveryContainer $Context $service
        }
        if (-not (Test-RecoveryPorts $container.Ports $Expected[$service])) {
            throw "$service has a missing or unexpected actual binding; manual review is required."
        }
    }
    foreach ($service in @('api', 'streamlit')) {
        $container = $containers[$service]
        $uri = Get-RecoveryHealthUri $service $Expected[$service]
        $repair = ($container.State -ne 'running' -or
            -not (Test-RecoveryPorts $container.ConfiguredPorts $Expected[$service]) -or
            -not (Test-RecoveryPorts $container.Ports $Expected[$service]))
        if ($CheckOnly) {
            if ($repair -or -not (Test-RecoveryHttp $uri)) { throw "$service failed actual binding/reachability checks." }
        } else {
            if (-not $repair) {
                # Give a normally starting container time to become reachable.
                # If Docker reports bindings but its host proxy is broken,
                # one controlled recreation is still needed.
                try {
                    Wait-RecoveryCondition { Test-RecoveryHttp $uri } $HealthTimeoutSeconds $PollSeconds "$service health"
                } catch { $repair = $true }
            }
            if ($repair) {
                Write-RecoveryLog $Context "Recreating $service to restore its Tailscale binding."
                $null = Invoke-RecoveryDocker $Context ($Context.ComposeArguments + @('up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--force-recreate', $service)) 120
            }
            Wait-RecoveryCondition {
                $current = Get-RecoveryContainer $Context $service
                $current.State -eq 'running' -and
                    (Test-RecoveryPorts $current.ConfiguredPorts $Expected[$service]) -and
                    (Test-RecoveryPorts $current.Ports $Expected[$service]) -and
                    (Test-RecoveryHttp $uri)
            } $HealthTimeoutSeconds $PollSeconds "$service actual binding and host HTTP health"
        }
        Write-RecoveryLog $Context "$service reachable: $uri (actual binding verified)."
    }
}

Export-ModuleMember -Function *-Recovery*
