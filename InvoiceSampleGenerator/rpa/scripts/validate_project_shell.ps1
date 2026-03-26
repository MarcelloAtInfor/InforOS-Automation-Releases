param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

$projectFile = Join-Path $ProjectRoot "project.json"
if (-not (Test-Path $projectFile)) {
    throw "Missing project.json at $projectFile"
}

$project = Get-Content -Raw $projectFile | ConvertFrom-Json
$failures = New-Object System.Collections.Generic.List[string]

$mainFile = Join-Path $ProjectRoot $project.main
if (-not (Test-Path $mainFile)) {
    $failures.Add("Main workflow missing: $mainFile")
}

foreach ($source in $project.sourceFiles) {
    $sourceFile = Join-Path $source.filePath $source.fileName
    if (-not (Test-Path $sourceFile)) {
        $failures.Add("Declared source file missing: $sourceFile")
        continue
    }

    try {
        [xml](Get-Content -Raw $sourceFile) | Out-Null
    } catch {
        $failures.Add("XAML parse failed: $sourceFile :: $($_.Exception.Message)")
    }
}

Get-ChildItem -Path (Join-Path $ProjectRoot "config") -Filter *.json -File | ForEach-Object {
    try {
        Get-Content -Raw $_.FullName | ConvertFrom-Json | Out-Null
    } catch {
        $failures.Add("JSON parse failed: $($_.FullName) :: $($_.Exception.Message)")
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    throw "Project shell validation failed with $($failures.Count) issue(s)."
}

Write-Host "Project shell validation passed."
Write-Host "Main workflow: $($project.main)"
Write-Host "Registered source files: $($project.sourceFiles.Count)"
