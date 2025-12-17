# Token Tracking Setup Guide

This guide walks you through setting up token tracking in Open WebUI.

## Prerequisites

- Open WebUI backend installed and running
- Access to the backend directory
- Database file location: `backend/data/webui.db`

## Installation

### Step 1: Install the Token Tracking Package

Install the upgraded fork of the token tracking package:

```bash
pip install --upgrade --force-reinstall --no-cache-dir git+https://github.com/sarang-remapai/openwebui-token-tracking.git
```

### Step 2: Run Initial Migration

Initialize the token tracking database:

```bash
cd /Users/sarangali/Workspace/privateai/private_ai_frontend/backend && export DATABASE_URL="sqlite:///$(pwd)/data/webui.db" && owui-token-tracking init 2>&1
```

## Configuration

### Step 3: Create OpenAI Pipe Function

Create a new function file in Open WebUI's functions directory (typically `backend/functions/` or similar). Create a file named `openai_pipe.py` with the following content:

```python
"""
title: OpenAI Pipe
author: Simon Stone
requirements: 
version: 0.1.0
"""
# Notice that 'requirements' is empty above.
# This prevents Open WebUI from overwriting your custom library.

from openwebui_token_tracking.pipes.openai import OpenAITrackedPipe
Pipe = OpenAITrackedPipe
```

**Important**: The empty `requirements` field prevents Open WebUI from overwriting your custom library.

### Step 4: Enable OpenAI Pipe Function

1. Go to Open WebUI Settings
2. Navigate to Functions/Extensions section
3. Enable the "OpenAI Pipe" function
4. Set your OpenAI API key in the settings

### Step 5: Insert Models into Database

Run the migration command with `token_parity.json` to insert model configurations:

```bash
cd /Users/sarangali/Workspace/privateai/private_ai_frontend/backend && export DATABASE_URL="sqlite:////Users/sarangali/Workspace/privateai/private_ai_frontend/backend/data/webui.db" && owui-token-tracking init --model-json token-tracking/token_parity.json
```

**Note**: Whenever you add new models to `token_parity.json`, you need to run this migration command again to update the database.

### Step 6: Create Check Balance Function

Create a new function file named `check_balance.py` in the functions directory with the following content:

