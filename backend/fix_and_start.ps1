# Fix ChromaDB corruption and start the server
cd $PSScriptRoot

Write-Host "Checking for ChromaDB corruption..." -ForegroundColor Yellow

# Backup and reset corrupted ChromaDB if it exists
$chromaDbPath = "data\vector_db\chroma.sqlite3"
if (Test-Path $chromaDbPath) {
    $backupPath = "data\vector_db\chroma.sqlite3.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Host "Backing up existing ChromaDB database to: $backupPath" -ForegroundColor Cyan
    Copy-Item $chromaDbPath $backupPath -ErrorAction SilentlyContinue
    
    # Try to remove the corrupted database
    # Note: You may want to keep the backup and manually inspect it
    Write-Host "Removing corrupted ChromaDB database. It will be recreated on startup." -ForegroundColor Yellow
    Remove-Item $chromaDbPath -Force -ErrorAction SilentlyContinue
}

# Set environment variables if not already set
if (-not $env:WEBUI_SECRET_KEY -and -not $env:WEBUI_JWT_SECRET_KEY) {
    $keyFile = ".webui_secret_key"
    if (Test-Path $keyFile) {
        $env:WEBUI_SECRET_KEY = Get-Content $keyFile -Raw
        Write-Host "Loaded WEBUI_SECRET_KEY from file" -ForegroundColor Green
    } else {
        # Generate a random key
        Write-Host "Generating new WEBUI_SECRET_KEY..." -ForegroundColor Cyan
        $bytes = New-Object byte[] 12
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        $rng.GetBytes($bytes)
        $key = [Convert]::ToBase64String($bytes)
        $key | Out-File -FilePath $keyFile -NoNewline -Encoding utf8
        $env:WEBUI_SECRET_KEY = $key
    }
}

Write-Host "Starting server..." -ForegroundColor Green
Write-Host "Using Python wrapper to avoid PowerShell argument parsing issues" -ForegroundColor Cyan
Write-Host ""

# Run using the Python wrapper script
python run_uvicorn.py

