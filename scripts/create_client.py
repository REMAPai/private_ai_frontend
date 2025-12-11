#!/usr/bin/env python3
"""
Script to create a client and optionally assign a subscription plan.

Usage:
    python create_client.py --name "Client Name" --plan-id 1 --seats 1
    python create_client.py --name "My Client" --plan-id 1
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
from datetime import datetime, timedelta
from pathlib import Path

# Add the backend directory to the path
backend_path = '/app/backend' if os.path.exists('/app/backend') else os.path.join(Path(__file__).resolve().parents[1], 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from open_webui.internal.db import get_db
from open_webui.models.subscriptions import Client, SubscriptionPlan, ClientModel


def create_client(
    name: str,
    subscription_plan_id: int = None,
    seats_purchased: int = 1,
    next_reset_date: datetime = None
) -> ClientModel:
    """Create a new client"""
    with get_db() as db:
        # Check if client with same name exists
        existing = db.query(Client).filter(Client.name == name).first()
        if existing:
            print(f"❌ Error: Client with name '{name}' already exists (ID: {existing.id})")
            sys.exit(1)
        
        # Validate subscription plan if provided
        plan = None
        if subscription_plan_id:
            plan = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.id == subscription_plan_id
            ).first()
            if not plan:
                print(f"❌ Error: Subscription plan with ID {subscription_plan_id} not found")
                sys.exit(1)
            
            if not plan.is_active:
                print(f"⚠️  Warning: Subscription plan '{plan.plan_name}' is not active")
        
        # Set default reset date if not provided
        if next_reset_date is None:
            next_reset_date = datetime.utcnow() + timedelta(days=30)
        
        client = Client(
            name=name,
            subscription_plan_id=subscription_plan_id,
            seats_purchased=seats_purchased,
            next_reset_date=next_reset_date
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        
        # Calculate total tokens if plan is assigned
        total_tokens = 0
        if subscription_plan_id and plan:
            total_tokens = plan.tokens_per_seat * seats_purchased
        
        print(f"✓ Created client successfully!")
        print(f"  Client ID: {client.id}")
        print(f"  Client Name: {name}")
        print(f"  Seats Purchased: {seats_purchased}")
        if subscription_plan_id and plan:
            print(f"  Subscription Plan: {plan.plan_name} (ID: {subscription_plan_id})")
            print(f"  Tokens per seat: {plan.tokens_per_seat:,}")
            print(f"  Total tokens: {total_tokens:,} ({plan.tokens_per_seat:,} × {seats_purchased} seats)")
        else:
            print(f"  No subscription plan assigned")
        print(f"  Next reset date: {next_reset_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return ClientModel.model_validate(client)


def main():
    parser = argparse.ArgumentParser(
        description='Create a client and optionally assign a subscription plan',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_client.py --name "Test Client" --plan-id 1 --seats 1
  python create_client.py --name "My Company" --plan-id 2 --seats 5
  python create_client.py --name "Client Without Plan"
        """
    )
    
    parser.add_argument(
        '--name',
        required=True,
        help='Name of the client (must be unique)'
    )
    parser.add_argument(
        '--plan-id',
        type=int,
        default=None,
        help='ID of the subscription plan to assign (optional)'
    )
    parser.add_argument(
        '--seats',
        type=int,
        default=1,
        help='Number of seats purchased (default: 1)'
    )
    
    args = parser.parse_args()
    
    try:
        create_client(
            name=args.name,
            subscription_plan_id=args.plan_id,
            seats_purchased=args.seats
        )
    except Exception as e:
        print(f"❌ Error creating client: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
