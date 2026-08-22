param(
    [string]$Version = "1.1.1"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

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

$Dist = Join-Path $ProjectRoot "dist\MasVis-for-Windows"
if (-not (Test-Path (Join-Path $Dist "MasVis-for-Windows.exe"))) { throw "Build output not found. Run .\packaging\build_packaging_test.ps1 first." }

$ReleaseRoot = Join-Path $ProjectRoot "release"
$FolderName = "MasVis-for-Windows-$Version-win64"
$Stage = Join-Path $ReleaseRoot $FolderName
$Zip = Join-Path $ReleaseRoot "$FolderName.zip"

Remove-Item $Stage -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $Zip -Force -ErrorAction SilentlyContinue
New-Item $ReleaseRoot -ItemType Directory -Force | Out-Null
Copy-Item $Dist $Stage -Recurse -Force

foreach ($Required in @("MasVis-for-Windows.exe", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "THIRD-PARTY-LICENSES")) {
    if (-not (Test-Path (Join-Path $Stage $Required))) { throw "Release file missing: $Required" }
}

$PackedFfmpeg = Join-Path $Stage "_internal\vendor\ffmpeg\ffmpeg.exe"
$PackedFfprobe = Join-Path $Stage "_internal\vendor\ffmpeg\ffprobe.exe"
if (-not (Test-Path $PackedFfmpeg)) { throw "Release gate failed: bundled ffmpeg.exe is missing." }
if (-not (Test-Path $PackedFfprobe)) { throw "Release gate failed: bundled ffprobe.exe is missing." }
if ((Get-Sha256Hex $PackedFfmpeg) -ne $ExpectedFfmpegSha256) { throw "Release gate failed: ffmpeg.exe SHA256 mismatch." }
if ((Get-Sha256Hex $PackedFfprobe) -ne $ExpectedFfprobeSha256) { throw "Release gate failed: ffprobe.exe SHA256 mismatch." }

if (Test-Path (Join-Path $Stage "Setup-FFmpeg.cmd")) { throw "Release gate failed: obsolete Setup-FFmpeg.cmd is present." }
if (Test-Path (Join-Path $Stage "Setup-FFmpeg.ps1")) { throw "Release gate failed: obsolete Setup-FFmpeg.ps1 is present." }

Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Zip -CompressionLevel Optimal
$Hash = Get-Sha256Hex $Zip
$SizeMiB = [math]::Round((Get-Item $Zip).Length / 1MB, 2)

Write-Host ""
Write-Host "=== Release ZIP created ===" -ForegroundColor Green
Write-Host $Zip
Write-Host "Size: $SizeMiB MiB"
Write-Host "SHA256: $Hash"
Write-Host "Bundled FFmpeg gate: PASS (exact 9.0.1 binaries present)" -ForegroundColor Green
Write-Host "Portable runtime gate: PASS (no FFmpeg setup helper required)" -ForegroundColor Green
