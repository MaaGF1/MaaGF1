<#
.SYNOPSIS
    Resource Updater for MaaGF1
    
.DESCRIPTION
    This script updates specific resource files (interface.json, resource/, resource_en/)
    by downloading a specific resource zip asset from GitHub Releases.
    It supports preserving or modifying the 'agent' configuration in interface.json.

.NOTES
    Author: SwordofMorning
    Date: 2025-12-22
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
# 2. Version & Agent Detection
# -----------------------------------------------------------------------------

Log-Info $Lang.detecting_version

$InterfaceJsonPath = Join-Path $RootDir "interface.json"
if (-not (Test-Path $InterfaceJsonPath)) {
    Log-Error "interface.json not found in project root."
    Read-Host $Lang.press_enter
    exit 1
}

$CurrentHasAgent = $false

try {
    # We use ConvertFrom-Json here ONLY for reading/detection. 
    # We will NOT use it for writing to preserve formatting.
    $InterfaceData = Get-Content $InterfaceJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $CurrentVersion = $InterfaceData.version
    
    # Check for Agent configuration
    if ($null -ne $InterfaceData.agent) {
        $CurrentHasAgent = $true
    }

    # Regex to parse v1.8.1 -> Major:1, Minor:8
    if ($CurrentVersion -match "^v(\d+)\.(\d+)\.") {
        $CurrentMajor = $Matches[1]
        $CurrentMinor = $Matches[2]
    } else {
        throw "Version format in interface.json is invalid ($CurrentVersion)."
    }
    
    Log-Info ($Lang.current_version -f $CurrentVersion)
    $AgentStatusStr = if ($CurrentHasAgent) { "Enabled" } else { "Disabled" }
    Log-Info ($Lang.agent_detected -f $AgentStatusStr)
}
catch {
    Log-Error "Error reading version: $_"
    Read-Host $Lang.press_enter
    exit 1
}

# -----------------------------------------------------------------------------
# 3. Fetch GitHub Releases
# -----------------------------------------------------------------------------

Log-Info $Lang.fetching_releases

# Use Releases API instead of Tags API to access Assets
$ApiUrl = "https://api.github.com/repos/$($Settings.repo_owner)/$($Settings.repo_name)/releases"

try {
    # Note: GitHub API has rate limits.
    $Releases = Invoke-RestMethod -Uri $ApiUrl -Method Get -ErrorAction Stop
}
catch {
    Log-Error $Lang.network_error
    Write-Host $_
    Read-Host $Lang.press_enter
    exit 1
}

# Filter Releases based on Major.Minor version constraint and Asset existence
$AvailableVersions = @()
foreach ($Release in $Releases) {
    $TagName = $Release.tag_name
    
    # Check if tag matches vX.Y pattern
    if ($TagName -match "^v(\d+)\.(\d+)\.") {
        $TagMajor = $Matches[1]
        $TagMinor = $Matches[2]
        
        if ($TagMajor -eq $CurrentMajor -and $TagMinor -eq $CurrentMinor) {
            
            # Look for the specific resource zip asset
            # Expected name: MaaGF1-Resource-vX.Y.Z.zip
            $TargetAssetName = "MaaGF1-Resource-$TagName.zip"
            $AssetObj = $Release.assets | Where-Object { $_.name -eq $TargetAssetName } | Select-Object -First 1

            if ($AssetObj) {
                $DisplayObj = [PSCustomObject]@{
                    Name = $TagName
                    DownloadUrl = $AssetObj.browser_download_url
                    IsPre = $Release.prerelease
                }
                $AvailableVersions += $DisplayObj
            }
        }
    }
}

if ($AvailableVersions.Count -eq 0) {
    Log-Warn ($Lang.no_compatible_versions -f $CurrentMajor, $CurrentMinor)
    Read-Host $Lang.press_enter
    exit 0
}

# -----------------------------------------------------------------------------
# 4. User Interaction (Version Selection)
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

# -----------------------------------------------------------------------------
# 5. User Interaction (Agent Selection)
# -----------------------------------------------------------------------------

Write-Host ""
Log-Info $Lang.agent_menu_title
Write-Host "1. $($Lang.agent_opt_keep -f $AgentStatusStr)"
Write-Host "2. $($Lang.agent_opt_enable)"
Write-Host "3. $($Lang.agent_opt_disable)"

$AgentSelection = 0
while ($true) {
    $InputStr = Read-Host $Lang.agent_select
    if ([int]::TryParse($InputStr, [ref]$AgentSelection) -and $AgentSelection -ge 1 -and $AgentSelection -le 3) {
        break
    }
    Log-Warn $Lang.invalid_selection
}

