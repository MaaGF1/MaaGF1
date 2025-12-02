<#
.SYNOPSIS
    Resource Updater for MaaGF1
    
.DESCRIPTION
    This script updates specific resource files (interface.json, resource/, resource_en/)
    by downloading the source code of a specific tag from GitHub.
    It enforces updates only within the same Major.Minor version family.

.NOTES
    Author: AI Assistant
    Date: 2023-10-27
    Path: tools/nadia/updater.ps1
#>

# -----------------------------------------------------------------------------
# 1. Initialization & Configuration
# -----------------------------------------------------------------------------

# Set encoding to UTF8 to handle Chinese characters correctly
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Determine script location and root directory
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Resolve-Path "$ScriptPath\..\.." 
$ConfigPath = Join-Path $ScriptPath "config.json"

# Load Configuration
if (-not (Test-Path $ConfigPath)) {
    Write-Host "Error: config.json not found in $ScriptPath" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

try {
    $JsonContent = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $Settings = $JsonContent.settings
    
    # Simple Language Detection (Default to EN, switch to ZH if system locale is Chinese)
    $LangCode = "en"
    if ((Get-Culture).Name -match "zh") { $LangCode = "zh" }
    $Lang = $JsonContent.lang.$LangCode
}
catch {
    Write-Host "Error parsing config.json: $_" -ForegroundColor Red
    exit 1
}

# Helper function for localized output
function Log-Info ($Message) { Write-Host $Message -ForegroundColor Cyan }
function Log-Success ($Message) { Write-Host $Message -ForegroundColor Green }
function Log-Warn ($Message) { Write-Host $Message -ForegroundColor Yellow }
function Log-Error ($Message) { Write-Host $Message -ForegroundColor Red }

# -----------------------------------------------------------------------------
# 2. Version Detection
# -----------------------------------------------------------------------------

Log-Info $Lang.detecting_version

$InterfaceJsonPath = Join-Path $RootDir "interface.json"
if (-not (Test-Path $InterfaceJsonPath)) {
    Log-Error "interface.json not found in project root."
    Read-Host $Lang.press_enter
    exit 1
}

try {
    $InterfaceData = Get-Content $InterfaceJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $CurrentVersion = $InterfaceData.version
    
    # Regex to parse v1.8.1 -> Major:1, Minor:8
    if ($CurrentVersion -match "^v(\d+)\.(\d+)\.") {
        $CurrentMajor = $Matches[1]
        $CurrentMinor = $Matches[2]
    } else {
        throw "Version format in interface.json is invalid ($CurrentVersion)."
    }
    
    Log-Info ($Lang.current_version -f $CurrentVersion)
}
catch {
    Log-Error "Error reading version: $_"
    Read-Host $Lang.press_enter
    exit 1
}

# -----------------------------------------------------------------------------
# 3. Fetch GitHub Tags
# -----------------------------------------------------------------------------

Log-Info $Lang.fetching_tags

$ApiUrl = "https://api.github.com/repos/$($Settings.repo_owner)/$($Settings.repo_name)/tags"

try {
    # Use Invoke-RestMethod. 
    # Note: GitHub API has rate limits. For unauthenticated requests, it's 60/hr.
    $Tags = Invoke-RestMethod -Uri $ApiUrl -Method Get -ErrorAction Stop
}
catch {
    Log-Error $Lang.network_error
    Write-Host $_
    Read-Host $Lang.press_enter
    exit 1
}

# Filter Tags based on Major.Minor version constraint
$AvailableVersions = @()
foreach ($Tag in $Tags) {
    $TagName = $Tag.name
    
    # Check if tag matches vX.Y pattern
    if ($TagName -match "^v(\d+)\.(\d+)\.") {
        $TagMajor = $Matches[1]
        $TagMinor = $Matches[2]
        
        if ($TagMajor -eq $CurrentMajor -and $TagMinor -eq $CurrentMinor) {
            $IsPreRelease = $TagName -match "-" # Simple check for alpha/beta/rc
            $DisplayObj = [PSCustomObject]@{
                Name = $TagName
                ZipUrl = $Tag.zipball_url
                IsPre = $IsPreRelease
            }
            $AvailableVersions += $DisplayObj
        }
    }
}

if ($AvailableVersions.Count -eq 0) {
    Log-Warn "No compatible versions found for v$CurrentMajor.$CurrentMinor.x"
    Read-Host $Lang.press_enter
    exit 0
}

# -----------------------------------------------------------------------------
# 4. User Interaction
# -----------------------------------------------------------------------------

Log-Info $Lang.select_version
Write-Host "------------------------------------------------"

$Index = 1
foreach ($Ver in $AvailableVersions) {
    $Marker = ""
    if ($Ver.Name -eq $CurrentVersion) { $Marker = " <--- Current" }
    
    $PreMsg = ""
    if ($Ver.IsPre) { $PreMsg = " $($Lang.pre_release_warning)" }
    
    $Color = "White"
    if ($Ver.IsPre) { $Color = "Yellow" }
    if ($Ver.Name -eq $CurrentVersion) { $Color = "Green" }

    Write-Host "[$Index] $($Ver.Name)$PreMsg$Marker" -ForegroundColor $Color
    $Index++
}
Write-Host "------------------------------------------------"

$Selection = 0
while ($true) {
    $InputStr = Read-Host "Select [1-$($AvailableVersions.Count)]"
    if ([int]::TryParse($InputStr, [ref]$Selection) -and $Selection -ge 1 -and $Selection -le $AvailableVersions.Count) {
        break
    }
    Log-Warn $Lang.invalid_selection
}

$TargetVer = $AvailableVersions[$Selection - 1]

if ($TargetVer.Name -eq $CurrentVersion) {
    Log-Success $Lang.same_version
    Read-Host $Lang.press_enter
    exit 0
}

# -----------------------------------------------------------------------------
# 5. Download and Update Logic
# -----------------------------------------------------------------------------

# Prepare Paths
$TempDir = Join-Path $ScriptPath "temp_update"
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
New-Item -ItemType Directory -Path $TempDir | Out-Null

$ZipPath = Join-Path $TempDir "source.zip"

# Construct Download URL using Proxy
# GitHub Archive URL format: https://github.com/user/repo/archive/refs/tags/v1.0.0.zip
$OriginalUrl = "https://github.com/$($Settings.repo_owner)/$($Settings.repo_name)/archive/refs/tags/$($TargetVer.Name).zip"
$DownloadUrl = "$($Settings.proxy_url)$OriginalUrl"

Log-Info ($Lang.downloading -f $TargetVer.Name)
Log-Info "URL: $DownloadUrl"

try {
    # Download
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath -UseBasicParsing
    
    Log-Info $Lang.extracting
    # Extract Zip
    Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force
    
    # Find the extracted root folder (GitHub zips usually have a root folder like Repo-1.0.0)
    $ExtractedRoot = Get-ChildItem -Path $TempDir -Directory | Select-Object -First 1
    $SourceAssetsPath = Join-Path $ExtractedRoot.FullName "assets"
    
    if (-not (Test-Path $SourceAssetsPath)) {
        throw "Assets folder not found in the downloaded source code."
    }

    Log-Info $Lang.updating

    # Define resources to update mapping: Source (relative to assets/) -> Destination (relative to RootDir)
    $UpdateMap = @{
        "interface.json" = "interface.json"
        "resource"       = "resource"
        "resource_en"    = "resource_en"
    }

    foreach ($Key in $UpdateMap.Keys) {
        $SrcItem = Join-Path $SourceAssetsPath $Key
        $DestItem = Join-Path $RootDir $UpdateMap[$Key]

        if (Test-Path $SrcItem) {
            # 1. Remove Old
            if (Test-Path $DestItem) {
                Write-Host "  - Removing old $Key..." -ForegroundColor Gray
                Remove-Item $DestItem -Recurse -Force
            }
            
            # 2. Copy New
            Write-Host "  - Installing new $Key..." -ForegroundColor Gray
            Copy-Item -Path $SrcItem -Destination $DestItem -Recurse
        } else {
            Log-Warn "Warning: $Key not found in update package."
        }
    }

    Log-Info $Lang.cleaning
    Remove-Item $TempDir -Recurse -Force

    Log-Success ($Lang.success -f $TargetVer.Name)

}
catch {
    Log-Error "Update Failed: $_"
    if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
}

Read-Host $Lang.press_enter