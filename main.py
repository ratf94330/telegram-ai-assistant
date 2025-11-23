import os
import asyncio
import sqlite3
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import User, UserStatusOnline, UserStatusOffline
import requests
from telegram import Bot
import time

# Your actual credentials
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

    def generate_response(self, text):
        try:
            prompt = f"User: {text}\nAI:"
            
            payload = {
                "inputs": prompt,
                "parameters": {"max_length": 150, "temperature": 0.7}
            }
            
            response = requests.post(self.conversation_url, headers=self.headers, json=payload)
            result = response.json()
            
            if 'generated_text' in result:
                full_text = result['generated_text']
                if "AI:" in full_text:
                    return full_text.split("AI:")[-1].strip()
                return full_text.replace(prompt, "").strip()
            else:
                return "Hello! I'm assisting while the account owner is offline. How can I help you?"
                
        except Exception as e:
            print(f"❌ AI Error: {e}")
            return "I'm here to assist you! What would you like to talk about?"

    def summarize_conversation(self, conversation_text):
        try:
            if len(conversation_text) > 800:
                conversation_text = conversation_text[:800]
                
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

def get_recent_conversation(user_id, limit=5):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("SELECT message, is_bot FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", 
              (user_id, limit))
    messages = c.fetchall()
    conn.close()
    
    conversation_text = ""
    for msg, is_bot in reversed(messages):
        sender = "AI" if is_bot else "User"
        conversation_text += f"{sender}: {msg}\n"
    
    return conversation_text

def update_user_status(user_id, is_online):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("REPLACE INTO user_status VALUES (?, ?, ?)", 
              (user_id, datetime.now(), is_online))
    conn.commit()
    conn.close()

async def send_report_to_owner(username, user_id):
    """Send conversation summary to owner via bot"""
    try:
        conversation_text = get_recent_conversation(user_id, limit=10)
        summary = ai_client.summarize_conversation(conversation_text)
        
        report = f"""📊 *DM CONVERSATION REPORT*

👤 *User*: {username} (ID: {user_id})
📝 *Summary*: {summary}

*Recent Conversation:*
{conversation_text}

*Report Time*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=OWNER_ID, text=report, parse_mode='Markdown')
        print(f"✅ Report sent to owner for conversation with {username}")
    except Exception as e:
        print(f"❌ Error sending report: {e}")

# Create a unique session name for Railway
session_name = f"railway_session_{OWNER_ID}"

# Telegram Client for your personal account
client = TelegramClient(session_name, API_ID, API_HASH)

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
    
    # SIMPLIFIED: Always respond (we'll improve online detection later)
    # For now, we'll assume you're offline when the bot is running
    
    print(f"   🤖 AI responding to {username}")
    
    # Save incoming message
    save_message(event.sender_id, username, message_text, False)
    
    # Generate AI response
    ai_response = ai_client.generate_response(message_text)
    
    # Send response with different formatting
    await event.reply(f"`{ai_response}`", parse_mode='markdown')
    
    # Save AI response
    save_message(event.sender_id, username, ai_response, True)
    
    # Send report to owner
    await asyncio.sleep(2)
    await send_report_to_owner(username, event.sender_id)

async def main():
    # Initialize database
    init_db()
    
    print("🔑 Starting Telegram client...")
    
    try:
        # Start the client
        await client.start()
        
        # Get user info
        me = await client.get_me()
        print(f"✅ Logged in as: {me.first_name} (ID: {me.id})")
        
        # Set initial status
        update_user_status(OWNER_ID, False)
        print("👤 Bot is running and will respond to messages")
        
    except Exception as e:
        print(f"❌ Error starting client: {e}")
        print("💡 If you see 'AuthKeyDuplicatedError', wait a few minutes and restart")
        return
    
    print("\n" + "="*50)
    print("🤖 AI Assistant ACTIVE for your personal Telegram!")
    print("💬 AI will respond to DMs")
    print("📊 You'll receive summaries via @Dr_assistbot")
    print("="*50 + "\n")
    
    # Keep running
    try:
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Client disconnected: {e}")
        print("🔄 Restarting in 10 seconds...")
        await asyncio.sleep(10)
        await main()

if __name__ == '__main__':
    asyncio.run(main())