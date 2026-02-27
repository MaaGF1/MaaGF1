<#
.SYNOPSIS
    Build Script for Windows
#>

Write-Host "[*] Locating the Visual Studio build environment..." -ForegroundColor Cyan

# Find VS installation path via vswhere
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"

if (-not (Test-Path $vswhere)) {
    Write-Error "[-] The vswhere.exe file cannot be found. Please check if Visual Studio is installed.
    exit 1
}

# Get the VS path containing the C++ x64 compilation toolchain
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ([string]::IsNullOrEmpty($vsPath)) {
    Write-Error "[-] No matching MSVC build environment found. Please check your VS installation components."
    exit 1
}

$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"

if (-not (Test-Path $vcvars)) {
    Write-Error "[-] Script for environment variables not found: $vcvars"
    exit 1
}

Write-Host "[+] Find the MSVC environment: $vcvars" -ForegroundColor Green
Write-Host "[*] Initiating the SCons build..." -ForegroundColor Cyan
Write-Host "------------------------------------------------------"

# Use cmd.exe to execute the command repeatedly to ensure that SCons can inherit the environment variables set by vcvars64.bat.
$cmd = "`"$vcvars`" && scons"
cmd.exe /c $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "------------------------------------------------------"
    Write-Host "[+] Build successful! The artifacts have been output to the .\build directory." -ForegroundColor Green
} else {
    Write-Host "------------------------------------------------------"
    Write-Error "[-] The build failed. Please check the error message above."
}