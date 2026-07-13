$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$srcDir = Join-Path $scriptDir "src"
$embedScript = Join-Path $scriptDir "sandbox.ipxe"
$outputFile = Join-Path $srcDir "bin-x86_64-efi\ipxe.efi"

if (-not (Test-Path $srcDir)) {
    Write-Host "Missing iPXE source directory: $srcDir" -ForegroundColor Yellow
    Write-Host "Clone iPXE first so that the src directory exists." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $embedScript)) {
    Write-Host "Missing embed script: $embedScript" -ForegroundColor Yellow
    exit 1
}

Push-Location $srcDir
try {
    Write-Host "Building ipxe.efi ..."
    & make "bin-x86_64-efi/ipxe.efi" "EMBED=$embedScript"

    if (-not (Test-Path $outputFile)) {
        throw "Build finished but output file was not created: $outputFile"
    }

    Write-Host ""
    Write-Host "Build complete:" -ForegroundColor Green
    Write-Host $outputFile
}
finally {
    Pop-Location
}
