#!/usr/bin/env python3
"""
Test script to verify the users endpoint functionality
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

async def test_users_endpoint():
    """Test the users endpoint"""
    print("🔍 Testing users endpoint...")
    
    try:
        # First, we need to get a valid token by logging in
        async with aiohttp.ClientSession() as session:
            # Try to login with a test user (you'll need to create this user first)
            login_data = {
                "email": "test@example.com",
                "password": "testpassword"
            }
            
            async with session.post("http://localhost:8000/auth/login", json=login_data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    token = token_data["access_token"]
                    print("✅ Login successful, got token")
                else:
                    print(f"❌ Login failed: {response.status}")
                    print("Please create a test user first using the register endpoint")
                    return False
            
            # Now test the users endpoint
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get("http://localhost:8000/auth/users", headers=headers) as response:
                if response.status == 200:
                    users = await response.json()
                    print(f"✅ Users endpoint working! Found {len(users)} users")
                    
                    if users:
                        print("\n📋 Users list:")
                        for i, user in enumerate(users, 1):
                            print(f"  {i}. {user['username']} ({user['email']})")
                    else:
                        print("❌ No users found")
                    
                    return True
                else:
                    print(f"❌ Users endpoint failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing users endpoint: {str(e)}")
        return False

async def test_register_user():
    """Test user registration"""
    print("\n🔍 Testing user registration...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Register a test user
            register_data = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpassword"
            }
            
            async with session.post("http://localhost:8000/auth/register", json=register_data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    print("✅ User registration successful!")
                    return token_data["access_token"]
                elif response.status == 400:
                    print("ℹ️ User already exists, trying login instead")
                    # Try login instead
                    login_data = {
                        "email": "test@example.com",
                        "password": "testpassword"
                    }
                    async with session.post("http://localhost:8000/auth/login", json=login_data) as login_response:
                        if login_response.status == 200:
                            token_data = await login_response.json()
                            print("✅ Login successful!")
                            return token_data["access_token"]
                        else:
                            print(f"❌ Login failed: {login_response.status}")
                            return None
                else:
                    print(f"❌ Registration failed: {response.status}")
                    return None
                    
    except Exception as e:
        print(f"❌ Error testing registration: {str(e)}")
        return None

if __name__ == "__main__":
    load_dotenv()
    
    print("🧪 Users Endpoint Test")
    print("=" * 40)
    
    # Test registration/login first
    token = asyncio.run(test_register_user())
    
    if token:
        # Test users endpoint
        success = asyncio.run(test_users_endpoint())
        
        print("\n" + "=" * 40)
        if success:
            print("🎉 Users endpoint test completed successfully!")
        else:
            print("💥 Users endpoint test failed.")
    else:
        print("💥 Could not get authentication token.")
    
    print("\n💡 Tips:")
    print("  - Make sure backend is running: python app.py")
    print("  - Create some test users using the register endpoint")
    print("  - Check that the users endpoint returns all registered users")
