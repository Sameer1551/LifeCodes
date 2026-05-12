# ============================================================
# Context-Menu-Manager.ps1
#
# A generic utility to manage Windows right-click context menu 
# entries for folders and folder backgrounds.
#
# Usage Examples:
#   Add a regular program:
#     ./Context-Menu-Manager.ps1 -Name "Notepad" -Path "C:\Windows\notepad.exe"
#
#   Add a UWP (Store) app:
#     ./Context-Menu-Manager.ps1 -Name "Codex" -AppId "OpenAI.Codex_2p2nqsd0c76g0!App" -Type UWP
#
#   Remove an entry:
#     ./Context-Menu-Manager.ps1 -Name "Notepad" -Action Remove
# ============================================================

Param(
    [Parameter(Mandatory=$false)]
    [string]$Name,          # Display name in the menu

    [Parameter(Mandatory=$false)]
    [string]$Path,          # Full path to the .exe (for standard apps)

    [Parameter(Mandatory=$false)]
    [string]$AppId,         # UWP AppId (for Store apps)

    [Parameter(Mandatory=$false)]
    [ValidateSet("Exe", "UWP")]
    [string]$Type = "Exe",  # Type of application

    [Parameter(Mandatory=$false)]
    [ValidateSet("Add", "Remove", "SetupDefaults")]
    [string]$Action = "Add", # Add or Remove the entry

    [Parameter(Mandatory=$false)]
    [string]$IconPath       # Optional: Path to a custom icon
)

# --- Internal Functions ---

function New-ContextMenuEntry {
    param([string]$KeyName, [string]$Label, [string]$Command, [string]$Icon)

    $roots = @(
        "HKCU:\Software\Classes\Directory\shell\$KeyName",
        "HKCU:\Software\Classes\Directory\Background\shell\$KeyName"
    )

    foreach ($root in $roots) {
        $cmdKey = "$root\command"
        
        # Adjust command for background context if it contains folder tokens
        $actualCommand = $Command
        if ($root -like "*Background*") {
            $actualCommand = $Command -replace '%1', '%V'
        }

        if (-not (Test-Path $root)) { New-Item -Path $root -Force | Out-Null }
        Set-ItemProperty -Path $root -Name "(default)" -Value $Label
        if ($Icon) { Set-ItemProperty -Path $root -Name "Icon" -Value ('"' + $Icon + '"') }

        if (-not (Test-Path $cmdKey)) { New-Item -Path $cmdKey -Force | Out-Null }
        Set-ItemProperty -Path $cmdKey -Name "(default)" -Value $actualCommand

        Write-Host "  [+] Added: $root" -ForegroundColor Green
    }
}

function Remove-ContextMenuEntry {
    param([string]$KeyName)

    $roots = @(
        "HKCU:\Software\Classes\Directory\shell\$KeyName",
        "HKCU:\Software\Classes\Directory\Background\shell\$KeyName"
    )

    foreach ($root in $roots) {
        if (Test-Path $root) {
            Remove-Item -Path $root -Recurse -Force
            Write-Host "  [-] Removed: $root" -ForegroundColor Yellow
        }
    }
}

function Get-CodexIcon {
    $pkg = Get-AppxPackage | Where-Object { $_.Name -eq "OpenAI.Codex" } | Select-Object -First 1
    if ($pkg) {
        $icon = Get-ChildItem $pkg.InstallLocation -Filter "*.ico" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        return $icon.FullName
    }
    return $null
}

# --- Main Logic ---

Write-Host "`n--- Context Menu Manager ---" -ForegroundColor Cyan

if ($Action -eq "SetupDefaults") {
    Write-Host "Setting up default apps (Antigravity & Codex)..."
    
    # Antigravity
    $antiPath = "$env:LOCALAPPDATA\Programs\Antigravity\Antigravity.exe"
    if (Test-Path $antiPath) {
        New-ContextMenuEntry -KeyName "OpenWithAntigravity" -Label "Open with Antigravity" -Command "`"$antiPath`" `"%1`"" -Icon $antiPath
    }

    # Codex
    $codexAppId = "OpenAI.Codex_2p2nqsd0c76g0!App"
    $codexIcon = Get-CodexIcon
    New-ContextMenuEntry -KeyName "OpenWithCodex" -Label "Open with Codex" -Command "explorer.exe shell:AppsFolder\$codexAppId" -Icon $codexIcon
    
    Write-Host "`nSetup complete!" -ForegroundColor Cyan
    exit
}

if ($Action -eq "Remove") {
    if (-not $Name) { Write-Error "Name is required to remove an entry."; exit }
    $safeKey = $Name -replace '\s+', ''
    Remove-ContextMenuEntry -KeyName "OpenWith$safeKey"
    Write-Host "`nRemoval complete!" -ForegroundColor Cyan
    exit
}

# Default Action: Add
if (-not $Name) {
    Write-Host "No parameters provided. Showing help..."
    Write-Host "Use -Action SetupDefaults to re-install Antigravity/Codex."
    Write-Host "Example: ./Context-Menu-Manager.ps1 -Name 'My App' -Path 'C:\path\to\app.exe'"
    exit
}

$safeKey = "OpenWith" + ($Name -replace '\s+', '')
if ($Type -eq "UWP") {
    if (-not $AppId) { Write-Error "AppId is required for UWP apps."; exit }
    New-ContextMenuEntry -KeyName $safeKey -Label "Open with $Name" -Command "explorer.exe shell:AppsFolder\$AppId" -Icon $IconPath
} else {
    if (-not $Path) { Write-Error "Path is required for Exe apps."; exit }
    if (-not (Test-Path $Path)) { Write-Error "Executable not found at: $Path"; exit }
    $icon = if ($IconPath) { $IconPath } else { $Path }
    New-ContextMenuEntry -KeyName $safeKey -Label "Open with $Name" -Command "`"$Path`" `"%1`"" -Icon $icon
}

Write-Host "`nOperation complete!" -ForegroundColor Cyan
