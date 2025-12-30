#!/usr/bin/env bash

# Script to initialize token tracking database migrations
# This script runs on container startup to ensure migrations are applied

# Don't use set -e as we want to handle errors gracefully
set -u

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

# Check if owui-token-tracking command is available
if ! command -v owui-token-tracking &> /dev/null; then
    echo "Warning: owui-token-tracking command not found. Skipping token tracking initialization."
    echo "Make sure git+https://github.com/sarang-remapai/openwebui-token-tracking.git is installed."
    exit 0
fi

# Set database URL - use environment variable if set, otherwise default to standard location
if [ -z "${DATABASE_URL:-}" ]; then
    # Default to the standard OpenWebUI database location
    export DATABASE_URL="sqlite:///app/backend/data/webui.db"
    # If /app doesn't exist (not in Docker), use current directory
    if [ ! -d "/app" ]; then
        export DATABASE_URL="sqlite:///$(pwd)/data/webui.db"
    fi
fi

echo "Initializing token tracking database..."
echo "Database URL: $DATABASE_URL"

# Check if database file exists (for SQLite)
if [[ "$DATABASE_URL" == sqlite* ]]; then
    DB_PATH=$(echo "$DATABASE_URL" | sed 's|sqlite:///||' | sed 's|sqlite+sqlcipher:///||')
    DB_DIR=$(dirname "$DB_PATH")
    
    # Create directory if it doesn't exist
    if [ ! -d "$DB_DIR" ]; then
        echo "Creating database directory: $DB_DIR"
        mkdir -p "$DB_DIR"
    fi
fi

# Check if token tracking tables already exist
# We'll check by trying to run init and see if it says tables already exist
# or we can check if the tables exist directly

# Run initial migration (this is idempotent - safe to run multiple times)
echo "Running token tracking initialization..."
if owui-token-tracking init 2>&1; then
    echo "Initial migration completed successfully"
else
    echo "Initial migration completed or already applied (non-zero exit is OK)"
fi

# Run model migration if token_parity.json exists
if [ -f "token-tracking/token_parity.json" ]; then
    echo "Running model migration from token_parity.json..."
    if owui-token-tracking init --model-json token-tracking/token_parity.json 2>&1; then
        echo "Model migration completed successfully"
    else
        echo "Model migration completed or already applied (non-zero exit is OK)"
    fi
else
    echo "Warning: token-tracking/token_parity.json not found, skipping model migration"
fi

echo "Token tracking initialization complete!"
