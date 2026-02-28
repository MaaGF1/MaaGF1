<#
.SYNOPSIS
    Build script wrapper for SCons with Mode Selection.
.EXAMPLE
    .\build.ps1 -Mode Debug
    .\build.ps1 -Mode Release
#>

param (
    [ValidateSet("debug", "release")]
    [string]$Mode = "release"
)

Write-Host "[*] Selected Build Mode: $Mode" -ForegroundColor Yellow
Write-Host "[*] Locating Visual Studio 2022 Environment..." -ForegroundColor Cyan

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"

if (-not (Test-Path $vswhere)) {
    Write-Error "[-] vswhere.exe not found."
    exit 1
}

# Get the VS path containing the C++ x64 build toolchain
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ([string]::IsNullOrEmpty($vsPath)) {
    Write-Error "[-] MSVC Toolchain not found."
    exit 1
}

$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"

if (-not (Test-Path $vcvars)) {
    Write-Error "[-] vcvars64.bat not found."
    exit 1
}

Write-Host "[+] Found MSVC Env: $vcvars" -ForegroundColor Green
Write-Host "[*] Starting SCons build pipeline..." -ForegroundColor Cyan
Write-Host "------------------------------------------------------"

# Pass the mode argument to SCons
$cmd = "`"$vcvars`" && scons mode=$Mode"
cmd.exe /c $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "------------------------------------------------------"
    Write-Host "[+] Build SUCCESS! Output generated in .\build directory." -ForegroundColor Green
} else {
    Write-Host "------------------------------------------------------"
    Write-Error "[-] Build FAILED. Check errors above."
}