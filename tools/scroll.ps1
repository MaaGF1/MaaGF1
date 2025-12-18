# Mouse wheel automation script for Girls' Frontline
# Configurable parameters
param(
    [int]$ScrollCount = 100,           # Number of scroll operations
    [string]$Direction = "down",       # Scroll direction: "up" or "down"
    [int]$MouseX = -1,                 # Mouse X position relative to window (-1 for center)
    [int]$MouseY = -1                  # Mouse Y position relative to window (-1 for center)
)

try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    
    # Define Windows API functions
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public class MouseWheelHelper {
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
    
    public const uint MOUSEEVENTF_WHEEL = 0x0800;
    
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left, Top, Right, Bottom;
    }
}
"@

    # Validate direction parameter
    if ($Direction -notin @("up", "down")) {
        Write-Host "Error: Direction must be 'up' or 'down'"
        exit 1
    }
    
    # Set wheel delta based on direction
    $wheelDelta = if ($Direction -eq "up") { 
        [uint32]120 
    } else { 
        [uint32]([uint32]::MaxValue - 120 + 1)  # Equivalent to -120 in uint32
    }
    
    Write-Host "Searching for game window..."
    
    # Find game window
    $gameWindowTitles = @("少女前线", "Girls' Frontline", "GirlsFrontline")
    $gameWindow = [System.IntPtr]::Zero
    $foundTitle = ""
    
    foreach ($title in $gameWindowTitles) {
        $window = [MouseWheelHelper]::FindWindow($null, $title)
        if ($window -ne [System.IntPtr]::Zero) {
            $gameWindow = $window
            $foundTitle = $title
            Write-Host "Found window: $title"
            break
        }
    }
    
    # Find by process name if method 1 failed
    if ($gameWindow -eq [System.IntPtr]::Zero) {
        
        # Name List
        $targetProcessNames = @("GrilsFrontLine", "GirlsFrontLine")
        
        foreach ($procName in $targetProcessNames) {
            Write-Host "Checking process name: $procName ..."
            $processes = Get-Process -Name $procName -ErrorAction SilentlyContinue
            
            if ($processes) {
                foreach ($process in $processes) {
                    if ($process.MainWindowHandle -ne [System.IntPtr]::Zero) {
                        $gameWindow = $process.MainWindowHandle
                        $foundTitle = $process.MainWindowTitle
                        Write-Host "Found via process ($procName): $($process.MainWindowTitle)"
                        break
                    }
                }
            }
            
            # If find, then break
            if ($gameWindow -ne [System.IntPtr]::Zero) {
                break
            }
        }
    }
    
    # Exit if no game window found
    if ($gameWindow -eq [System.IntPtr]::Zero) {
        Write-Host "Error: Game window not found"
        exit 1
    }
    
    # Get window position and size
    $rect = New-Object MouseWheelHelper+RECT
    $rectResult = [MouseWheelHelper]::GetWindowRect($gameWindow, [ref]$rect)
    if (-not $rectResult) {
        Write-Host "Error: Failed to get window rect"
        exit 1
    }
    
    # Calculate target mouse position
    if ($MouseX -ge 0 -and $MouseY -ge 0) {
        # Use specified coordinates (relative to window)
        $targetX = $rect.Left + $MouseX
        $targetY = $rect.Top + $MouseY
        Write-Host "Using specified mouse position: ($MouseX, $MouseY) relative to window"
    } else {
        # Use window center
        $targetX = ($rect.Left + $rect.Right) / 2
        $targetY = ($rect.Top + $rect.Bottom) / 2
        Write-Host "Using window center: ($targetX, $targetY)"
    }
    
    Write-Host "Window position: Left=$($rect.Left), Top=$($rect.Top), Right=$($rect.Right), Bottom=$($rect.Bottom)"
    Write-Host "Absolute mouse position: ($targetX, $targetY)"
    
    # Activate game window
    Write-Host "Activating game window..."
    $activateResult = [MouseWheelHelper]::SetForegroundWindow($gameWindow)
    if (-not $activateResult) {
        Write-Host "Warning: Failed to activate window"
    }
    Start-Sleep -Milliseconds 500
    
    # Set mouse position to target position
    Write-Host "Moving mouse to target position..."
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($targetX, $targetY)
    Start-Sleep -Milliseconds 200
    
    # Perform mouse wheel operations
    Write-Host "Executing $ScrollCount scroll operations ($Direction)..."
    for ($i = 0; $i -lt $ScrollCount; $i++) {
        [MouseWheelHelper]::mouse_event([MouseWheelHelper]::MOUSEEVENTF_WHEEL, 0, 0, $wheelDelta, [System.UIntPtr]::Zero)
        if (($i + 1) % 10 -eq 0) {
            Write-Host "Scroll $($i + 1)/$ScrollCount completed"
        }
        Start-Sleep -Milliseconds 1
    }
    
    Write-Host "All $ScrollCount scroll operations completed successfully"
    
}
catch {
    Write-Host "Error: $($_.Exception.Message)"
    exit 1
}