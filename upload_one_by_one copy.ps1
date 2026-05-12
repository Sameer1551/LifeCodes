# upload_one_by_one.ps1
$RemoteUrl = "https://github.com/Sameer1551/LifeCodes.git"
$Branch = "main"

Write-Host "--- Git Contribution Script ---" -ForegroundColor Green

# 1. Check Git Config (Crucial for contributions!)
$ConfigEmail = git config user.email
if ($ConfigEmail -ne "siddheshvikram1@gmail.com") {
    Write-Host "WARNING: Your git email is set to '$ConfigEmail'." -ForegroundColor Yellow
    Write-Host "Setting it to siddheshvikram1@gmail.com for you..." -ForegroundColor Cyan
    git config user.email "siddheshvikram1@gmail.com"
}
Write-Host "Using Email: $(git config user.email)" -ForegroundColor Gray
Write-Host "-------------------------------" -ForegroundColor Green

# 2. Initialization
if (-not (Test-Path .git)) {
    Write-Host "Initializing Git repository..." -ForegroundColor Cyan
    git init
    git remote add origin $RemoteUrl
    git branch -M $Branch
}

# 3. Get all files recursively
$Files = Get-ChildItem -Path . -File -Recurse | Where-Object { 
    $_.FullName -notmatch "\\\.git\\" -and 
    $_.Name -ne "upload_one_by_one.ps1" 
}
$Total = $Files.Count
$Count = 0

Write-Host "Found $Total files. Starting sequential upload..." -ForegroundColor Green

foreach ($File in $Files) {
    $Count++
    
    # Calculate relative path and use forward slashes for Git
    $RelativePath = ($File.FullName.Replace($PWD.Path, "").TrimStart("\")).Replace("\", "/")
    
    # Check if the file actually needs to be committed
    $Status = git status --porcelain "$RelativePath"
    if (-not $Status) {
        Write-Host "[$Count/$Total] Skipping: $RelativePath (No changes detected)" -ForegroundColor Gray
        continue
    }

    Write-Host "[$Count/$Total] Uploading: $RelativePath" -ForegroundColor Cyan
    
    # Add and Commit
    git add "$RelativePath"
    git commit -m "Add $RelativePath" -q
    
    if ($LASTEXITCODE -eq 0) {
        # Push to Remote
        git push origin $Branch -q
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "!! Push failed. Retrying in 15s..." -ForegroundColor Red
            Start-Sleep -Seconds 15
            git push origin $Branch
        }
        
        # Random delay (30-90 seconds)
        $Wait = Get-Random -Minimum 30 -Maximum 90
        Write-Host "Done. Waiting $Wait seconds..." -ForegroundColor DarkGray
        Start-Sleep -Seconds $Wait
    } else {
        Write-Host "!! Failed to commit $RelativePath" -ForegroundColor Red
    }
}

Write-Host "Task Complete!" -ForegroundColor Green

