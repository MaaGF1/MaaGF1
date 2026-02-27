<#
.SYNOPSIS
    build script
#>

Write-Host "[*] Locating Visual Studio 2022 build environment..." -ForegroundColor Cyan

# Locate the VS installation path via vswhere
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"

if (-not (Test-Path $vswhere)) {
    Write-Error "[-] vswhere.exe not found. Please ensure Visual Studio is installed."
    exit 1
}

# Get the VS path containing the C++ x64 build toolchain
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ([string]::IsNullOrEmpty($vsPath)) {
    Write-Error "[-] No matching MSVC build environment found. Please check VS installation components."
    exit 1
}

$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"

if (-not (Test-Path $vcvars)) {
    Write-Error "[-] Environment variable script not found: $vcvars"
    exit 1
}

Write-Host "[+] Found MSVC environment: $vcvars" -ForegroundColor Green
Write-Host "[*] Starting SCons build process..." -ForegroundColor Cyan
Write-Host "------------------------------------------------------"

# Use cmd.exe to execute sequentially, ensuring SCons inherits environment variables set by vcvars64.bat
$cmd = "`"$vcvars`" && scons"
cmd.exe /c $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "------------------------------------------------------"
    Write-Host "[+] Build successful! Artifacts have been output to the .\build directory." -ForegroundColor Green
} else {
    Write-Host "------------------------------------------------------"
    Write-Error "[-] Build failed. Please check the error messages above."
}