$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Ffmpeg = Join-Path $ProjectRoot "vendor\ffmpeg\ffmpeg.exe"
$Ffprobe = Join-Path $ProjectRoot "vendor\ffmpeg\ffprobe.exe"
$Spec = Join-Path $ProjectRoot "MasVis-for-Windows.spec"

$ExpectedFfmpegSha256 = "72A489ECCD008C2EC2C0A5856C5C75BC3D8BBFA90166C4566865C246445E6AA3"
$ExpectedFfprobeSha256 = "19202B23C0043F15AD1B7BCE2344F406FD52BD6EFD8F995CE02E7392A1CEC52F"

function Get-Sha256Hex([string]$Path) {
    $Stream = [System.IO.File]::OpenRead($Path)
    try {
        $Hasher = [System.Security.Cryptography.SHA256]::Create()
        try { $Bytes = $Hasher.ComputeHash($Stream) }
        finally { $Hasher.Dispose() }
    }
    finally { $Stream.Dispose() }
    return ([System.BitConverter]::ToString($Bytes)).Replace("-", "")
}

if (-not (Test-Path $Python)) { throw "Project virtual environment not found: $Python" }
if (-not (Test-Path $Ffmpeg)) { throw "Bundled ffmpeg.exe not found. Run .\packaging\fetch_ffmpeg.ps1 first." }
if (-not (Test-Path $Ffprobe)) { throw "Bundled ffprobe.exe not found. Run .\packaging\fetch_ffmpeg.ps1 first." }

Write-Host "=== Packaging baseline ===" -ForegroundColor Cyan
& $Python -c "import sys, numpy, scipy, matplotlib, PIL, PySide6, PyInstaller; from PySide6.QtCore import qVersion; print('Python:', sys.version.split()[0]); print('NumPy:', numpy.__version__); print('SciPy:', scipy.__version__); print('Matplotlib:', matplotlib.__version__); print('Pillow:', PIL.__version__); print('PySide6:', PySide6.__version__); print('Qt:', qVersion()); print('PyInstaller:', PyInstaller.__version__)"

$VersionLine = (& $Ffmpeg -version 2>&1 | Select-Object -First 1).ToString()
if (-not $VersionLine.Contains("ffmpeg version 9.0.1-essentials_build-www.gyan.dev")) { throw "Unexpected FFmpeg vendor build: $VersionLine" }
if ((Get-Sha256Hex $Ffmpeg) -ne $ExpectedFfmpegSha256) { throw "ffmpeg.exe SHA256 mismatch." }
if ((Get-Sha256Hex $Ffprobe) -ne $ExpectedFfprobeSha256) { throw "ffprobe.exe SHA256 mismatch." }
Write-Host $VersionLine
Write-Host "FFmpeg vendor hashes: OK" -ForegroundColor Green

Write-Host ""
Write-Host "=== Python syntax gate ===" -ForegroundColor Cyan
& $Python -m py_compile app.py audio_loader.py runtime_ffmpeg.py dynamics_assessment.py dynamics_common.py dynamics_compare.py src\analysis.py src\output.py src\params.py src\utils.py
if ($LASTEXITCODE -ne 0) { throw "Python syntax gate failed." }
Write-Host "Syntax: OK" -ForegroundColor Green

Write-Host ""
Write-Host "=== License staging ===" -ForegroundColor Cyan
$LicenseStage = Join-Path $ProjectRoot "release-license-staging"
& $Python .\packaging\collect_licenses.py $LicenseStage
if ($LASTEXITCODE -ne 0) { throw "License collector reported missing required inputs." }

Write-Host ""
Write-Host "=== PyInstaller onedir build ===" -ForegroundColor Cyan
Remove-Item .\build -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\dist -Recurse -Force -ErrorAction SilentlyContinue
& $Python -m PyInstaller --clean --noconfirm $Spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$Dist = Join-Path $ProjectRoot "dist\MasVis-for-Windows"
$Exe = Join-Path $Dist "MasVis-for-Windows.exe"
if (-not (Test-Path $Exe)) { throw "Expected executable was not created: $Exe" }

Copy-Item .\LICENSE (Join-Path $Dist "LICENSE") -Force
Copy-Item .\README.md (Join-Path $Dist "README.md") -Force
Copy-Item .\THIRD_PARTY_NOTICES.md (Join-Path $Dist "THIRD_PARTY_NOTICES.md") -Force
if (Test-Path $LicenseStage) { Copy-Item $LicenseStage (Join-Path $Dist "THIRD-PARTY-LICENSES") -Recurse -Force }

$FfmpegTarget = Join-Path $Dist "THIRD-PARTY-LICENSES\FFmpeg-Gyan-9.0.1"
New-Item $FfmpegTarget -ItemType Directory -Force | Out-Null
if (Test-Path .\packaging\licenses\GPL-3.0.txt) { Copy-Item .\packaging\licenses\GPL-3.0.txt (Join-Path $FfmpegTarget "GPL-3.0.txt") -Force }
if (Test-Path .\packaging\THIRD_PARTY_SOURCE.md) { Copy-Item .\packaging\THIRD_PARTY_SOURCE.md (Join-Path $FfmpegTarget "THIRD_PARTY_SOURCE.md") -Force }
if (Test-Path .\vendor\ffmpeg) {
    Get-ChildItem .\vendor\ffmpeg -File | Where-Object { $_.Extension -ne '.exe' } | Copy-Item -Destination $FfmpegTarget -Force
}

$PackedFfmpeg = Join-Path $Dist "_internal\vendor\ffmpeg\ffmpeg.exe"
$PackedFfprobe = Join-Path $Dist "_internal\vendor\ffmpeg\ffprobe.exe"
if (-not (Test-Path $PackedFfmpeg)) { throw "Packaging failure: bundled ffmpeg.exe missing from dist." }
if (-not (Test-Path $PackedFfprobe)) { throw "Packaging failure: bundled ffprobe.exe missing from dist." }
if ((Get-Sha256Hex $PackedFfmpeg) -ne $ExpectedFfmpegSha256) { throw "Packaged ffmpeg.exe SHA256 mismatch." }
if ((Get-Sha256Hex $PackedFfprobe) -ne $ExpectedFfprobeSha256) { throw "Packaged ffprobe.exe SHA256 mismatch." }
Write-Host "Bundled FFmpeg gate: PASS (exact validated binaries embedded)" -ForegroundColor Green

Write-Host ""
Write-Host "=== Build result ===" -ForegroundColor Green
Get-Item $Exe | Select-Object FullName, @{Name="SizeMB";Expression={[math]::Round($_.Length / 1MB, 2)}}, @{Name="SHA256";Expression={Get-Sha256Hex $_.FullName}}
Write-Host ""
Write-Host "Distribution folder:" -ForegroundColor Cyan
Write-Host $Dist
Write-Host ""
Write-Host "Self-contained packaging policy: PASS. No FFmpeg setup step is required." -ForegroundColor Green
Write-Host "After focused final validation, use .\packaging\create_release_zip.ps1." -ForegroundColor Yellow
