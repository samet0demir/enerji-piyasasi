param(
    [ValidateSet('Start', 'Stop')][string]$Action = 'Start',
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path $PSScriptRoot -Parent
$runDir = Join-Path $projectDir '.local'
$stateFile = Join-Path $runDir 'processes.json'
$appUrl = 'http://localhost:5173'

function Get-OwnedProcess($entry) {
    $process = Get-Process -Id $entry.id -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().Ticks.ToString() -eq $entry.started) {
        return $process
    }
}

function Stop-OwnedProcesses($entries) {
    foreach ($entry in $entries) {
        $process = Get-OwnedProcess $entry
        if ($process) { Stop-Process -InputObject $process -Force }
    }
}

function Test-Ready {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:5001/api/health' -TimeoutSec 3
        $page = Invoke-WebRequest 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 3
        return $health.status -eq 'UP' -and $page.StatusCode -eq 200
    } catch { return $false }
}

$startedProcesses = @()
try {
    if (Test-Path -LiteralPath $stateFile) {
        $saved = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
        if ($Action -eq 'Start' -and @($saved | Where-Object { Get-OwnedProcess $_ }).Count -eq 2 -and (Test-Ready)) {
            Write-Host "Uygulama zaten acik: $appUrl"
            if (-not $NoBrowser) { Start-Process $appUrl }
            exit 0
        }
        Stop-OwnedProcesses $saved
        Remove-Item -LiteralPath $stateFile
    }
    if ($Action -eq 'Stop') {
        Write-Host 'Uygulama kapatildi.'
        exit 0
    }

    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodeCommand) { throw 'Node.js bulunamadi. Node.js kurup tekrar Baslat.bat dosyasini acin.' }
    foreach ($port in @(5001, 5173)) {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $port)
        try { $listener.Start() }
        catch { throw "$port portu baska bir uygulamada acik. Once o uygulamayi kapatin." }
        finally { $listener.Stop() }
    }
    foreach ($folder in @('backend', 'frontend')) {
        $dependency = if ($folder -eq 'backend') { 'node_modules/tsx/dist/cli.mjs' } else { 'node_modules/vite/bin/vite.js' }
        if (-not (Test-Path -LiteralPath (Join-Path (Join-Path $projectDir $folder) $dependency))) {
            Write-Host "$folder icin ilk kurulum yapiliyor..."
            Push-Location (Join-Path $projectDir $folder)
            try {
                & npm.cmd ci
                if ($LASTEXITCODE -ne 0) { throw "$folder kurulumu basarisiz." }
            } finally { Pop-Location }
        }
    }
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null

    # Use the configured development copy; create an isolated local copy if needed.
    $localDb = Join-Path $env:LOCALAPPDATA 'EnerjiPiyasasi/energy-dev.db'
    $envFile = Join-Path $projectDir 'backend/.env'
    if (Test-Path -LiteralPath $envFile) {
        $dbLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^DB_PATH=' } | Select-Object -Last 1
        if ($dbLine) {
            $configured = $dbLine.Substring(8).Trim().Trim('"').Trim("'")
            $candidate = if ([IO.Path]::IsPathRooted($configured)) { $configured } else { Join-Path $projectDir "backend/$configured" }
            $production = [IO.Path]::GetFullPath((Join-Path $projectDir 'backend/data/energy.db'))
            if ([IO.Path]::GetFullPath($candidate) -ne $production -and (Test-Path -LiteralPath $candidate)) {
                $localDb = $candidate
            }
        }
    }
    if (-not (Test-Path -LiteralPath $localDb)) {
        New-Item -ItemType Directory -Path (Split-Path $localDb -Parent) -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $projectDir 'backend/data/energy.db') -Destination $localDb
    }
    $env:DB_PATH = $localDb
    $env:PORT = '5001'
    Write-Host 'Enerji uygulamasi baslatiliyor...'
    $backend = Start-Process -FilePath $nodeCommand.Source -ArgumentList @('--import', 'tsx', 'src/index.ts') `
        -WorkingDirectory (Join-Path $projectDir 'backend') -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runDir 'backend.log') -RedirectStandardError (Join-Path $runDir 'backend-error.log')
    $startedProcesses += @{ id = $backend.Id; started = $backend.StartTime.ToUniversalTime().Ticks.ToString() }
    $frontend = Start-Process -FilePath $nodeCommand.Source `
        -ArgumentList @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort') `
        -WorkingDirectory (Join-Path $projectDir 'frontend') -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runDir 'frontend.log') -RedirectStandardError (Join-Path $runDir 'frontend-error.log')
    $startedProcesses += @{ id = $frontend.Id; started = $frontend.StartTime.ToUniversalTime().Ticks.ToString() }
    ConvertTo-Json -InputObject $startedProcesses | Set-Content -LiteralPath $stateFile -Encoding UTF8

    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if ($backend.HasExited -or $frontend.HasExited) { break }
        if (Test-Ready) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw "Uygulama acilamadi. Hata kayitlari: $runDir" }
    Write-Host "Hazir: $appUrl"
    Write-Host 'Kapatmak icin Durdur.bat dosyasina cift tiklayin.'
    if (-not $NoBrowser) { Start-Process $appUrl }
} catch {
    Stop-OwnedProcesses $startedProcesses
    if ($startedProcesses.Count -gt 0 -and (Test-Path -LiteralPath $stateFile)) {
        Remove-Item -LiteralPath $stateFile
    }
    Write-Host "Hata: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
