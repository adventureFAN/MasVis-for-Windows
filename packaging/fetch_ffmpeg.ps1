$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Stage = Join-Path $env:TEMP "MasVis-FFmpeg-9.0.1"
$Archive = Join-Path $Stage "ffmpeg-9.0.1-essentials_build.zip"
$Extract = Join-Path $Stage "extracted"
$Vendor = Join-Path $ProjectRoot "vendor\ffmpeg"

$Url = "https://github.com/GyanD/codexffmpeg/releases/download/9.0.1/ffmpeg-9.0.1-essentials_build.zip"
$ExpectedArchiveSha256 = "FEC81AE03971D9DD4BE3EBE02E263BD2EC1D789483F931BDBA5F5715E65DA2E9"
$ExpectedFfmpegSha256 = "72A489ECCD008C2EC2C0A5856C5C75BC3D8BBFA90166C4566865C246445E6AA3"
$ExpectedFfprobeSha256 = "19202B23C0043F15AD1B7BCE2344F406FD52BD6EFD8F995CE02E7392A1CEC52F"
$ExpectedVersionMarker = "ffmpeg version 9.0.1-essentials_build-www.gyan.dev"

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

Remove-Item $Stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item $Stage -ItemType Directory -Force | Out-Null
New-Item $Extract -ItemType Directory -Force | Out-Null

Write-Host "=== FFmpeg 9.0.1 Essentials herunterladen ===" -ForegroundColor Cyan
& curl.exe -L --fail --retry 3 --progress-bar $Url -o $Archive
if ($LASTEXITCODE -ne 0) { throw "FFmpeg download failed." }

$ArchiveHash = Get-Sha256Hex $Archive
if ($ArchiveHash -ne $ExpectedArchiveSha256) {
    throw "FFmpeg archive SHA256 mismatch. Expected $ExpectedArchiveSha256, got $ArchiveHash."
}
Write-Host "Archiv SHA256: OK" -ForegroundColor Green

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($Archive, $Extract)

$Ffmpeg = Get-ChildItem $Extract -Recurse -Filter ffmpeg.exe -File | Select-Object -First 1
$Ffprobe = Get-ChildItem $Extract -Recurse -Filter ffprobe.exe -File | Select-Object -First 1
if (-not $Ffmpeg -or -not $Ffprobe) { throw "ffmpeg.exe or ffprobe.exe was not found in the verified archive." }

$FfmpegHash = Get-Sha256Hex $Ffmpeg.FullName
$FfprobeHash = Get-Sha256Hex $Ffprobe.FullName
if ($FfmpegHash -ne $ExpectedFfmpegSha256) { throw "ffmpeg.exe SHA256 mismatch." }
if ($FfprobeHash -ne $ExpectedFfprobeSha256) { throw "ffprobe.exe SHA256 mismatch." }

$VersionLine = (& $Ffmpeg.FullName -version 2>&1 | Select-Object -First 1).ToString()
if (-not $VersionLine.Contains($ExpectedVersionMarker)) { throw "Unexpected FFmpeg version: $VersionLine" }

$Filters = & $Ffmpeg.FullName -filters 2>&1
if (-not ($Filters -match '\bebur128\b')) { throw "Required FFmpeg filter ebur128 is missing." }
if (-not ($Filters -match '\bastats\b')) { throw "Required FFmpeg filter astats is missing." }

Remove-Item $Vendor -Recurse -Force -ErrorAction SilentlyContinue
New-Item $Vendor -ItemType Directory -Force | Out-Null
Copy-Item $Ffmpeg.FullName (Join-Path $Vendor "ffmpeg.exe")
Copy-Item $Ffprobe.FullName (Join-Path $Vendor "ffprobe.exe")

$Readme = Get-ChildItem $Extract -Recurse -Filter README.txt -File | Select-Object -First 1
if ($Readme) { Copy-Item $Readme.FullName (Join-Path $Vendor "FFMPEG-GYAN-README.txt") -Force }
$License = Get-ChildItem $Extract -Recurse -Filter LICENSE -File | Select-Object -First 1
if ($License) { Copy-Item $License.FullName (Join-Path $Vendor "FFMPEG-GYAN-LICENSE.txt") -Force }

Write-Host ""
Write-Host "=== FFmpeg vendor baseline ready ===" -ForegroundColor Green
Write-Host $VersionLine
Write-Host "ffmpeg SHA256 : $FfmpegHash"
Write-Host "ffprobe SHA256: $FfprobeHash"
Write-Host "Vendor path    : $Vendor"