$FinalAgentState = $false
switch ($AgentSelection) {
    1 { $FinalAgentState = $CurrentHasAgent }
    2 { $FinalAgentState = $true }
    3 { $FinalAgentState = $false }
}

# -----------------------------------------------------------------------------
# 6. Download and Update Logic
# -----------------------------------------------------------------------------

# Prepare Temp Directory
$TempDir = Join-Path $ScriptPath "temp_update"
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
New-Item -ItemType Directory -Path $TempDir | Out-Null

$ZipPath = Join-Path $TempDir "resource_pack.zip"

# Construct Download URL using Proxy
$OriginalUrl = $TargetVer.DownloadUrl
$DownloadUrl = "$($Settings.proxy_url)$OriginalUrl"

Log-Info ($Lang.downloading -f $TargetVer.Name)
Log-Info "URL: $DownloadUrl"

try {
    # 1. Download
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath -UseBasicParsing
    
    # 2. Backup Existing Files
    Log-Info $Lang.backing_up
    $BackupDir = Join-Path $ScriptPath "backup_$(Get-Date -Format 'yyyyMMddHHmmss')"
    New-Item -ItemType Directory -Path $BackupDir | Out-Null

    $FilesToUpdate = @("interface.json", "resource", "resource_en")
    
    foreach ($ItemName in $FilesToUpdate) {
        $ItemPath = Join-Path $RootDir $ItemName
        if (Test-Path $ItemPath) {
            Move-Item -Path $ItemPath -Destination $BackupDir -Force
        }
    }

    # 3. Extract Zip
    Log-Info $Lang.extracting
    # The new zip structure is flat, so we extract directly to RootDir
    Expand-Archive -Path $ZipPath -DestinationPath $RootDir -Force

    # 4. Handle Agent Logic
    # STRATEGY: To preserve the specific formatting (Tabs, comments, inline arrays)
    # enforced by the Python script, we DO NOT use ConvertTo-Json.
    # Instead, we use text manipulation to append the agent node if needed.
    
    if ($FinalAgentState) {
        Log-Info $Lang.restoring_agent
        
        $NewInterfacePath = Join-Path $RootDir "interface.json"
        if (Test-Path $NewInterfacePath) {
            
            # Read as raw text
            $RawContent = Get-Content $NewInterfacePath -Raw -Encoding UTF8
            
            # Find the last closing brace '}'
            $LastBraceIndex = $RawContent.LastIndexOf('}')
            
            if ($LastBraceIndex -gt 0) {
                # Slice the content before the last '}'
                $ContentBeforeEnd = $RawContent.Substring(0, $LastBraceIndex)
                
                # Prepare the Agent JSON String
                # We use explicit Tabs (`t) to match the user's config: "indent": { "style": "tab", "width": 1 }
                # The comma at the start is crucial to separate it from the previous node.
                $AgentString = @'
,
	"agent": {
		"child_exec": "{PROJECT_DIR}/agent/dist/maa_agent.exe",
		"child_args": []
	}
'@
                # Reassemble the file: Original Content + Agent String + Closing Brace
                # We assume the original file ends cleanly (e.g. with a newline or just '}')
                $NewContent = $ContentBeforeEnd + $AgentString + "`n}"
                
                # Write back using UTF8 (No BOM is preferred by some, but PS default UTF8 usually adds BOM. 
                # Standard JSON parsers handle BOM fine.)
                Set-Content $NewInterfacePath -Value $NewContent -Encoding UTF8 -NoNewline
            } else {
                Log-Warn "Warning: Could not find closing brace in interface.json. Agent config was NOT added."
            }
        }
    }
    # If $FinalAgentState is false, we do nothing. 
    # The file extracted from the ZIP is already the "Standard" version (clean, formatted, no agent).

    Log-Info $Lang.cleaning
    Remove-Item $TempDir -Recurse -Force

    Log-Success ($Lang.success -f $TargetVer.Name)

}
catch {
    Log-Error "Update Failed: $_"
    
    # Attempt Restore
    Log-Warn "Attempting to restore from backup..."
    if ($BackupDir -and (Test-Path $BackupDir)) {
        foreach ($ItemName in $FilesToUpdate) {
            $BackupItem = Join-Path $BackupDir $ItemName
            $DestItem = Join-Path $RootDir $ItemName
            if (Test-Path $BackupItem) {
                if (Test-Path $DestItem) { Remove-Item $DestItem -Recurse -Force }
                Move-Item -Path $BackupItem -Destination $RootDir -Force
            }
        }
        Write-Host "Restore completed." -ForegroundColor Yellow
    }
    
    if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
}

Read-Host $Lang.press_enter