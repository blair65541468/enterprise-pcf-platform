[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Start", "Stop", "Status", "Logs", "Test")]
    [string]$Action,

    [string]$EnvFile
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $RepoRoot "docker-compose.openlca.yml"
if (-not $EnvFile) {
    $EnvFile = Join-Path $RepoRoot ".env.openlca.local"
}
$EnvFile = [System.IO.Path]::GetFullPath($EnvFile)

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing local configuration: $Path. Copy .env.openlca.example to .env.openlca.local first."
    }

    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }
        $separator = $trimmed.IndexOf("=")
        if ($separator -lt 1) {
            throw "Invalid dotenv entry in ${Path}: $line"
        }
        $name = $trimmed.Substring(0, $separator).Trim()
        $value = $trimmed.Substring($separator + 1).Trim()
        if (
            $value.Length -ge 2 -and
            (($value.StartsWith('"') -and $value.EndsWith('"')) -or
             ($value.StartsWith("'") -and $value.EndsWith("'")))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $existing = [Environment]::GetEnvironmentVariable($name, "Process")
        if ([string]::IsNullOrWhiteSpace($existing)) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

function Require-Value {
    param([string]$Name)

    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Required setting $Name is missing in $EnvFile."
    }
    return $value
}

function Assert-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker CLI is not installed or not available on PATH."
    }
    & docker info --format "{{.ServerVersion}}" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop Linux engine is not running. Start Docker Desktop and retry."
    }
}

function Assert-NoOpenLcaDesktop {
    $desktop = Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessName -match "^openlca" } |
        Select-Object -First 1
    if ($desktop) {
        throw "openLCA Desktop is running (PID $($desktop.Id)). Close it before mounting the workspace in gdt-server."
    }
}

function Assert-LocalConfiguration {
    $accepted = Require-Value "OPENLCA_LICENSE_ACCEPTED"
    if ($accepted.Trim().ToLowerInvariant() -ne "true") {
        throw "Set OPENLCA_LICENSE_ACCEPTED=true only after confirming the gdt-server and database licence conditions."
    }

    $workspaceText = Require-Value "OPENLCA_WORKSPACE_PATH"
    $databaseName = Require-Value "OPENLCA_DATABASE_NAME"
    $workspace = Resolve-Path -LiteralPath $workspaceText -ErrorAction Stop
    $databases = Join-Path $workspace.Path "databases"
    if (-not (Test-Path -LiteralPath $databases -PathType Container)) {
        throw "Workspace does not contain a databases directory: $databases"
    }
    $database = Join-Path $databases $databaseName
    if (-not (Test-Path -LiteralPath $database)) {
        $available = Get-ChildItem -LiteralPath $databases -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty Name
        $suffix = if ($available) { " Available databases: $($available -join ', ')." } else { "" }
        throw "Database '$databaseName' was not found under $databases.$suffix"
    }

    [Environment]::SetEnvironmentVariable(
        "OPENLCA_WORKSPACE_PATH",
        $workspace.Path,
        "Process"
    )
}

function Get-ComposeArguments {
    return @(
        "compose",
        "--env-file", $EnvFile,
        "-f", $ComposeFile
    )
}

function Invoke-Compose {
    param([string[]]$Arguments)

    $compose = Get-ComposeArguments
    & docker @compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed with exit code $LASTEXITCODE."
    }
}

function Get-OpenLcaUrl {
    $port = [Environment]::GetEnvironmentVariable("OPENLCA_HOST_PORT", "Process")
    if ([string]::IsNullOrWhiteSpace($port)) {
        $port = "8080"
    }
    if ($port -notmatch "^\d+$" -or [int]$port -lt 1 -or [int]$port -gt 65535) {
        throw "OPENLCA_HOST_PORT must be an integer from 1 to 65535."
    }
    return "http://127.0.0.1:$port"
}

function Add-LocalNoProxy {
    $items = @()
    if ($env:NO_PROXY) {
        $items += $env:NO_PROXY.Split(",") | ForEach-Object { $_.Trim() } |
            Where-Object { $_ }
    }
    $items += @("127.0.0.1", "localhost")
    $env:NO_PROXY = ($items | Select-Object -Unique) -join ","
}

function Wait-OpenLca {
    param([string]$Url)

    $timeoutText = [Environment]::GetEnvironmentVariable(
        "OPENLCA_TIMEOUT_SECONDS",
        "Process"
    )
    $timeout = 600
    if ($timeoutText) {
        if (-not [int]::TryParse($timeoutText, [ref]$timeout) -or $timeout -le 0) {
            throw "OPENLCA_TIMEOUT_SECONDS must be a positive integer."
        }
    }

    $deadline = [DateTime]::UtcNow.AddSeconds($timeout)
    do {
        try {
            $version = Invoke-RestMethod -Uri "$Url/api/version" -TimeoutSec 5
            Write-Host "openLCA REST is ready at $Url (version: $version)."
            return
        } catch {
            Start-Sleep -Seconds 2
        }
    } while ([DateTime]::UtcNow -lt $deadline)

    Write-Warning "openLCA did not become ready within $timeout seconds. Container logs follow."
    $compose = Get-ComposeArguments
    & docker @compose logs --tail 200 openlca
    throw "Timed out waiting for $Url/api/version."
}

Import-DotEnv -Path $EnvFile
Add-LocalNoProxy

switch ($Action) {
    "Start" {
        Assert-NoOpenLcaDesktop
        Assert-LocalConfiguration
        Assert-Docker
        Invoke-Compose -Arguments @("up", "--build", "-d", "openlca")
        Wait-OpenLca -Url (Get-OpenLcaUrl)
    }
    "Stop" {
        Assert-Docker
        Invoke-Compose -Arguments @("down")
    }
    "Status" {
        Assert-Docker
        Invoke-Compose -Arguments @("ps")
    }
    "Logs" {
        Assert-Docker
        Invoke-Compose -Arguments @("logs", "--tail", "200", "openlca")
    }
    "Test" {
        Assert-NoOpenLcaDesktop
        Assert-LocalConfiguration
        Assert-Docker
        $url = Get-OpenLcaUrl
        Wait-OpenLca -Url $url

        $caseFile = Require-Value "OPENLCA_TEST_CASE_FILE"
        if (-not [System.IO.Path]::IsPathRooted($caseFile)) {
            $caseFile = Join-Path $RepoRoot $caseFile
        }
        $caseFile = [System.IO.Path]::GetFullPath($caseFile)
        if (-not (Test-Path -LiteralPath $caseFile -PathType Leaf)) {
            throw "Integration test case does not exist: $caseFile"
        }

        $python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
            throw "Python virtual environment is missing: $python"
        }
        $env:OPENLCA_URL = $url
        $env:OPENLCA_TEST_CASE_FILE = $caseFile
        Push-Location $RepoRoot
        try {
            & $python -m pytest --run-openlca -m openlca_integration tests/test_openlca_integration.py -q
            if ($LASTEXITCODE -ne 0) {
                throw "Real openLCA integration tests failed with exit code $LASTEXITCODE."
            }
        } finally {
            Pop-Location
        }
    }
}
