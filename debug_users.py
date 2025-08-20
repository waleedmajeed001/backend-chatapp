#!/usr/bin/env python3
"""
Debug script to check online users and connection status
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

async def check_online_users():
    """Check current online users via debug endpoint"""
    print("🔍 Checking online users...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/debug/online-users") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Online users endpoint working!")
                    print(f"📊 Total connections: {data['total_connections']}")
                    print(f"👥 Online users: {len(data['online_users'])}")
                    
                    if data['online_users']:
                        print("\n📋 Online users list:")
                        for i, user in enumerate(data['online_users'], 1):
                            print(f"  {i}. {user['username']} ({user['email']})")
                    else:
                        print("❌ No users online")
                    
                    if data['connection_details']:
                        print(f"\n🔗 Connection details:")
                        for conn in data['connection_details']:
                            print(f"  - {conn['user']['username']} (WS ID: {conn['websocket_id']})")
                    
                    return True
                else:
                    print(f"❌ Online users endpoint failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error checking online users: {str(e)}")
        return False

async def check_recent_messages():
    """Check recent messages"""
    print("\n🔍 Checking recent messages...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/messages?limit=5") as response:
                if response.status == 200:
                    messages = await response.json()
                    print(f"✅ Found {len(messages)} recent messages")
                    
                    if messages:
                        print("\n📝 Recent messages:")
                        for i, msg in enumerate(messages[-3:], 1):  # Show last 3
                            print(f"  {i}. {msg['user']['username']}: {msg['content'][:50]}...")
                    
                    return True
                else:
                    print(f"❌ Messages endpoint failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error checking messages: {str(e)}")
        return False

if __name__ == "__main__":
    load_dotenv()
    
    print("🐛 Debug: Online Users and Messages")
    print("=" * 40)
    
    success1 = asyncio.run(check_online_users())
    success2 = asyncio.run(check_recent_messages())
    
    print("\n" + "=" * 40)
    if success1 and success2:
        print("🎉 Debug check completed successfully!")
    else:
        print("💥 Some checks failed. Check your backend is running.")
    
    print("\n💡 Tips:")
    print("  - Make sure backend is running: python app.py")
    print("  - Check backend console for connection logs")
    print("  - Try connecting from different browsers/devices")
    print("  - Look for 'User connected' and 'User disconnected' messages")
