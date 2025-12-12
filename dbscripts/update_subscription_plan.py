#!/usr/bin/env python3
"""
Script to update a subscription plan in the database.

Usage:
    python update_subscription_plan.py --plan-id 1 --tokens 100000
    python update_subscription_plan.py --plan-id 1 --tokens 500000 --description "Updated description"
    python update_subscription_plan.py --plan-id 1 --name "New Plan Name"
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
from pathlib import Path
from datetime import datetime

# Add the backend directory to the path
backend_path = '/app/backend' if os.path.exists('/app/backend') else os.path.join(Path(__file__).resolve().parents[1], 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from open_webui.internal.db import get_db
from open_webui.models.subscriptions import SubscriptionPlan, SubscriptionPlanModel


def update_subscription_plan(
    plan_id: int,
    tokens_per_seat: int = None,
    plan_name: str = None,
    description: str = None,
    is_active: bool = None
) -> SubscriptionPlanModel:
    """Update an existing subscription plan"""
    with get_db() as db:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        
        if not plan:
            print(f"❌ Error: Subscription plan with ID {plan_id} not found")
            sys.exit(1)
        
        # Store original values for display
        original_tokens = plan.tokens_per_seat
        original_name = plan.plan_name
        original_description = plan.description
        original_active = plan.is_active
        
        # Update fields if provided
        if tokens_per_seat is not None:
            plan.tokens_per_seat = tokens_per_seat
        if plan_name is not None:
            # Check if new name conflicts with existing plan
            existing = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.plan_name == plan_name,
                SubscriptionPlan.id != plan_id
            ).first()
            if existing:
                print(f"❌ Error: Plan with name '{plan_name}' already exists (ID: {existing.id})")
                sys.exit(1)
            plan.plan_name = plan_name
        if description is not None:
            plan.description = description
        if is_active is not None:
            plan.is_active = is_active
        
        # Update the updated_at timestamp
        plan.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(plan)
        
        print(f"✓ Updated subscription plan successfully!")
        print(f"  Plan ID: {plan.id}")
        print(f"\nChanges made:")
        if tokens_per_seat is not None and tokens_per_seat != original_tokens:
            print(f"  Tokens per seat: {original_tokens:,} → {tokens_per_seat:,}")
        if plan_name is not None and plan_name != original_name:
            print(f"  Plan name: '{original_name}' → '{plan_name}'")
        if description is not None and description != original_description:
            print(f"  Description: '{original_description or 'N/A'}' → '{description or 'N/A'}'")
        if is_active is not None and is_active != original_active:
            print(f"  Active status: {original_active} → {is_active}")
        
        print(f"\nCurrent plan details:")
        print(f"  Plan ID: {plan.id}")
        print(f"  Plan Name: {plan.plan_name}")
        print(f"  Tokens per seat: {plan.tokens_per_seat:,}")
        print(f"  Description: {plan.description or 'N/A'}")
        print(f"  Active: {plan.is_active}")
        
        return SubscriptionPlanModel.model_validate(plan)


def main():
    parser = argparse.ArgumentParser(
        description='Update an existing subscription plan in the database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update tokens only
  python update_subscription_plan.py --plan-id 1 --tokens 100000
  
  # Update tokens and description
  python update_subscription_plan.py --plan-id 1 --tokens 500000 --description "Updated description"
  
  # Update plan name
  python update_subscription_plan.py --plan-id 1 --name "New Plan Name"
  
  # Deactivate a plan
  python update_subscription_plan.py --plan-id 1 --inactive
  
  # Activate a plan
  python update_subscription_plan.py --plan-id 1 --active
        """
    )
    
    parser.add_argument(
        '--plan-id',
        type=int,
        required=True,
        help='ID of the subscription plan to update'
    )
    parser.add_argument(
        '--tokens',
        type=int,
        default=None,
        help='New number of tokens per seat'
    )
    parser.add_argument(
        '--name',
        default=None,
        help='New name for the plan'
    )
    parser.add_argument(
        '--description',
        default=None,
        help='New description for the plan'
    )
    parser.add_argument(
        '--active',
        action='store_true',
        help='Set the plan as active'
    )
    parser.add_argument(
        '--inactive',
        action='store_true',
        help='Set the plan as inactive'
    )
    
    args = parser.parse_args()
    
    # Handle active/inactive flags
    is_active = None
    if args.active and args.inactive:
        print("❌ Error: Cannot specify both --active and --inactive")
        sys.exit(1)
    elif args.active:
        is_active = True
    elif args.inactive:
        is_active = False
    
    # Check if at least one field is being updated
    if args.tokens is None and args.name is None and args.description is None and is_active is None:
        print("❌ Error: At least one field must be specified for update (--tokens, --name, --description, --active, or --inactive)")
        sys.exit(1)
    
    try:
        update_subscription_plan(
            plan_id=args.plan_id,
            tokens_per_seat=args.tokens,
            plan_name=args.name,
            description=args.description,
            is_active=is_active
        )
    except Exception as e:
        print(f"❌ Error updating subscription plan: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
