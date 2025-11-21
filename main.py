import os
import asyncio
import sqlite3
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import User, UserStatusOnline, UserStatusOffline
import requests
from telegram import Bot
import time

# Your actual credentials - I'm including them directly
API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
BOT_TOKEN = "8420521879:AAFMCYFVCZBczxooABd402Gn6ojb2p3kltU"
HUGGINGFACE_TOKEN = "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"
OWNER_ID = 1723764689

print("🤖 Starting AI Assistant for your personal Telegram account...")

# Initialize database
def init_db():
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER, 
                  username TEXT, 
                  message TEXT, 
                  is_bot BOOLEAN, 
                  timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_status
                 (user_id INTEGER PRIMARY KEY, 
                  last_online DATETIME, 
                  is_online BOOLEAN)''')
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# Hugging Face AI Client
class FreeAIClient:
    def __init__(self, token):
        self.token = token
        self.conversation_url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        self.summary_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        self.headers = {"Authorization": f"Bearer {token}"}

    def generate_response(self, text, conversation_history=[]):
        try:
            # Prepare conversation history
            past_user_inputs = [msg["text"] for msg in conversation_history if not msg["is_bot"]][-3:]
            generated_responses = [msg["text"] for msg in conversation_history if msg["is_bot"]][-3:]
            
            payload = {
                "inputs": {
                    "text": text,
                    "past_user_inputs": past_user_inputs,
                    "generated_responses": generated_responses
                }
            }
            
            response = requests.post(self.conversation_url, headers=self.headers, json=payload)
            result = response.json()
            
            if 'generated_text' in result:
                return result['generated_text']
            elif 'error' in result:
                return "I'm processing your request. Please try again in a moment."
            else:
                return "Hello! I'm assisting while the account owner is offline. How can I help you?"
                
        except Exception as e:
            print(f"❌ AI Error: {e}")
            return "I'm here to assist you! What would you like to talk about?"

    def summarize_conversation(self, conversation_text):
        try:
            if len(conversation_text) > 1000:
                conversation_text = conversation_text[:1000]
                
            payload = {"inputs": conversation_text}
            
            response = requests.post(self.summary_url, headers=self.headers, json=payload)
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0 and 'summary_text' in result[0]:
                return result[0]['summary_text']
            return "Conversation completed."
            
        except Exception as e:
            print(f"❌ Summary Error: {e}")
            return "Conversation ended."

# Initialize AI client
ai_client = FreeAIClient(HUGGINGFACE_TOKEN)
print("✅ AI Client initialized")

def save_message(user_id, username, message, is_bot):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, username, message, is_bot, timestamp) VALUES (?, ?, ?, ?, ?)",
              (user_id, username, message, is_bot, datetime.now()))
    conn.commit()
    conn.close()

def get_conversation_history(user_id, limit=6):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("SELECT message, is_bot FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", 
              (user_id, limit))
    history = [{"text": row[0], "is_bot": row[1]} for row in c.fetchall()]
    conn.close()
    return history[::-1]  # Reverse to get chronological order

def update_user_status(user_id, is_online):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("REPLACE INTO user_status VALUES (?, ?, ?)", 
              (user_id, datetime.now(), is_online))
    conn.commit()
    conn.close()

def is_user_online(user_id):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("SELECT last_online, is_online FROM user_status WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return False
    
    last_online, is_online = result
    if isinstance(last_online, str):
        last_online = datetime.fromisoformat(last_online)
    
    # Consider offline if last seen > 3 minutes ago
    if datetime.now() - last_online > timedelta(minutes=3):
        return False
    return bool(is_online)

async def send_report_to_owner(conversation_text, username, user_id):
    """Send conversation summary to owner via bot"""
    try:
        summary = ai_client.summarize_conversation(conversation_text)
        
        report = f"""📊 *DM CONVERSATION REPORT*

👤 *User*: {username} (ID: {user_id})
📝 *Summary*: {summary}

*Conversation:*
{conversation_text}

*Report Time*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=OWNER_ID, text=report, parse_mode='Markdown')
        print(f"✅ Report sent to owner for conversation with {username}")
    except Exception as e:
        print(f"❌ Error sending report: {e}")

# Track owner online status
owner_online = False

# Telegram Client for your personal account
client = TelegramClient('user_session', API_ID, API_HASH)

@client.on(events.UserUpdate)
async def handler(event):
    """Track when you come online/offline"""
    global owner_online
    
    if event.original_update.user_id == OWNER_ID:
        user = await client.get_entity(OWNER_ID)
        if hasattr(user, 'status'):
            if isinstance(user.status, UserStatusOnline):
                owner_online = True
                update_user_status(OWNER_ID, True)
                print("👤 Owner is ONLINE - AI won't respond to new messages")
            elif isinstance(user.status, UserStatusOffline):
                owner_online = False
                update_user_status(OWNER_ID, False)
                print("👤 Owner is OFFLINE - AI will respond to new messages")
        else:
            # If we can't determine status, assume offline after some time
            owner_online = False
            update_user_status(OWNER_ID, False)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    """Handle incoming DMs to your personal account"""
    # Don't respond to yourself
    if event.sender_id == OWNER_ID:
        return
    
    # Get sender info
    user = await event.get_sender()
    username = user.username or user.first_name or f"User{event.sender_id}"
    message_text = event.message.text
    
    print(f"📩 New message from {username}: {message_text[:50]}...")
    
    # Check if owner is online
    if owner_online:
        print(f"   ⏸️ Owner is online - ignoring message from {username}")
        return
    
    print(f"   🤖 Owner is offline - AI responding to {username}")
    
    # Save incoming message
    save_message(event.sender_id, username, message_text, False)
    
    # Get conversation history
    history = get_conversation_history(event.sender_id)
    
    # Generate AI response
    ai_response = ai_client.generate_response(message_text, history)
    
    # Send response with different formatting
    await event.reply(f"`{ai_response}`", parse_mode='markdown')
    
    # Save AI response
    save_message(event.sender_id, username, ai_response, True)
    
    # Prepare conversation for reporting
    full_history = get_conversation_history(event.sender_id, limit=10)
    conversation_text = "\n".join([
        f"{'🤖 AI' if msg['is_bot'] else '👤 User'}: {msg['text']}" 
        for msg in full_history
    ])
    
    # Send report to owner (only if conversation has multiple messages)
    if len(full_history) >= 2:
        await send_report_to_owner(conversation_text, username, event.sender_id)

async def main():
    # Initialize database
    init_db()
    
    # Start the client
    await client.start()
    
    # Get initial owner status
    try:
        me = await client.get_me()
        print(f"✅ Logged in as: {me.first_name} (ID: {me.id})")
        
        # Check initial online status
        user = await client.get_entity(OWNER_ID)
        if hasattr(user, 'status'):
            if isinstance(user.status, UserStatusOnline):
                owner_online = True
                print("👤 Initial status: ONLINE")
            else:
                owner_online = False
                print("👤 Initial status: OFFLINE")
        
        update_user_status(OWNER_ID, owner_online)
        
    except Exception as e:
        print(f"❌ Error getting user info: {e}")
    
    print("\n" + "="*50)
    print("🤖 AI Assistant ACTIVE for your personal Telegram!")
    print("📱 Monitoring your online status...")
    print("💬 AI will respond to DMs when you're offline")
    print("📊 You'll receive summaries via @Dr_assistbot")
    print("="*50 + "\n")
    
    # Keep running
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
