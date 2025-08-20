#!/usr/bin/env python3
"""
Test script to verify database connection and table creation
"""

import asyncio
import os
from dotenv import load_dotenv
from database.connection import get_db_connection, init_db

async def test_database():
    """Test database connection and table creation"""
    print("🔍 Testing database connection...")
    
    try:
        # Test connection
        conn = await get_db_connection()
        print("✅ Database connection successful!")
        
        # Test table creation
        await init_db()
        print("✅ Database tables created/verified!")
        
        # Test querying tables
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        messages_count = await conn.fetchval("SELECT COUNT(*) FROM messages")
        
        print(f"📊 Current database state:")
        print(f"   - Users: {users_count}")
        print(f"   - Messages: {messages_count}")
        
        # Test indexes
        indexes = await conn.fetch("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE tablename IN ('users', 'messages')
        """)
        
        print(f"📈 Database indexes:")
        for index in indexes:
            print(f"   - {index['indexname']} on {index['tablename']}")
        
        await conn.close()
        print("✅ All database tests passed!")
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    load_dotenv()
    
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL not found in environment variables")
        print("Please create a .env file with your Neon database URL")
        exit(1)
    
    success = asyncio.run(test_database())
    if success:
        print("\n🎉 Database is ready for the chat application!")
    else:
        print("\n💥 Database setup failed. Please check your configuration.")
        exit(1)
