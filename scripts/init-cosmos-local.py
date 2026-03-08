#!/usr/bin/env python3
"""
Initialize Cosmos DB for local development.
Creates database, containers, and seed data for 42-Bank.

Usage:
    uv run python scripts/init-cosmos-local.py

Environment Variables:
    COSMOS_ENDPOINT - Cosmos DB endpoint (default: emulator)
    COSMOS_KEY - Account key (default: emulator key)
    DATABASE_NAME - Database name (default: banking)

Requirements:
    uv add azure-cosmos
"""

import os
import sys
import json
import urllib3
from datetime import datetime

# Disable SSL warnings for emulator
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from azure.cosmos import CosmosClient, PartitionKey, exceptions
except ImportError:
    print("Error: azure-cosmos package required")
    print("Install with: uv add azure-cosmos")
    sys.exit(1)

# Configuration
EMULATOR_ENDPOINT = os.getenv(
    "COSMOS_ENDPOINT",
    "https://localhost:8081/"
)
EMULATOR_KEY = os.getenv(
    "COSMOS_KEY",
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "banking")

# Container configurations
CONTAINERS = {
    "users": {
        "partition_key": "/token",
        "description": "User accounts and balances"
    },
    "transactions": {
        "partition_key": "/timestamp",
        "description": "Transaction history"
    },
    "pending_requests": {
        "partition_key": "/request_id",
        "description": "Pending payment requests"
    },
    "products": {
        "partition_key": "/id",
        "description": "Banking products catalog"
    }
}

# Seed users (same as bootstrap.py)
SEED_USERS = [
    {"token": "alice_token", "username": "alice", "balance": 1000.0, "public_key": None},
    {"token": "bob_token", "username": "bob", "balance": 500.0, "public_key": None},
    {"token": "charlie_token", "username": "charlie", "balance": 250.0, "public_key": None},
]

# Seed products
SEED_PRODUCTS = [
    {"id": "checking-standard", "name": "Standard Checking", "description": "Basic checking account with no minimum balance", "rate": None, "type": "account"},
    {"id": "checking-premium", "name": "Premium Checking", "description": "Premium checking with interest and no fees", "rate": 0.01, "type": "account"},
    {"id": "savings-basic", "name": "Basic Savings", "description": "Simple savings account with competitive rates", "rate": 0.02, "type": "account"},
    {"id": "savings-high-yield", "name": "High-Yield Savings", "description": "High-yield savings with tiered interest rates", "rate": 0.04, "type": "account"},
    {"id": "cd-6month", "name": "6-Month CD", "description": "6-month certificate of deposit", "rate": 0.03, "type": "cd"},
    {"id": "cd-12month", "name": "12-Month CD", "description": "12-month certificate of deposit", "rate": 0.04, "type": "cd"},
]


def create_database(client: CosmosClient, database_name: str):
    """Create database if not exists."""
    print(f"\n1️⃣ Creating database: {database_name}")
    try:
        database = client.create_database_if_not_exists(
            id=database_name,
            offer_throughput=None  # Serverless
        )
        print(f"   ✅ Database ready")
        return database
    except Exception as e:
        print(f"   ⚠️  {e}")
        return client.get_database_client(database_name)


def create_containers(database, containers_config: dict):
    """Create containers if not exist."""
    print(f"\n2️⃣ Creating containers...")
    for container_name, config in containers_config.items():
        partition_key = config["partition_key"]
        try:
            container = database.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path=partition_key),
            )
            print(f"   ✅ {container_name} (partition: {partition_key})")
        except exceptions.CosmosResourceExistsError:
            print(f"   ⚠️  {container_name} already exists")
        except Exception as e:
            print(f"   ❌ {container_name}: {e}")


