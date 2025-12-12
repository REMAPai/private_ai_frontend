#!/usr/bin/env python3
"""
Script to assign a user to a client, which allocates tokens based on the client's subscription plan.

Usage:
    python assign_user_to_client.py --user-id "user-id-here" --client-id 1
    python assign_user_to_client.py --user-email "user@example.com" --client-id 1
"""

import sys
import os

# Set required environment variables BEFORE any other imports
# This must happen before importing pathlib or anything else that might trigger imports
webui_secret = os.environ.get('WEBUI_SECRET_KEY', '').strip()
if not webui_secret:
    os.environ['WEBUI_SECRET_KEY'] = 'dummy-secret-key-for-scripts'
webui_auth = os.environ.get('WEBUI_AUTH', '').strip().lower()
if webui_auth != 'false':
    os.environ['WEBUI_AUTH'] = 'false'

import argparse
from datetime import datetime
from pathlib import Path

# Add the backend directory to the path
backend_path = '/app/backend' if os.path.exists('/app/backend') else os.path.join(Path(__file__).resolve().parents[1], 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from open_webui.internal.db import get_db
from open_webui.models.subscriptions import Client, UsagePerUser, UsagePerUserModel
from open_webui.models.users import User


def assign_user_to_client(user_id: str, client_id: int) -> UsagePerUserModel:
    """Assign a user to a client"""
    with get_db() as db:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ Error: User with ID '{user_id}' not found")
            sys.exit(1)
        
        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            print(f"❌ Error: Client with ID {client_id} not found")
            sys.exit(1)
        
        # Get or create usage record
        usage = db.query(UsagePerUser).filter(UsagePerUser.user_id == user_id).first()
        if usage:
            usage.client_id = client_id
            usage.updated_at = datetime.utcnow()
        else:
            usage = UsagePerUser(
                user_id=user_id,
                client_id=client_id,
                used_tokens=0
            )
            db.add(usage)
        
        db.commit()
        db.refresh(usage)
        
        # Calculate allocated tokens
        allocated_tokens = 0
        if client.subscription_plan:
            allocated_tokens = client.subscription_plan.tokens_per_seat * client.seats_purchased
        
        print(f"✓ Successfully assigned user to client!")
        print(f"  User: {user.name} ({user.email})")
        print(f"  User ID: {user_id}")
        print(f"  Client: {client.name} (ID: {client_id})")
        if client.subscription_plan:
            print(f"  Subscription Plan: {client.subscription_plan.plan_name}")
            print(f"  Tokens per seat: {client.subscription_plan.tokens_per_seat:,}")
            print(f"  Seats: {client.seats_purchased}")
            print(f"  Allocated tokens: {allocated_tokens:,}")
            print(f"  Used tokens: {usage.used_tokens:,}")
            print(f"  Remaining tokens: {allocated_tokens - usage.used_tokens:,}")
        else:
            print(f"  ⚠️  Warning: Client has no subscription plan assigned")
            print(f"  User will use default token allocation")
        
        return UsagePerUserModel.model_validate(usage)


def get_user_id_by_email(email: str) -> str:
    """Get user ID by email"""
    with get_db() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ Error: User with email '{email}' not found")
            sys.exit(1)
        return user.id


def main():
    parser = argparse.ArgumentParser(
        description='Assign a user to a client to allocate tokens',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python assign_user_to_client.py --user-id "abc123" --client-id 1
  python assign_user_to_client.py --user-email "user@example.com" --client-id 1
        """
    )
    
    user_group = parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument(
        '--user-id',
        help='ID of the user to assign'
    )
    user_group.add_argument(
        '--user-email',
        help='Email of the user to assign'
    )
    
    parser.add_argument(
        '--client-id',
        type=int,
        required=True,
        help='ID of the client to assign the user to'
    )
    
    args = parser.parse_args()
    
    # Get user ID
    if args.user_email:
        user_id = get_user_id_by_email(args.user_email)
    else:
        user_id = args.user_id
    
    try:
        assign_user_to_client(user_id, args.client_id)
    except Exception as e:
        print(f"❌ Error assigning user to client: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
