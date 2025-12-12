# Token Management Scripts

These scripts help you manage subscription plans, clients, and user token allocation in the database.

## Prerequisites

Make sure your Docker containers are running:
```bash
docker ps
```

## How to Run

All scripts should be run inside the Docker container. 

### Option 1: Use the helper script (Easiest!)

```bash
# Copy scripts to container first (one time)
docker cp scripts/ open-webui:/tmp/scripts

# Then use the helper script from your host
./scripts/run_script.sh list_resources.py --users
./scripts/run_script.sh create_subscription_plan.py --name "Basic Plan" --tokens 5000
```

### Option 2: Run directly with environment variables

```bash
# Copy scripts to container (one time)
docker cp scripts/ open-webui:/tmp/scripts

# Run with required environment variables
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/list_resources.py --users
```

## Scripts

### 1. List Resources (Helper Script)

First, use this to find user IDs, plan IDs, and client IDs:

```bash
# List everything
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/list_resources.py

# List only users
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/list_resources.py --users

# List only plans
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/list_resources.py --plans

# List only clients
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/list_resources.py --clients
```

### 2. Create Subscription Plan

```bash
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/create_subscription_plan.py \
  --name "Basic Plan" \
  --tokens 5000 \
  --description "Basic plan with 5k tokens"

# With more tokens
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/create_subscription_plan.py \
  --name "Pro Plan" \
  --tokens 500000 \
  --description "Professional plan"
```

**Note the Plan ID** from the output - you'll need it for the next step!

### 2b. Update Subscription Plan (Adjust Tokens)

```bash
# Update tokens for an existing plan
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/update_subscription_plan.py \
  --plan-id 1 \
  --tokens 100000

# Update tokens and description
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/update_subscription_plan.py \
  --plan-id 1 \
  --tokens 500000 \
  --description "Updated plan description"

# Update plan name
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/update_subscription_plan.py \
  --plan-id 1 \
  --name "New Plan Name"

# Deactivate a plan
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/update_subscription_plan.py \
  --plan-id 1 \
  --inactive
```

### 3. Create Client with Plan

```bash
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/create_client.py \
  --name "Test Client" \
  --plan-id 1 \
  --seats 1

# With multiple seats
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/create_client.py \
  --name "Company Client" \
  --plan-id 1 \
  --seats 5
```

**Note the Client ID** from the output - you'll need it for the next step!

### 4. Assign User to Client

```bash
# Using user ID
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/assign_user_to_client.py \
  --user-id "your-user-id-here" \
  --client-id 1

# Using user email (easier!)
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/assign_user_to_client.py \
  --user-email "user@example.com" \
  --client-id 1
```

## Complete Example Workflow

```bash
# Step 1: List users to find your user email
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/list_resources.py --users

# Step 2: Create a subscription plan
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/create_subscription_plan.py \
  --name "Basic Plan" \
  --tokens 5000

# Output will show: Plan ID: 1

# Step 3: Create a client with this plan
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/create_client.py \
  --name "My Test Client" \
  --plan-id 1 \
  --seats 1

# Output will show: Client ID: 1

# Step 4: Assign user to client
docker exec -e WEBUI_SECRET_KEY=dummy-secret-key -e WEBUI_AUTH=false open-webui python /tmp/scripts/assign_user_to_client.py \
  --user-email "your-email@example.com" \
  --client-id 1
```

## Quick Token Reset (Alternative)

If you just want to reset tokens without using plans/clients:

```bash
# Direct SQL approach (simpler for quick testing)
docker exec -it open-webui sqlite3 /app/backend/data/webui.db "
UPDATE usage_per_user 
SET used_tokens = 0, updated_at = datetime('now')
WHERE user_id = 'YOUR_USER_ID';
"
```

## Troubleshooting

- **"Module not found"**: Make sure you're running inside the container
- **"User not found"**: Use `list_resources.py --users` to find correct user ID/email
- **"Plan not found"**: Use `list_resources.py --plans` to see available plans
- **"Client not found"**: Use `list_resources.py --clients` to see available clients