def seed_users(database, seed_data: list):
    """Seed initial user accounts."""
    print(f"\n3️⃣ Seeding users...")
    users_container = database.get_container_client("users")
    
    for user_data in seed_data:
        user_doc = {
            "id": user_data["token"],
            "token": user_data["token"],
            "username": user_data["username"],
            "public_key": user_data["public_key"],
            "accounts": {
                "checking": {
                    "balance": user_data["balance"],
                    "account_type": "checking",
                    "opened_at": datetime.now().isoformat()
                },
                "savings": {
                    "balance": 0.0,
                    "account_type": "savings",
                    "opened_at": datetime.now().isoformat()
                }
            },
            "created_at": datetime.now().isoformat()
        }
        
        try:
            users_container.upsert_item(body=user_doc)
            print(f"   ✅ {user_data['username']}: ${user_data['balance']:.2f}")
        except Exception as e:
            print(f"   ⚠️  {user_data['username']}: {e}")


def seed_products(database, products_data: list):
    """Seed product catalog."""
    print(f"\n4️⃣ Seeding products...")
    products_container = database.get_container_client("products")
    
    for product in products_data:
        product_doc = {
            "id": product["id"],
            "name": product["name"],
            "description": product["description"],
            "rate": product.get("rate"),
            "type": product["type"],
            "created_at": datetime.now().isoformat()
        }
        
        try:
            products_container.upsert_item(body=product_doc)
            print(f"   ✅ {product['name']}")
        except Exception as e:
            print(f"   ⚠️  {product['name']}: {e}")


def verify_containers(database):
    """Verify all containers exist and show counts."""
    print(f"\n5️⃣ Verifying containers...")
    
    for container_name in CONTAINERS.keys():
        try:
            container = database.get_container_client(container_name)
            props = container.read()
            print(f"   ✅ {container_name}: {props.get('id')}")
        except Exception as e:
            print(f"   ❌ {container_name}: {e}")


def print_connection_info():
    """Print connection information for reference."""
    print("\n" + "="*60)
    print("📝 Connection Information")
    print("="*60)
    print(f"\nEndpoint: {EMULATOR_ENDPOINT}")
    print(f"Database: {DATABASE_NAME}")
    print("\nEnvironment Variables:")
    print(f'  export COSMOS_ENDPOINT="{EMULATOR_ENDPOINT}"')
    print(f'  export COSMOS_KEY="{EMULATOR_KEY}"')
    print(f'  export DATABASE_NAME="{DATABASE_NAME}"')
    print("\nConnection String:")
    print(f'  export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint={EMULATOR_ENDPOINT};AccountKey={EMULATOR_KEY}"')
    print("\nData Explorer:")
    print(f"  https://localhost:1234/_explorer/index.html")
    print("="*60)


def main():
    """Initialize local Cosmos DB for 42-Bank development."""
    print("🏦 42-Bank - Cosmos DB Initialization")
    print("="*60)
    print("This script initializes Cosmos DB for local development")
    print()
    
    # Connect to emulator
    print(f"Connecting to Cosmos DB at {EMULATOR_ENDPOINT}...")
    
    try:
        client = CosmosClient(
            EMULATOR_ENDPOINT,
            credential=EMULATOR_KEY,
            connection_verify=False  # Emulator has self-signed cert
        )
        print("✅ Connected to Cosmos DB")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Docker is running: docker ps")
        print("  2. Start emulator: docker-compose up -d cosmos-emulator")
        print("  3. Wait 30 seconds for emulator to start")
        sys.exit(1)
    
    # Create database
    database = create_database(client, DATABASE_NAME)
    
    # Create containers
    create_containers(database, CONTAINERS)
    
    # Seed data
    seed_users(database, SEED_USERS)
    seed_products(database, SEED_PRODUCTS)
    
    # Verify
    verify_containers(database)
    
    # Print connection info
    print_connection_info()
    
    print("\n✅ Initialization complete!")
    print("\nNext steps:")
    print("  1. Start servers with Cosmos: DB_MODE=cosmos ./dev.sh alice")
    print("  2. Or use SQLite (default):   ./dev.sh alice")


if __name__ == "__main__":
    main()