```python
"""
title: Check Balance
author: Simon Stone
version: 0.1.0
requirements: 
icon_url: data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIj8+CjwhLS0gQ3JlYXRlZCB3aXRoIElua3NjYXBlIChodHRwOi8vd3d3Lmlua3NjYXBlLm9yZy8pIC0tPgoKPHN2ZwogICB3aWR0aD0iMjRtbSIKICAgaGVpZ2h0PSIyNG1tIgogICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgIHZlcnNpb249IjEuMSIKICAgaWQ9InN2ZzUiCiAgIHhtbDpzcGFjZT0icHJlc2VydmUiCiAgIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICAgeG1sbnM6c3ZnPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnMKICAgICBpZD0iZGVmczIiIC8+PHRleHQKICAgICB4bWw6c3BhY2U9InByZXNlcnZlIgogICAgIHN0eWxlPSJmb250LXNpemU6My4yMTgzN3B4O2ZvbnQtZmFtaWx5OlZpcmdpbDstaW5rc2NhcGUtZm9udC1zcGVjaWZpY2F0aW9uOlZpcmdpbDtmaWxsOiM2NzY3Njc7ZmlsbC1vcGFjaXR5OjE7c3Ryb2tlLXdpZHRoOjAuNjA4NTQxO3N0cm9rZS1saW5lY2FwOnJvdW5kO3N0cm9rZS1saW5lam9pbjpyb3VuZDtzdHJva2UtZGFzaGFycmF5Om5vbmUiCiAgICAgeD0iMTYuNTE3MTkxIgogICAgIHk9Ii0xLjk1NjE0MTUiCiAgICAgaWQ9InRleHQ0NTciCiAgICAgdHJhbnNmb3JtPSJzY2FsZSgwLjk5MzQyNjk4LDEuMDA2NjE2NSkiPjx0c3BhbgogICAgICAgaWQ9InRzcGFuNDU1IgogICAgICAgc3R5bGU9ImZpbGw6IzY3Njc2NztmaWxsLW9wYWNpdHk6MTtzdHJva2Utd2lkdGg6MC42MDg1NDE7c3Ryb2tlLWRhc2hhcnJheTpub25lIgogICAgICAgeD0iMTYuNTE3MTkxIgogICAgICAgeT0iLTEuOTU2MTQxNSIgLz48L3RleHQ+PGcKICAgICBpZD0iZzE4NjkxIgogICAgIHRyYW5zZm9ybT0ibWF0cml4KDAuODI4MTEzOTgsMCwwLDAuODMxMDI1NzMsMi4zNDAyODg3LDIuMzcwOTM0MSkiCiAgICAgc3R5bGU9InN0cm9rZS13aWR0aDoxLjIwNTQ1Ij48dGV4dAogICAgICAgeG1sOnNwYWNlPSJwcmVzZXJ2ZSIKICAgICAgIHN0eWxlPSJmb250LXNpemU6MTQuMjQ1cHg7Zm9udC1mYW1pbHk6VmlyZ2lsOy1pbmtzY2FwZS1mb250LXNwZWNpZmljYXRpb246VmlyZ2lsO2ZpbGw6IzY3Njc2NztmaWxsLW9wYWNpdHk6MTtzdHJva2U6bm9uZTtzdHJva2Utd2lkdGg6MC43MzM1NjM7c3Ryb2tlLWxpbmVjYXA6cm91bmQ7c3Ryb2tlLWxpbmVqb2luOnJvdW5kO3N0cm9rZS1kYXNoYXJyYXk6bm9uZTtzdHJva2Utb3BhY2l0eToxIgogICAgICAg4D0iMTIuODE3OTE5IgogICAgICAgeT0iMTkuNTEwNDg5IgogICAgICAgaWQ9InRleHQxMTcxIgogICAgICAgdHJhbnNmb3JtPSJzY2FsZSgwLjk5MzQyNjk5LDEuMDA2NjE2NSkiPjx0c3BhbgogICAgICAgICBpZD0idHNwYW4xMTY5IgogICAgICAgICBzdHlsZT0iZm9udC1zdHlsZTpub3JtYWw7Zm9udC12YXJpYW50Om5vcm1hbDtmb250LXdlaWdodDpib2xkO2ZvbnQtc3RyZXRjaDpub3JtYWw7Zm9udC1mYW1pbHk6J0RhcnRtb3V0aCBSdXppY2thJzstaW5rc2NhcGUtZm9udC1zcGVjaWZpY2F0aW9uOidEYXJ0bW91dGggUnV6aWNrYSBCb2xkJztmaWxsOiM2NzY3Njc7ZmlsbC1vcGFjaXR5OjE7c3Ryb2tlOm5vbmU7c3Ryb2tlLXdpZHRoOjAuNzMzNTYzO3N0cm9rZS1kYXNoYXJyYXk6bm9uZTtzdHJva2Utb3BhY2l0eToxIgogICAgICAgICB4PSIxMi44MTc5MTkiCiAgICAgICAgIHk9IjE5LjUxMDQ4OSI+JDwvdHNwYW4+PC90ZXh0PjxyZWN0CiAgICAgICBzdHlsZT0iZmlsbDpub25lO2ZpbGwtb3BhY2l0eToxO3N0cm9rZTojNjc2NzY3O3N0cm9rZS13aWR0aDoxLjkxMzY0O3N0cm9rZS1saW5lY2FwOmJ1dHQ7c3Ryb2tlLWxpbmVqb2luOnJvdW5kO3N0cm9rZS1kYXNoYXJyYXk6bm9uZTtzdHJva2Utb3BhY2l0eToxIgogICAgICAgaWQ9InJlY3QyMDYxIgogICAgICAgd2lkdGg9IjE3LjU4OTg1MSIKICAgICAgIGhlaWdodD0iMjIuMTE0MjA2IgogICAgICAgeD0iMy4yMDUwNzQxIgogICAgICAgeT0iMC45NDI4OTYzNyIgLz48cGF0aAogICAgICAgc3R5bGU9ImZpbGw6bm9uZTtmaWxsLW9wYWNpdHk6MTtzdHJva2U6IzY3Njc2NztzdHJva2Utd2lkdGg6MS45MTM2NDtzdHJva2UtbGluZWNhcDpidXR0O3N0cm9rZS1saW5lam9pbjpyb3VuZDtzdHJva2UtZGFzaGFycmF5Om5vbmU7c3Ryb2tlLW9wYWNpdHk6MSIKICAgICAgIGQ9Ik0gNi40NjI0NTM1LDMuODU4NDUxMSBIIDE3LjUzNzU0NiIKICAgICAgIGlkPSJwYXRoMjEyNiIgLz48cGF0aAogICAgICAgc3R5bGU9ImZpbGw6bm9uZTtmaWxsLW9wYWNpdHk6MTtzdHJva2U6IzY3Njc2NztzdHJva2Utd2lkdGg6MS45MTM2NDtzdHJva2UtbGluZWNhcDpidXR0O3N0cm9rZS1saW5lam9pbjpyb3VuZDtzdHJva2UtZGFzaGFycmF5Om5vbmU7c3Ryb2tlLW9wYWNpdHk6MSIKICAgICAgIGQ9Ik0gNi40NjI0NTM1LDcuMTMyMTU4OSBIIDE3LjUzNzU0NiIKICAgICAgIGlkPSJwYXRoMjEyNi01IiAvPjwvZz48L3N2Zz4K
"""
from openwebui_token_tracking.actions import CreditBalance
Action = CreditBalance
```

