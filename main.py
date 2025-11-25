import os
import asyncio
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Bot
import random
import google.generativeai as genai # Import the official library

# --- YOUR CREDENTIALS (REPLACE THESE WITH NEW SECURE ONES) ---
API_ID = 26908211
API_HASH = "YOUR_NEW_API_HASH_HERE" 
BOT_TOKEN = "YOUR_NEW_BOT_TOKEN_HERE"
OWNER_ID = 1723764689

# Environment variables
STRING_SESSION = os.environ.get('STRING_SESSION', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

print("🤖 Starting AI Assistant for your personal Telegram account...")

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
        # Basic sanitization
        safe_msg = str(msg).replace('*', '').replace('_', '')
        conversation_text += f"{sender}: {safe_msg}\n"
    
    return conversation_text

async def send_report_to_owner(username, user_id):
    try:
        conversation_text = get_recent_conversation(user_id, limit=8)
        # Simple summary for the report
        summary = f"Conversation with {username}"
        report = f"""📊 DM CONVERSATION REPORT

👤 User: {username} (ID: {user_id})
📝 Context: {summary}

Recent Conversation:
{conversation_text}

Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=OWNER_ID, text=report)
    except Exception as e:
        print(f"❌ Error sending report: {e}")

# ---------------- AI Client (UPDATED) ---------------- #
class GeminiAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.conversations = {}
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Safety settings to prevent blocking harmless messages
                self.safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                self.model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=self.safety_settings)
                print("✅ Gemini Service Configured")
            except Exception as e:
                print(f"❌ Failed to configure Gemini: {e}")
                self.model = None
        else:
            print("❌ Gemini API Key Not Set")
            self.model = None

    async def generate_response(self, user_id, user_message):
        if user_id not in self.conversations:
            self.conversations[user_id] = []

        # Build history
        history = self.conversations[user_id][-4:]
        history_text = "\n".join(history)

        prompt = f"""You are a personal AI assistant for a Telegram user. They are offline.
Role: Reply on their behalf. Be friendly, chill, and concise.
Do not sound robotic. Do not say "I am an AI" unless asked.

Recent chat context:
{history_text}

Current User Message: {user_message}
Reply:"""

        # Try Google Gemini API using Official Library
        if self.model:
            try:
                print("🤖 Sending request to Gemini...")
                # Using async generation
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=150
                    )
                )
                
                if response.text:
                    ai_text = response.text.strip()
                    print("✅ Gemini replied successfully")
                    
                    # Update history
                    self.conversations[user_id].append(f"User: {user_message}")
                    self.conversations[user_id].append(f"AI: {ai_text}")
                    if len(self.conversations[user_id]) > 10:
                        self.conversations[user_id] = self.conversations[user_id][-10:]
                    
                    return ai_text
                    
            except Exception as e:
                print(f"❌ Gemini API Error: {str(e)}")
                # If error contains "429" it means quota exceeded
                if "429" in str(e):
                    print("⚠️ Quota exceeded. Switching to fallback.")
        
        # Fall back to smart responses if API fails or is missing
        print("⚠️ Using Fallback Responses")
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
ai_client = GeminiAIClient(GEMINI_API_KEY)

# ---------------- Telegram Client ---------------- #
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    # Don't reply to yourself
    if event.sender_id == OWNER_ID:
        return

    user = await event.get_sender()
    username = user.username or user.first_name or f"User{event.sender_id}"
    message_text = event.message.text
    
    print(f"📩 New from {username}: {message_text}")

    # Save incoming
    save_message(event.sender_id, username, message_text, False)

    # Simulate typing for realism
    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(1.5) # Wait a bit to look human
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
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY missing")
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
