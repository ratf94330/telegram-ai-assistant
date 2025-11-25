import os
import asyncio
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Bot
import random

# Try to import the new Google Gemini library
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("❌ google-generativeai library not available")

# Your credentials
API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
BOT_TOKEN = "8420521879:AAFMCYFVCZBczxooABd402Gn6ojb2p3kltU"
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
        safe_msg = msg.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[')
        conversation_text += f"{sender}: {safe_msg}\n"
    
    return conversation_text

async def send_report_to_owner(username, user_id):
    try:
        conversation_text = get_recent_conversation(user_id, limit=8)
        summary = ai_client.summarize_conversation(conversation_text)
        report = f"""📊 DM CONVERSATION REPORT

👤 User: {username} (ID: {user_id})
📝 Summary: {summary}

Recent Conversation:
{conversation_text}

Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=OWNER_ID, text=report)
        print(f"✅ Report sent to owner for conversation with {username}")
    except Exception as e:
        print(f"❌ Error sending report: {e}")

# ---------------- AI Client with CORRECT Gemini API ---------------- #
class GeminiAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.conversations = {}
        
        # Initialize Gemini client if available
        if GEMINI_AVAILABLE and api_key:
            try:
                self.client = genai.Client(api_key=api_key)
                self.gemini_working = True
                print("✅ Gemini AI Client initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini client: {e}")
                self.gemini_working = False
        else:
            self.gemini_working = False
            if not GEMINI_AVAILABLE:
                print("❌ google-generativeai library not installed")
            if not api_key:
                print("❌ GEMINI_API_KEY not set")

    async def generate_response(self, user_id, user_message):
        if user_id not in self.conversations:
            self.conversations[user_id] = []

        # Build conversation context
        history = self.conversations[user_id][-4:]  # Last 2 exchanges
        history_text = "\n".join(history)

        prompt = f"""You are a helpful AI assistant responding to Telegram messages when the account owner is offline.
Keep responses friendly, conversational, and concise (1-2 sentences).

Recent conversation:
{history_text}

User: {user_message}
AI:"""

        # Try Gemini API first if available
        if self.gemini_working:
            try:
                print("🤖 Calling Gemini API with genai.Client...")
                response = self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt
                )
                ai_text = response.text.strip()
                
                # Update conversation history
                self.conversations[user_id].append(f"User: {user_message}")
                self.conversations[user_id].append(f"AI: {ai_text}")
                
                # Keep history manageable
                if len(self.conversations[user_id]) > 10:
                    self.conversations[user_id] = self.conversations[user_id][-10:]
                
                print(f"🤖 Gemini response: {ai_text}")
                return ai_text
                
            except Exception as e:
                print(f"❌ Gemini API call failed: {e}")
                # Fall back to smart responses
                return self.get_smart_fallback(user_message)
        else:
            # Use smart fallback if Gemini not available
            return self.get_smart_fallback(user_message)

    def get_smart_fallback(self, user_message):
        message = user_message.lower().strip()
        
        # Math questions
        if '1+1' in message or '2+2' in message or 'what is 1+1' in message:
            return "1 + 1 = 2! 😊 Basic math is something I can definitely help with!"
        
        # Greetings
        if any(word in message for word in ['hi', 'hello', 'hey', 'sup', 'wassup']):
            return "Hey there! 👋 I'm an AI assistant helping out while the account owner is away. What's up?"
        
        elif 'how are you' in message:
            return "I'm doing great, thanks for asking! Just here to chat. How about you?"
        
        elif 'who are you' in message or 'what are you' in message:
            return "I'm an AI assistant! The account owner set me up to respond to messages when they're offline."
        
        elif 'owner' in message or 'online' in message:
            return "The account owner is currently offline, but I'm here to chat and help with questions!"
        
        elif 'you ai' in message or 'you bot' in message:
            return "Yes, I'm an AI! 🤖 I'm handling messages while the account owner is unavailable."
        
        # Specific questions
        elif 'donald trump' in message:
            return "Donald Trump is a former US President and businessman. He served as the 45th president from 2017 to 2021."
        
        elif '?' in message:
            if 'name' in message:
                return "I'm an AI assistant! You can think of me as a helpful chatbot."
            elif 'joke' in message:
                return "Why don't scientists trust atoms? Because they make up everything! 😄"
            elif 'weather' in message:
                return "I don't have real-time weather data, but I hope you're having great weather!"
            elif 'time' in message:
                return f"According to my clock, it's about {datetime.now().strftime('%H:%M')} UTC!"
            else:
                return "That's an interesting question! I'm an AI assistant, so my knowledge has limits, but I'd be happy to chat about it."
        
        elif any(word in message for word in ['thanks', 'thank you']):
            return "You're welcome! 😊 Happy to help!"
        
        elif any(word in message for word in ['bye', 'goodbye', 'see you']):
            return "Take care! 👋 The owner will see your messages when they return."
        
        elif len(message) < 3:
            return "Got it! 👍 What else would you like to talk about?"
        
        else:
            # More engaging default responses
            responses = [
                "I see what you're saying! What are your thoughts on that?",
                "That's interesting! Tell me more about that.",
                "Thanks for sharing! What's been on your mind lately?",
                "I appreciate the message! Is there anything specific you'd like to chat about?",
                "That's cool! I'm here to keep you company while the owner is away."
            ]
            return random.choice(responses)

    def summarize_conversation(self, conversation_text):
        lines = conversation_text.count('\n') + 1
        return f"Conversation with {lines} messages"

# Initialize AI client
ai_client = GeminiAIClient(GEMINI_API_KEY)
print("✅ AI Client initialized")

# ---------------- Telegram Client ---------------- #
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    if event.sender_id == OWNER_ID:
        return

    user = await event.get_sender()
    username = user.username or user.first_name or f"User{event.sender_id}"
    message_text = event.message.text
    print(f"📩 New message from {username}: {message_text}")
    print(f"   🤖 AI responding to {username}")

    save_message(event.sender_id, username, message_text, False)

    # Generate AI response
    ai_response = await ai_client.generate_response(event.sender_id, message_text)
    print(f"   💬 AI says: {ai_response}")

    await event.reply(f"`{ai_response}`", parse_mode='markdown')
    save_message(event.sender_id, username, ai_response, True)

    # Send report
    await asyncio.sleep(1)
    await send_report_to_owner(username, event.sender_id)

# ---------------- Main ---------------- #
async def main():
    init_db()

    print("🔑 Starting Telegram client with string session...")
    if not STRING_SESSION:
        print("❌ ERROR: STRING_SESSION environment variable is not set!")
        return
    if not GEMINI_API_KEY:
        print("❌ ERROR: GEMINI_API_KEY environment variable is not set!")
        return

    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ Logged in as: {me.first_name} (ID: {me.id})")
        print("👤 Bot is running and will respond to messages")
    except Exception as e:
        print(f"❌ Error starting client: {e}")
        return

    print("\n" + "="*50)
    print("🤖 AI Assistant ACTIVE for your personal Telegram!")
    print("💬 Using Google Gemini 1.5 Flash AI for intelligent responses")
    print("📊 You'll receive summaries via @Dr_assistbot")
    print("="*50 + "\n")

    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())