#!/usr/bin/env python3
"""
Test script to verify WebSocket functionality
"""

import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
from services.auth_service import AuthService

async def test_websocket_connection():
    """Test WebSocket connection and messaging"""
    print("🔍 Testing WebSocket connection...")
    
    try:
        # Get a test token (you'll need to create a user first)
        # For testing, you can use the auth endpoints to create a user and get a token
        
        # Test WebSocket connection
        uri = "ws://localhost:8000/ws/chat?token=test_token"
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection established!")
            
            # Send a test message
            test_message = "Hello from test client!"
            await websocket.send(test_message)
            print(f"📤 Sent message: {test_message}")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received response: {response}")
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for response")
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {str(e)}")
        return False
    
    return True

async def test_online_users_endpoint():
    """Test the debug endpoint for online users"""
    print("🔍 Testing online users endpoint...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/debug/online-users") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Online users endpoint working!")
                    print(f"📊 Online users: {data['online_users']}")
                    print(f"🔗 Total connections: {data['total_connections']}")
                    return True
                else:
                    print(f"❌ Online users endpoint failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Online users test failed: {str(e)}")
        return False

if __name__ == "__main__":
    load_dotenv()
    
    print("🧪 WebSocket and Connection Tests")
    print("=" * 40)
    
    # Test online users endpoint
    success1 = asyncio.run(test_online_users_endpoint())
    
    # Note: WebSocket test requires authentication
    print("\n📝 Note: WebSocket test requires valid JWT token")
    print("   Create a user first using the auth endpoints")
    
    if success1:
        print("\n🎉 Basic tests passed!")
    else:
        print("\n💥 Tests failed. Please check your configuration.")
