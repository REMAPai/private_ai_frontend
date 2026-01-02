# PowerShell script to start the Open WebUI backend
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

# Add conditional Playwright browser installation
if ($env:WEB_LOADER_ENGINE -eq "playwright") {
    if (-not $env:PLAYWRIGHT_WS_URL) {
        Write-Host "Installing Playwright browsers..."
        playwright install chromium
        playwright install-deps chromium
    }
    python -c "import nltk; nltk.download('punkt_tab')"
}

$KEY_FILE = ".webui_secret_key"
if ($env:WEBUI_SECRET_KEY_FILE) {
    $KEY_FILE = $env:WEBUI_SECRET_KEY_FILE
}

$PORT = if ($env:PORT) { $env:PORT } else { "8080" }
$HOST = if ($env:HOST) { $env:HOST } else { "0.0.0.0" }

if (-not $env:WEBUI_SECRET_KEY -and -not $env:WEBUI_JWT_SECRET_KEY) {
    Write-Host "Loading WEBUI_SECRET_KEY from file, not provided as an environment variable."
    
    if (-not (Test-Path $KEY_FILE)) {
        Write-Host "Generating WEBUI_SECRET_KEY"
        $bytes = New-Object byte[] 12
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        $rng.GetBytes($bytes)
        $key = [Convert]::ToBase64String($bytes)
        $key | Out-File -FilePath $KEY_FILE -NoNewline -Encoding utf8
    }
    
    Write-Host "Loading WEBUI_SECRET_KEY from $KEY_FILE"
    $env:WEBUI_SECRET_KEY = Get-Content $KEY_FILE -Raw
}

if ($env:USE_OLLAMA_DOCKER -eq "true") {
    Write-Host "USE_OLLAMA is set to true, starting ollama serve."
    Start-Process -NoNewWindow ollama -ArgumentList "serve"
}

if ($env:USE_CUDA_DOCKER -eq "true") {
    Write-Host "CUDA is enabled, appending LD_LIBRARY_PATH to include torch/cudnn & cublas libraries."
    $env:LD_LIBRARY_PATH = "$env:LD_LIBRARY_PATH;/usr/local/lib/python3.11/site-packages/torch/lib;/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"
}

# Check if SPACE_ID is set
if ($env:SPACE_ID) {
    Write-Host "Configuring for HuggingFace Space deployment"
    if ($env:ADMIN_USER_EMAIL -and $env:ADMIN_USER_PASSWORD) {
        Write-Host "Admin user configured, creating"
        $env:WEBUI_SECRET_KEY = $env:WEBUI_SECRET_KEY
        Start-Process -NoNewWindow python -ArgumentList "-m", "uvicorn", "open_webui.main:app", "--host", $HOST, "--port", $PORT, "--forwarded-allow-ips", "*"
        $webuiProcess = Get-Process | Where-Object { $_.CommandLine -like "*uvicorn*" } | Select-Object -First 1
        Write-Host "Waiting for webui to start..."
        $maxAttempts = 30
        $attempt = 0
        while ($attempt -lt $maxAttempts) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:${PORT}/health" -UseBasicParsing -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) { break }
            } catch {
                Start-Sleep -Seconds 1
                $attempt++
            }
        }
        Write-Host "Creating admin user..."
        $body = @{
            email = $env:ADMIN_USER_EMAIL
            password = $env:ADMIN_USER_PASSWORD
            name = "Admin"
        } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://localhost:${PORT}/api/v1/auths/signup" -Method Post -Body $body -ContentType "application/json"
        Write-Host "Shutting down webui..."
        Stop-Process -Id $webuiProcess.Id
    }
    $env:WEBUI_URL = $env:SPACE_HOST
}

# Initialize token tracking database migrations
if (Test-Path "$SCRIPT_DIR\init-token-tracking.sh") {
    Write-Host "Running token tracking initialization..."
    bash "$SCRIPT_DIR\init-token-tracking.sh"
}

$UVICORN_WORKERS = if ($env:UVICORN_WORKERS) { $env:UVICORN_WORKERS } else { "1" }
$env:UVICORN_WORKERS = $UVICORN_WORKERS

# Run uvicorn using Python wrapper script to avoid PowerShell argument parsing issues
$env:WEBUI_SECRET_KEY = $env:WEBUI_SECRET_KEY
$env:HOST = $HOST
$env:PORT = $PORT

# Use Python wrapper script to completely bypass PowerShell argument parsing
python run_uvicorn.py

