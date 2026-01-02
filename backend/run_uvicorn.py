#!/usr/bin/env python
"""Wrapper script to run uvicorn with proper arguments."""
import sys
import os
import subprocess

if __name__ == "__main__":
    # Set default secret key if not set
    if not os.environ.get("WEBUI_SECRET_KEY") and not os.environ.get("WEBUI_JWT_SECRET_KEY"):
        key_file = os.environ.get("WEBUI_SECRET_KEY_FILE", ".webui_secret_key")
        if os.path.exists(key_file):
            with open(key_file, "r") as f:
                os.environ["WEBUI_SECRET_KEY"] = f.read().strip()
    
    # Build uvicorn arguments
    import uvicorn
    
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    workers = int(os.environ.get("UVICORN_WORKERS", "1"))
    
    uvicorn.run(
        "open_webui.main:app",
        host=host,
        port=port,
        forwarded_allow_ips="*",
        workers=workers
    )

