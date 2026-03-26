param(
    [Parameter(Mandatory = $true)][string]$RequestJsonPath,
    [string]$OutputFolder = "",
    [string]$PythonExe = "python",
    [string]$ResponseJsonPath = "",
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

if ([string]::IsNullOrWhiteSpace($ResponseJsonPath)) {
    $ResponseJsonPath = Join-Path ([System.IO.Path]::GetTempPath()) ("InvoiceSampleGenerator_response_" + [System.Guid]::NewGuid().ToString("N") + ".json")
}

$responseDirectory = Split-Path -Parent $ResponseJsonPath
if (-not [string]::IsNullOrWhiteSpace($responseDirectory)) {
    New-Item -ItemType Directory -Path $responseDirectory -Force | Out-Null
}

try {
    if (-not (Test-Path $rendererScript)) {
        throw "Renderer script not found at $rendererScript"
    }

    if (-not (Test-Path $RequestJsonPath)) {
        throw "Request JSON not found at $RequestJsonPath"
    }

    $resolvedRequestJsonPath = (Resolve-Path $RequestJsonPath).Path
    $arguments = @($rendererScript, "--request-json", $resolvedRequestJsonPath, "--response-json", $ResponseJsonPath)
    if (-not [string]::IsNullOrWhiteSpace($OutputFolder)) {
        $arguments += @("--output-folder", $OutputFolder)
    }

    Write-Host "Invoking renderer:"
    Write-Host "  Python: $PythonExe"
    Write-Host "  Script: $rendererScript"
    Write-Host "  Request: $resolvedRequestJsonPath"
    if (-not [string]::IsNullOrWhiteSpace($OutputFolder)) {
        Write-Host "  Output: $OutputFolder"
    }
    Write-Host "  Response: $ResponseJsonPath"

    & $PythonExe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Renderer returned exit code $LASTEXITCODE"
    }
}
catch {
    $resolvedOutputFolder = ""
    try {
        if (-not [string]::IsNullOrWhiteSpace($OutputFolder)) {
            $resolvedOutputFolder = [System.IO.Path]::GetFullPath($OutputFolder)
        }
        else {
            $request = Get-Content $resolvedRequestJsonPath -Raw | ConvertFrom-Json
            if ($request.outputFolder) {
                $resolvedOutputFolder = [System.IO.Path]::GetFullPath([string]$request.outputFolder)
            }
            else {
                $resolvedOutputFolder = Join-Path (Split-Path -Parent $resolvedRequestJsonPath) "output"
            }
        }
    }
    catch {
        $resolvedOutputFolder = ""
    }

    $failurePayload = [ordered]@{
        operationStatus = "FAILED"
        errorMessage = $_.Exception.Message
        requestJsonPath = $(if ([string]::IsNullOrWhiteSpace($resolvedRequestJsonPath)) { $RequestJsonPath } else { $resolvedRequestJsonPath })
        documentCount = 0
        documentMode = ""
        layoutVariant = ""
        resolvedOutputFolder = $resolvedOutputFolder
        manifestPath = ""
        registryPath = ""
        generatedFiles = @()
    }
    $failurePayload | ConvertTo-Json -Depth 4 | Set-Content -Path $ResponseJsonPath -Encoding UTF8
    throw
}
