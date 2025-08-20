#!/usr/bin/env python3
"""
Test script for private messaging functionality
"""

import asyncio
import aiohttp
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://localhost:8000"

async def test_private_messaging():
    """Test private messaging functionality"""
    print("🧪 Private Messaging Tests")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Register two users
        print("\n1. Registering test users...")
        
        user1_data = {
            "username": "testuser1",
            "email": "test1@example.com",
            "password": "password123"
        }
        
        user2_data = {
            "username": "testuser2", 
            "email": "test2@example.com",
            "password": "password123"
        }
        
        # Register user1
        async with session.post(f"{BASE_URL}/auth/register", json=user1_data) as response:
            if response.status == 200:
                user1_token = (await response.json())["access_token"]
                print("✅ User1 registered successfully")
            elif response.status == 400:
                # User might already exist, try to login
                print("⚠️ User1 might already exist, trying to login...")
                async with session.post(f"{BASE_URL}/auth/login", json=user1_data) as login_response:
                    if login_response.status == 200:
                        user1_token = (await login_response.json())["access_token"]
                        print("✅ User1 logged in successfully")
                    else:
                        print(f"❌ Failed to login user1: {login_response.status}")
                        return
            else:
                print(f"❌ Failed to register user1: {response.status}")
                return
        
        # Register user2
        async with session.post(f"{BASE_URL}/auth/register", json=user2_data) as response:
            if response.status == 200:
                user2_token = (await response.json())["access_token"]
                print("✅ User2 registered successfully")
            elif response.status == 400:
                # User might already exist, try to login
                print("⚠️ User2 might already exist, trying to login...")
                async with session.post(f"{BASE_URL}/auth/login", json=user2_data) as login_response:
                    if login_response.status == 200:
                        user2_token = (await login_response.json())["access_token"]
                        print("✅ User2 logged in successfully")
                    else:
                        print(f"❌ Failed to login user2: {login_response.status}")
                        return
            else:
                print(f"❌ Failed to register user2: {response.status}")
                return
        
        # Test 2: Get user profiles
        print("\n2. Getting user profiles...")
        
        headers1 = {"Authorization": f"Bearer {user1_token}"}
        headers2 = {"Authorization": f"Bearer {user2_token}"}
        
        async with session.get(f"{BASE_URL}/auth/me", headers=headers1) as response:
            if response.status == 200:
                user1_profile = await response.json()
                print(f"✅ User1 profile: {user1_profile['username']} (ID: {user1_profile['id']})")
            else:
                print(f"❌ Failed to get user1 profile: {response.status}")
                return
        
        async with session.get(f"{BASE_URL}/auth/me", headers=headers2) as response:
            if response.status == 200:
                user2_profile = await response.json()
                print(f"✅ User2 profile: {user2_profile['username']} (ID: {user2_profile['id']})")
            else:
                print(f"❌ Failed to get user2 profile: {response.status}")
                return
        
        # Test 3: Create conversation between users
        print("\n3. Creating conversation...")
        
        conversation_data = {
            "user1_id": user1_profile["id"],
            "user2_id": user2_profile["id"]
        }
        
        async with session.post(f"{BASE_URL}/private/conversations", json=conversation_data, headers=headers1) as response:
            if response.status == 200:
                conversation = await response.json()
                conversation_id = conversation["id"]
                print(f"✅ Conversation created: ID {conversation_id}")
            else:
                print(f"❌ Failed to create conversation: {response.status}")
                error_text = await response.text()
                print(f"Error details: {error_text}")
                return
        
        # Test 4: Get user conversations
        print("\n4. Getting user conversations...")
        
        async with session.get(f"{BASE_URL}/private/conversations", headers=headers1) as response:
            if response.status == 200:
                conversations = await response.json()
                print(f"✅ User1 has {len(conversations)} conversations")
                for conv in conversations:
                    print(f"   - Conversation {conv['conversation']['id']} with {conv['other_user']['username']}")
            else:
                print(f"❌ Failed to get conversations: {response.status}")
                return
        
        # Test 5: Send private message
        print("\n5. Sending private message...")
        
        message_data = {
            "conversation_id": conversation_id,
            "sender_id": user1_profile["id"],
            "content": "Hello from user1!"
        }
        
        async with session.post(f"{BASE_URL}/private/conversations/{conversation_id}/messages", json=message_data, headers=headers1) as response:
            if response.status == 200:
                message = await response.json()
                print(f"✅ Message sent: {message['content']}")
            else:
                print(f"❌ Failed to send message: {response.status}")
                error_text = await response.text()
                print(f"Error details: {error_text}")
                return
        
        # Test 6: Get conversation messages
        print("\n6. Getting conversation messages...")
        
        async with session.get(f"{BASE_URL}/private/conversations/{conversation_id}/messages", headers=headers1) as response:
            if response.status == 200:
                messages = await response.json()
                print(f"✅ Found {len(messages)} messages in conversation")
                for msg in messages:
                    print(f"   - {msg['sender_username']}: {msg['content']}")
            else:
                print(f"❌ Failed to get messages: {response.status}")
                return
        
        # Test 7: Send message from user2
        print("\n7. Sending message from user2...")
        
        message_data2 = {
            "conversation_id": conversation_id,
            "sender_id": user2_profile["id"],
            "content": "Hello from user2!"
        }
        
        async with session.post(f"{BASE_URL}/private/conversations/{conversation_id}/messages", json=message_data2, headers=headers2) as response:
            if response.status == 200:
                message = await response.json()
                print(f"✅ Message sent: {message['content']}")
            else:
                print(f"❌ Failed to send message from user2: {response.status}")
                error_text = await response.text()
                print(f"Error details: {error_text}")
                return
        
        # Test 8: Get or create conversation with specific user
        print("\n8. Testing get/create conversation with user...")
        
        async with session.get(f"{BASE_URL}/private/conversations/with/{user2_profile['id']}", headers=headers1) as response:
            if response.status == 200:
                conv = await response.json()
                print(f"✅ Got conversation with user2: ID {conv['id']}")
            else:
                print(f"❌ Failed to get conversation with user: {response.status}")
                return
        
        print("\n🎉 All private messaging tests passed!")
        print("\n📝 Next steps:")
        print("1. Start the backend server: python app.py")
        print("2. Start the frontend: npm run dev")
        print("3. Test private messaging in the browser")
        print("4. Use WebSocket connections for real-time private messaging")

if __name__ == "__main__":
    asyncio.run(test_private_messaging())
