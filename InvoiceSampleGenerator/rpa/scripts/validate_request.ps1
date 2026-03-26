param(
    [Parameter(Mandatory = $true)][string]$RequestJsonPath,
    [string]$OutputFolder = "",
    [string]$PythonExe = "python",
    [string]$ValidationResultPath = "",
    [string]$RendererScript = ""
)

$ErrorActionPreference = "Stop"

# Resolve renderer script path
if ([string]::IsNullOrWhiteSpace($RendererScript)) {
    $shellProjectRoot = Split-Path -Parent $PSScriptRoot
    $invoiceProjectRoot = Split-Path -Parent (Split-Path -Parent $shellProjectRoot)
    $rendererScript = Join-Path $invoiceProjectRoot "scripts\render_invoice_batch.py"
} else {
    $rendererScript = $RendererScript
}
$resolvedRequestJsonPath = ""

if ([string]::IsNullOrWhiteSpace($ValidationResultPath)) {
    $ValidationResultPath = Join-Path ([System.IO.Path]::GetTempPath()) ("InvoiceSampleGenerator_validation_" + [System.Guid]::NewGuid().ToString("N") + ".txt")
}

$validationDirectory = Split-Path -Parent $ValidationResultPath
if (-not [string]::IsNullOrWhiteSpace($validationDirectory)) {
    New-Item -ItemType Directory -Path $validationDirectory -Force | Out-Null
}

try {
    if (-not (Test-Path $rendererScript)) {
        throw "Renderer script not found at $rendererScript"
    }

    if (-not (Test-Path $RequestJsonPath)) {
        throw "Request JSON not found at $RequestJsonPath"
    }

    $resolvedRequestJsonPath = (Resolve-Path $RequestJsonPath).Path
    $arguments = @($rendererScript, "--request-json", $resolvedRequestJsonPath, "--validate-only")
    if (-not [string]::IsNullOrWhiteSpace($OutputFolder)) {
        $arguments += @("--output-folder", $OutputFolder)
    }

    Write-Host "Validating request:"
    Write-Host "  Python: $PythonExe"
    Write-Host "  Script: $rendererScript"
    Write-Host "  Request: $resolvedRequestJsonPath"
    if (-not [string]::IsNullOrWhiteSpace($OutputFolder)) {
        Write-Host "  Output: $OutputFolder"
    }
    Write-Host "  Result: $ValidationResultPath"

    $validationOutput = & $PythonExe @arguments 2>&1
    $validationText = ($validationOutput | ForEach-Object { $_.ToString() }) -join [System.Environment]::NewLine
    if ([string]::IsNullOrWhiteSpace($validationText)) {
        $validationText = "Validation completed."
    }

    Set-Content -Path $ValidationResultPath -Value $validationText -Encoding UTF8

    if ($LASTEXITCODE -ne 0) {
        exit 1
    }

    exit 0
}
catch {
    $message = $_.Exception.Message
    if ([string]::IsNullOrWhiteSpace($message)) {
        $message = "Request validation failed."
    }
    Set-Content -Path $ValidationResultPath -Value $message -Encoding UTF8
    exit 1
}
