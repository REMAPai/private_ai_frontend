#!/usr/bin/env python3
"""
Helper script to list users, subscription plans, and clients.

Usage:
    python list_resources.py
    python list_resources.py --users
    python list_resources.py --plans
    python list_resources.py --clients
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
from open_webui.models.subscriptions import SubscriptionPlan, Client, UsagePerUser
from open_webui.models.users import User


def list_users():
    """List all users"""
    with get_db() as db:
        users = db.query(User).all()
        if not users:
            print("No users found")
            return
        
        print("\n" + "="*80)
        print("USERS")
        print("="*80)
        for user in users:
            print(f"  ID: {user.id}")
            print(f"  Name: {user.name}")
            print(f"  Email: {user.email}")
            print(f"  Role: {user.role}")
            print()


def list_plans():
    """List all subscription plans"""
    with get_db() as db:
        plans = db.query(SubscriptionPlan).all()
        if not plans:
            print("No subscription plans found")
            return
        
        print("\n" + "="*80)
        print("SUBSCRIPTION PLANS")
        print("="*80)
        for plan in plans:
            print(f"  ID: {plan.id}")
            print(f"  Name: {plan.plan_name}")
            print(f"  Tokens per seat: {plan.tokens_per_seat:,}")
            print(f"  Description: {plan.description or 'N/A'}")
            print(f"  Active: {plan.is_active}")
            print()


def list_clients():
    """List all clients"""
    with get_db() as db:
        clients = db.query(Client).all()
        if not clients:
            print("No clients found")
            return
        
        print("\n" + "="*80)
        print("CLIENTS")
        print("="*80)
        for client in clients:
            print(f"  ID: {client.id}")
            print(f"  Name: {client.name}")
            print(f"  Seats: {client.seats_purchased}")
            if client.subscription_plan:
                total_tokens = client.subscription_plan.tokens_per_seat * client.seats_purchased
                print(f"  Plan: {client.subscription_plan.plan_name} (ID: {client.subscription_plan_id})")
                print(f"  Total tokens: {total_tokens:,} ({client.subscription_plan.tokens_per_seat:,} × {client.seats_purchased})")
            else:
                print(f"  Plan: None")
            print(f"  Next reset: {client.next_reset_date}")
            print()


def list_all():
    """List all resources"""
    list_users()
    list_plans()
    list_clients()


def main():
    parser = argparse.ArgumentParser(
        description='List users, subscription plans, and clients',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--users',
        action='store_true',
        help='List only users'
    )
    parser.add_argument(
        '--plans',
        action='store_true',
        help='List only subscription plans'
    )
    parser.add_argument(
        '--clients',
        action='store_true',
        help='List only clients'
    )
    
    args = parser.parse_args()
    
    try:
        if args.users:
            list_users()
        elif args.plans:
            list_plans()
        elif args.clients:
            list_clients()
        else:
            list_all()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
