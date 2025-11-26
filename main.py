import os
import asyncio
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Bot
from groq import AsyncGroq  # Import Groq Async Client

# --- YOUR CREDENTIALS ---
# (I used the ones from your setup.py since you mentioned they are safe to use)
API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
BOT_TOKEN = "YOUR_NEW_BOT_TOKEN_HERE"  # Make sure to put your Bot Token here or in Env Vars
OWNER_ID = 1723764689

# Environment variables
STRING_SESSION = os.environ.get('STRING_SESSION', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '') # Changed from GEMINI to GROQ

print("🤖 Starting AI Assistant (Groq Edition)...")

# ---------------- Database ---------------- #
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
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def save_message(user_id, username, message, is_bot):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversations (user_id, username, message, is_bot, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, message, is_bot, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_recent_conversation(user_id, limit=6):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute(
        "SELECT message, is_bot FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    )
    messages = c.fetchall()
    conn.close()
    
    conversation_text = ""
    for msg, is_bot in reversed(messages):
        sender = "🤖 AI" if is_bot else "👤 User"
        safe_msg = str(msg).replace('*', '').replace('_', '')
        conversation_text += f"{sender}: {safe_msg}\n"
    
    return conversation_text

async def send_report_to_owner(username, user_id):
    try:
        conversation_text = get_recent_conversation(user_id, limit=8)
        summary = f"Conversation with {username}"
        report = f"""📊 DM CONVERSATION REPORT

👤 User: {username} (ID: {user_id})
📝 Context: {summary}

Recent Conversation:
{conversation_text}

Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        # Only send if BOT_TOKEN is set
        if BOT_TOKEN and BOT_TOKEN != "YOUR_NEW_BOT_TOKEN_HERE":
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(chat_id=OWNER_ID, text=report)
    except Exception as e:
        print(f"❌ Error sending report: {e}")

# ---------------- AI Client (Groq Implementation) ---------------- #
class GroqAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.conversations = {}  # Dictionary to store chat history per user
        
        if self.api_key:
            try:
                # Initialize AsyncGroq client
                self.client = AsyncGroq(api_key=self.api_key)
                # Model selection: llama-3.3-70b-versatile is smart and efficient
                # Alternatives: llama3-8b-8192 (faster/cheaper), mixtral-8x7b-32768
                self.model_name = "llama-3.3-70b-versatile" 
                print("✅ Groq Service Configured")
            except Exception as e:
                print(f"❌ Failed to configure Groq: {e}")
                self.client = None
        else:
            print("❌ Groq API Key Not Set")
            self.client = None

    async def generate_response(self, user_id, user_message):
        if not self.client:
            return self.get_smart_fallback(user_message)

        # Initialize history for new users
        if user_id not in self.conversations:
            self.conversations[user_id] = []

        # Construct the messages list for the API
        # 1. System Prompt
        messages = [{
            "role": "system",
            "content": """You are a personal AI assistant for a Telegram user. They are offline.
Role: Reply on their behalf. Be friendly, chill, and concise.
Do not sound robotic. Do not say "I am an AI" unless asked.
Keep responses short (1-2 sentences)."""
        }]

        # 2. Add recent history (last 4 interactions)
        # We store history as dictionaries in self.conversations now
        history = self.conversations[user_id][-8:] # Keep last 8 messages
        messages.extend(history)

        # 3. Add current user message
        messages.append({"role": "user", "content": user_message})

        try:
            print("🤖 Sending request to Groq...")
            completion = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=150,
                top_p=1,
            )
            
            ai_text = completion.choices[0].message.content
            
            if ai_text:
                ai_text = ai_text.strip()
                print("✅ Groq replied successfully")
                
                # Update internal history with dict objects
                self.conversations[user_id].append({"role": "user", "content": user_message})
                self.conversations[user_id].append({"role": "assistant", "content": ai_text})
                
                # Prune history if it gets too long to save memory
                if len(self.conversations[user_id]) > 10:
                    self.conversations[user_id] = self.conversations[user_id][-10:]
                
                return ai_text
                
        except Exception as e:
            print(f"❌ Groq API Error: {str(e)}")
            if "429" in str(e):
                print("⚠️ Rate limit exceeded.")
        
        # Fallback if API fails
        return self.get_smart_fallback(user_message)

    def get_smart_fallback(self, user_message):
        message = user_message.lower().strip()
        if any(word in message for word in ['hi', 'hello', 'hey', 'sup']):
            return "Hey! I'm an AI assistant covering while the owner is offline. Need anything?"
        elif 'how are you' in message:
            return "I'm good! Just holding down the fort. You?"
        elif 'who are you' in message:
            return "I'm an automated assistant replying while the owner is away."
        elif len(message) < 3:
            return "👍"
        else:
            return "I'm currently offline but I'll see this message as soon as I'm back!"

# Initialize AI client
ai_client = GroqAIClient(GROQ_API_KEY)

# ---------------- Telegram Client ---------------- #
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    # Don't reply to yourself or other bots (optional)
    if event.sender_id == OWNER_ID:
        return

    user = await event.get_sender()
    # Handle cases where user might be None or deleted
    if not user:
        return
        
    username = user.username or user.first_name or f"User{event.sender_id}"
    message_text = event.message.text
    
    print(f"📩 New from {username}: {message_text}")

    # Save incoming
    save_message(event.sender_id, username, message_text, False)

    # Simulate typing
    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(1.5) 
        ai_response = await ai_client.generate_response(event.sender_id, message_text)

    print(f"   💬 AI Reply: {ai_response}")

    # Send response
    await event.reply(ai_response)
    save_message(event.sender_id, username, ai_response, True)

    # Send report in background
    asyncio.create_task(send_report_to_owner(username, event.sender_id))

# ---------------- Main ---------------- #
async def main():
    init_db()

    print("🔑 Starting Telegram client...")
    if not STRING_SESSION:
        print("❌ STRING_SESSION missing")
        return
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY missing")
        print("⚠️ Please add GROQ_API_KEY to your Railway Variables")
        return

    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ Logged in as: {me.first_name}")
        print("👤 Bot is running...")
    except Exception as e:
        print(f"❌ Error starting client: {e}")
        return

    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())