### Step 7: Enable Check Balance Function

1. Go to Open WebUI Settings
2. Navigate to Functions/Extensions section
3. Enable the "Check Balance" function
4. **Make it global** (available to all users)

## Managing Plans and Users

After completing the setup above, you can create credit groups (plans) and assign users to them. 

For detailed commands on:
- Creating credit groups (plans) for clients
- Finding user IDs
- Assigning users to groups
- Managing token limits

See the **[db-management.ipynb](./db-management.ipynb)** notebook for all the management commands.

### Quick Reference

The workflow for managing clients:

1. **Create a Credit Group**: Create a group for each client with a token limit
   - The token limit is considered separately for each user in the group
   - Each user gets their own allocation based on the group's limit

2. **Assign Users**: Assign users to the group based on allocated seats under this group/client
   - Users are assigned to groups according to their client's allocated seats
   - Each user within a group has independent token tracking against the group's limit

## Adding New Models

When you need to add new models:

1. Update `token_parity.json` with the new model configuration
2. Run the migration command again:

```bash
cd /Users/sarangali/Workspace/privateai/private_ai_frontend/backend && export DATABASE_URL="sqlite:////Users/sarangali/Workspace/privateai/private_ai_frontend/backend/data/webui.db" && owui-token-tracking init --model-json token-tracking/token_parity.json
```

## Token Parity JSON Structure

The `token_parity.json` file defines the token cost structure for different models. Each model entry contains:

- `provider`: The provider name (e.g., "openai", "anthropic", etc.)
- `id`: The model identifier (e.g., "gpt-4.1-mini")
- `name`: Display name for the model
- `input_cost_credits`: Credits charged per input token
- `per_input_tokens`: Token multiplier for input (typically 1)
- `output_cost_credits`: Credits charged per output token
- `per_output_tokens`: Token multiplier for output (typically 1)

**Note**: The default settings (1 token = 1 credit) fit our use case.

## Troubleshooting

- If the migration fails, ensure the database path is correct
- Make sure the token tracking package is installed before running migrations
- Verify that functions are enabled in Open WebUI settings
- Check that API keys are properly configured in settings
