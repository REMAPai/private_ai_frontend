#!/usr/bin/env python3
"""
Script to create a subscription plan in the database.

Usage:
    python create_subscription_plan.py --name "Plan Name" --tokens 100000 --description "Description"
    python create_subscription_plan.py --name "Basic Plan" --tokens 5000
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

# Add the backend directory to the path
backend_path = '/app/backend' if os.path.exists('/app/backend') else os.path.join(Path(__file__).resolve().parents[1], 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from open_webui.internal.db import get_db
from open_webui.models.subscriptions import SubscriptionPlan, SubscriptionPlanModel


def create_subscription_plan(
    plan_name: str,
    tokens_per_seat: int,
    description: str = None,
    is_active: bool = True
) -> SubscriptionPlanModel:
    """Create a new subscription plan"""
    with get_db() as db:
        # Check if plan with same name exists
        existing = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_name == plan_name
        ).first()
        
        if existing:
            print(f"❌ Error: Plan with name '{plan_name}' already exists (ID: {existing.id})")
            sys.exit(1)
        
        plan = SubscriptionPlan(
            plan_name=plan_name,
            tokens_per_seat=tokens_per_seat,
            description=description,
            is_active=is_active
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        print(f"✓ Created subscription plan successfully!")
        print(f"  Plan ID: {plan.id}")
        print(f"  Plan Name: {plan.plan_name}")
        print(f"  Tokens per seat: {tokens_per_seat:,}")
        print(f"  Description: {description or 'N/A'}")
        print(f"  Active: {is_active}")
        
        return SubscriptionPlanModel.model_validate(plan)


def main():
    parser = argparse.ArgumentParser(
        description='Create a subscription plan in the database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_subscription_plan.py --name "Basic Plan" --tokens 5000
  python create_subscription_plan.py --name "Pro Plan" --tokens 500000 --description "Professional plan"
  python create_subscription_plan.py --name "Enterprise" --tokens 1000000 --description "Enterprise plan" --inactive
        """
    )
    
    parser.add_argument(
        '--name',
        required=True,
        help='Name of the subscription plan (must be unique)'
    )
    parser.add_argument(
        '--tokens',
        type=int,
        required=True,
        help='Number of tokens per seat'
    )
    parser.add_argument(
        '--description',
        default=None,
        help='Optional description of the plan'
    )
    parser.add_argument(
        '--inactive',
        action='store_true',
        help='Create the plan as inactive (default: active)'
    )
    
    args = parser.parse_args()
    
    try:
        create_subscription_plan(
            plan_name=args.name,
            tokens_per_seat=args.tokens,
            description=args.description,
            is_active=not args.inactive
        )
    except Exception as e:
        print(f"❌ Error creating subscription plan: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
