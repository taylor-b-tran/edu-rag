param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "SilentlyContinue"

function Convert-BytesToGB {
    param([Nullable[double]]$Bytes)
    if ($null -eq $Bytes) {
        return $null
    }
    return [Math]::Round($Bytes / 1GB, 2)
}

$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$computer = Get-CimInstance Win32_ComputerSystem | Select-Object -First 1
$os = Get-CimInstance Win32_OperatingSystem | Select-Object -First 1
$gpus = Get-CimInstance Win32_VideoController | ForEach-Object {
    [PSCustomObject]@{
        name = $_.Name
        adapter_ram_gb = Convert-BytesToGB $_.AdapterRAM
        driver_version = $_.DriverVersion
        video_processor = $_.VideoProcessor
    }
}

$nvidia = $null
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($null -eq $nvidiaSmi -and (Test-Path -LiteralPath "C:\Windows\System32\nvidia-smi.exe")) {
    $nvidiaSmi = Get-Item -LiteralPath "C:\Windows\System32\nvidia-smi.exe"
}
if ($null -ne $nvidiaSmi) {
    $nvidiaRaw = & $nvidiaSmi.Source --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader,nounits
    $cudaVersion = (& $nvidiaSmi.Source | Select-String -Pattern "CUDA Version" | ForEach-Object {
        if ($_.Line -match "CUDA Version:\s+([0-9.]+)") {
            $Matches[1]
        }
    } | Select-Object -First 1)
    $nvidia = @($nvidiaRaw | ForEach-Object {
        $parts = $_.Split(",").ForEach({ $_.Trim() })
        if ($parts.Count -ge 4) {
            [PSCustomObject]@{
                name = $parts[0]
                memory_total_mb = [int]$parts[1]
                memory_free_mb = [int]$parts[2]
                driver_version = $parts[3]
                cuda_version = $cudaVersion
            }
        }
    })
}

$docker = $null
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $docker = [PSCustomObject]@{
        version = (docker --version)
        compose_version = (docker compose version)
    }
}

$result = [PSCustomObject]@{
    checked_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    machine = [PSCustomObject]@{
        manufacturer = $computer.Manufacturer
        model = $computer.Model
        total_ram_gb = Convert-BytesToGB $computer.TotalPhysicalMemory
        os = $os.Caption
        os_version = $os.Version
    }
    cpu = [PSCustomObject]@{
        name = $cpu.Name
        physical_cores = $cpu.NumberOfCores
        logical_processors = $cpu.NumberOfLogicalProcessors
        max_clock_mhz = $cpu.MaxClockSpeed
    }
    gpu_windows = $gpus
    gpu_nvidia_smi = $nvidia
    docker = $docker
}

$json = $result | ConvertTo-Json -Depth 8

if ($OutputPath -ne "") {
    $parent = Split-Path -Parent $OutputPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $json | Set-Content -Path $OutputPath -Encoding UTF8
}

$json
