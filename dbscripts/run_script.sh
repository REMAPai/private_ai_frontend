#!/bin/bash
# Helper script to run Python scripts with required environment variables
# Usage: ./run_script.sh <script_name> [args...]

SCRIPT_NAME=$1
shift

docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python "/tmp/scripts/${SCRIPT_NAME}" "$@"
