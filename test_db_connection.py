#!/usr/bin/env python3
"""Test MongoDB connection."""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


async def test_connection():
    """Test MongoDB connection and basic operations."""
    print("🔍 Testing MongoDB Connection")
    print("=" * 50)
    print(f"MongoDB URI: {settings.mongodb_uri}")
    print(f"Database: {settings.mongodb_db_name}")
    print("=" * 50)

    try:
        # Create client
        client = AsyncIOMotorClient(settings.mongodb_uri)
        print("✓ Client created")

        # Test ping
        await client.admin.command("ping")
        print("✓ Connection successful (ping)")

        # Get database
        db = client[settings.mongodb_db_name]
        print(f"✓ Database selected: {settings.mongodb_db_name}")

        # List collections
        collections = await db.list_collection_names()
        print(f"✓ Collections found: {len(collections)}")
        if collections:
            print(f"  - {', '.join(collections)}")

        # Get server info
        server_info = await client.server_info()
        print(f"✓ MongoDB version: {server_info.get('version', 'unknown')}")

        # Close connection
        client.close()
        print("✓ Connection closed")
        print("\n✅ All tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
