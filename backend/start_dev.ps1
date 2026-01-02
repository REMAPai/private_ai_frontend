# Development script to start backend with CORS enabled for frontend dev server
cd $PSScriptRoot

# Set CORS to allow frontend dev server (Vite runs on port 5173 by default)
$env:CORS_ALLOW_ORIGIN = "http://localhost:5173;http://localhost:8080"

# Set environment variables if not already set
if (-not $env:WEBUI_SECRET_KEY -and -not $env:WEBUI_JWT_SECRET_KEY) {
    $keyFile = ".webui_secret_key"
    if (Test-Path $keyFile) {
        $env:WEBUI_SECRET_KEY = Get-Content $keyFile -Raw
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

Write-Host "Starting backend in development mode..." -ForegroundColor Green
Write-Host "CORS_ALLOW_ORIGIN: $env:CORS_ALLOW_ORIGIN" -ForegroundColor Cyan
Write-Host "Backend will be available at: http://localhost:8080" -ForegroundColor Cyan
Write-Host "Frontend dev server should connect to: http://localhost:8080" -ForegroundColor Cyan
Write-Host ""

# Run using the Python wrapper script
python run_uvicorn.py

