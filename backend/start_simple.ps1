# Simple PowerShell script to start the server using the Python wrapper
# This avoids all PowerShell argument parsing issues

cd $PSScriptRoot

# Set environment variables if not already set
if (-not $env:WEBUI_SECRET_KEY -and -not $env:WEBUI_JWT_SECRET_KEY) {
    $keyFile = ".webui_secret_key"
    if (Test-Path $keyFile) {
        $env:WEBUI_SECRET_KEY = Get-Content $keyFile -Raw
    }
    else {
        # Generate a random key
        $bytes = New-Object byte[] 12
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        $rng.GetBytes($bytes)
        $key = [Convert]::ToBase64String($bytes)
        $key | Out-File -FilePath $keyFile -NoNewline -Encoding utf8
        $env:WEBUI_SECRET_KEY = $key
    }
}

# Run using the Python wrapper script
python run_uvicorn.py

