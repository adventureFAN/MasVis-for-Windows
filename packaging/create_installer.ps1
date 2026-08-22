param(
    [string]$Version = "1.1.0",
    [string]$ISCCPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version must use numeric major.minor.patch form, for example 1.1.0."
}

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

function Resolve-Iscc([string]$RequestedPath) {
    if ($RequestedPath) {
        if (-not (Test-Path -LiteralPath $RequestedPath -PathType Leaf)) {
            throw "ISCC.exe not found at requested path: $RequestedPath"
        }
        return (Resolve-Path -LiteralPath $RequestedPath).Path
    }

    $Command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($Command) {
        return $Command.Source
    }

    $Candidates = @(
        (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe")
    )

    foreach ($Candidate in $Candidates) {
        if ($Candidate -and (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $Candidate).Path
        }
    }

    throw @"
Inno Setup 7 compiler (ISCC.exe) was not found.
Install the current x64 Inno Setup 7 release, for example:

  winget install --id JRSoftware.InnoSetup.7 -e -s winget -i

Then run this script again.
"@
}

$Dist = Join-Path $ProjectRoot "dist\MasVis-for-Windows"
$MainExe = Join-Path $Dist "MasVis-for-Windows.exe"
if (-not (Test-Path -LiteralPath $MainExe -PathType Leaf)) {
    throw "Build output not found. Run .\packaging\build_packaging_test.ps1 first."
}

foreach ($Required in @("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "THIRD-PARTY-LICENSES")) {
    if (-not (Test-Path -LiteralPath (Join-Path $Dist $Required))) {
        throw "Installer gate failed: release file missing from dist: $Required"
    }
}

$PackedFfmpeg = Join-Path $Dist "_internal\vendor\ffmpeg\ffmpeg.exe"
$PackedFfprobe = Join-Path $Dist "_internal\vendor\ffmpeg\ffprobe.exe"
if (-not (Test-Path -LiteralPath $PackedFfmpeg -PathType Leaf)) {
    throw "Installer gate failed: bundled ffmpeg.exe is missing."
}
if (-not (Test-Path -LiteralPath $PackedFfprobe -PathType Leaf)) {
    throw "Installer gate failed: bundled ffprobe.exe is missing."
}
if ((Get-Sha256Hex $PackedFfmpeg) -ne $ExpectedFfmpegSha256) {
    throw "Installer gate failed: ffmpeg.exe SHA256 mismatch."
}
if ((Get-Sha256Hex $PackedFfprobe) -ne $ExpectedFfprobeSha256) {
    throw "Installer gate failed: ffprobe.exe SHA256 mismatch."
}

foreach ($Obsolete in @("Setup-FFmpeg.cmd", "Setup-FFmpeg.ps1")) {
    if (Test-Path -LiteralPath (Join-Path $Dist $Obsolete)) {
        throw "Installer gate failed: obsolete helper is present: $Obsolete"
    }
}

$Compiler = Resolve-Iscc $ISCCPath
$Iss = Join-Path $PSScriptRoot "MasVis-for-Windows.iss"
if (-not (Test-Path -LiteralPath $Iss -PathType Leaf)) {
    throw "Inno Setup script is missing: $Iss"
}

$ReleaseRoot = Join-Path $ProjectRoot "release"
New-Item -ItemType Directory -Path $ReleaseRoot -Force | Out-Null
$SetupExe = Join-Path $ReleaseRoot "MasVis-for-Windows-$Version-Setup.exe"
Remove-Item -LiteralPath $SetupExe -Force -ErrorAction SilentlyContinue

Write-Host "=== Installer packaging baseline ==="
Write-Host "Source runtime: $Dist"
Write-Host "Inno compiler:  $Compiler"
Write-Host "Version:        $Version"
Write-Host "Bundled FFmpeg gate: PASS (exact 9.0.1 binaries present)" -ForegroundColor Green
Write-Host ""
Write-Host "=== Inno Setup build ==="

& $Compiler "/DMyAppVersion=$Version" $Iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compiler failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path -LiteralPath $SetupExe -PathType Leaf)) {
    throw "Installer build completed without the expected output: $SetupExe"
}

$Hash = Get-Sha256Hex $SetupExe
$SizeMiB = [math]::Round((Get-Item -LiteralPath $SetupExe).Length / 1MB, 2)

Write-Host ""
Write-Host "=== Setup installer created ===" -ForegroundColor Green
Write-Host $SetupExe
Write-Host "Size: $SizeMiB MiB"
Write-Host "SHA256: $Hash"
Write-Host "Installer source gate: PASS" -ForegroundColor Green
Write-Host "NOTE: Setup is currently not Authenticode-signed; Windows may show Unknown publisher." -ForegroundColor Yellow
