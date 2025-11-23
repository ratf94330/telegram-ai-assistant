import os
import asyncio
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import requests
from telegram import Bot
import random

# Your actual credentials
API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
BOT_TOKEN = "8420521879:AAFMCYFVCZBczxooABd402Gn6ojb2p3kltU"
HUGGINGFACE_TOKEN = "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"
OWNER_ID = 1723764689

# String session from environment variable
STRING_SESSION = os.environ.get('STRING_SESSION', '')

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
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# Improved AI Client with better fallbacks
class AIClient:
    def __init__(self, token):
        self.token = token
        # Updated Hugging Face endpoints
        self.conversation_url = "https://router.huggingface.co/models/microsoft/DialoGPT-medium"
        self.summary_url = "https://router.huggingface.co/models/facebook/bart-large-cnn"
        self.headers = {"Authorization": f"Bearer {token}"}

    def generate_response(self, text):
        try:
            # Try the new Hugging Face endpoint first
            prompt = f"User: {text}\nAI:"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 80,
                    "temperature": 0.8,
                    "do_sample": True
                }
            }
            
            print(f"🤖 Trying new Hugging Face endpoint...")
            response = requests.post(self.conversation_url, headers=self.headers, json=payload, timeout=15)
            print(f"🤖 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"🤖 API response: {result}")
                
                if isinstance(result, list) and len(result) > 0:
                    if 'generated_text' in result[0]:
                        full_text = result[0]['generated_text']
                        if "AI:" in full_text:
                            ai_response = full_text.split("AI:")[-1].strip()
                            # Clean up the response
                            if "User:" in ai_response:
                                ai_response = ai_response.split("User:")[0].strip()
                            return ai_response
            
            # If Hugging Face fails, use our smart fallback
            return self.get_smart_response(text)
                
        except Exception as e:
            print(f"❌ API Error: {e}")
            return self.get_smart_response(text)

    def get_smart_response(self, user_message):
        """Generate intelligent, context-aware responses without API"""
        message = user_message.lower().strip()
        
        # Greetings
        greetings = ['hi', 'hello', 'hey', 'sup', 'wassup', 'waruup', 'yo', 'hola']
        if any(greet in message for greet in greetings):
            return random.choice([
                "Hey there! 👋 How's your day going?",
                "Hello! Nice to hear from you!",
                "Hi! What's on your mind today?",
                "Hey! How can I help you? 😊"
            ])
        
        # How are you
        if any(phrase in message for phrase in ['how are you', 'how you', "what's up", 'how do you do']):
            return random.choice([
                "I'm doing great! Just here to chat. How about you?",
                "All good on my end! What's new with you?",
                "I'm functioning perfectly! How are things with you?",
                "Doing well, thanks for asking! How's your day going?"
            ])
        
        # Questions about AI/identity
        if any(phrase in message for phrase in ['are you ai', 'are you a robot', 'are you bot', 'who are you']):
            return random.choice([
                "I'm an AI assistant helping out while my owner is away! 🤖",
                "Yep, I'm an AI! Just keeping the conversations flowing.",
                "I'm an automated assistant chatting with you right now!",
                "That's right! I'm an AI helping with messages."
            ])
        
        # Questions about owner
        if any(phrase in message for phrase in ['owner', 'where is', 'when will', 'is he', 'is she']):
            return random.choice([
                "The account owner is currently unavailable, but I'm here to help!",
                "They're away at the moment, but I can assist you with anything.",
                "I'm handling messages while they're offline. What can I help with?",
                "They're not available right now, but I'd be happy to chat!"
            ])
        
        # Jokes
        if 'joke' in message:
            jokes = [
                "Why don't scientists trust atoms? Because they make up everything!",
                "Why did the scarecrow win an award? He was outstanding in his field!",
                "What do you call a fake noodle? An impasta!",
                "Why did the math book look so sad? Because it had too many problems!"
            ]
            return random.choice(jokes)
        
        # Help/questions
        if '?' in message:
            return random.choice([
                "That's an interesting question! What are your thoughts on it?",
                "I'm still learning about that topic. What do you think?",
                "That's a great question! I'd love to hear your perspective.",
                "I'm not entirely sure about that one. Maybe we can explore it together?"
            ])
        
        # Short messages
        if len(message) <= 2:
            return random.choice([
                "I see you're keeping it brief! 😄",
                "Short and sweet! What's on your mind?",
                "Got it! Anything else you'd like to talk about?",
                "👍 What's new with you?"
            ])
        
        # Confusion/negative
        if any(word in message for word in ['huh', 'what', 'weird', 'strange', 'confused']):
            return random.choice([
                "Sorry if I confused you! Let me know what you meant.",
                "My apologies! Could you rephrase that?",
                "I think I misunderstood. What were you saying?",
                "Let's try that again! What did you mean?"
            ])
        
        # Default positive responses
        positive_responses = [
            "That's really interesting! Tell me more about that.",
            "I appreciate you sharing that! What's been on your mind lately?",
            "That's cool! I'd love to hear more about your thoughts.",
            "Thanks for the message! What else is going on with you?",
            "That's fascinating! How do you feel about that?",
            "I like that perspective! What made you think of it?"
        ]
        return random.choice(positive_responses)

    def summarize_conversation(self, conversation_text):
        # Simple summary since Hugging Face might not work
        lines = conversation_text.split('\n')
        if len(lines) >= 4:
            return f"Conversation with {len(lines)//2} messages about various topics"
        return "Short conversation exchange"

# Initialize AI client
ai_client = AIClient(HUGGINGFACE_TOKEN)
print("✅ AI Client initialized")

def save_message(user_id, username, message, is_bot):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, username, message, is_bot, timestamp) VALUES (?, ?, ?, ?, ?)",
              (user_id, username, message, is_bot, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_recent_conversation(user_id, limit=6):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("SELECT message, is_bot FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", 
              (user_id, limit))
    messages = c.fetchall()
    conn.close()
    
    conversation_text = ""
    for msg, is_bot in reversed(messages):
        sender = "🤖 AI" if is_bot else "👤 User"
        # Escape Markdown characters
        safe_msg = msg.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[')
        conversation_text += f"{sender}: {safe_msg}\n"
    
    return conversation_text

async def send_report_to_owner(username, user_id):
    """Send conversation summary to owner via bot"""
    try:
        conversation_text = get_recent_conversation(user_id, limit=8)
        summary = ai_client.summarize_conversation(conversation_text)
        
        # Create report without Markdown to avoid parsing errors
        report = f"""📊 DM CONVERSATION REPORT

👤 User: {username} (ID: {user_id})
📝 Summary: {summary}

Recent Conversation:
{conversation_text}

Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        bot = Bot(token=BOT_TOKEN)
        # Send without Markdown parsing
        await bot.send_message(chat_id=OWNER_ID, text=report)
        print(f"✅ Report sent to owner for conversation with {username}")
    except Exception as e:
        print(f"❌ Error sending report: {e}")

# Create Telegram client with string session
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

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
    
    print(f"📩 New message from {username}: {message_text}")
    
    # Respond to all messages for now
    print(f"   🤖 AI responding to {username}")
    
    # Save incoming message
    save_message(event.sender_id, username, message_text, False)
    
    # Generate AI response
    ai_response = ai_client.generate_response(message_text)
    
    print(f"   💬 AI says: {ai_response}")
    
    # Send response with code formatting
    await event.reply(f"`{ai_response}`", parse_mode='markdown')
    
    # Save AI response
    save_message(event.sender_id, username, ai_response, True)
    
    # Send report to owner
    await asyncio.sleep(1)
    await send_report_to_owner(username, event.sender_id)

async def main():
    # Initialize database
    init_db()
    
    print("🔑 Starting Telegram client with string session...")
    
    if not STRING_SESSION:
        print("❌ ERROR: STRING_SESSION environment variable is not set!")
        return
    
    try:
        # Start the client
        await client.start()
        
        # Get user info
        me = await client.get_me()
        print(f"✅ Logged in as: {me.first_name} (ID: {me.id})")
        print("👤 Bot is running and will respond to messages")
        
    except Exception as e:
        print(f"❌ Error starting client: {e}")
        return
    
    print("\n" + "="*50)
    print("🤖 AI Assistant ACTIVE for your personal Telegram!")
    print("💬 AI will respond to DMs")
    print("📊 You'll receive summaries via @Dr_assistbot")
    print("="*50 + "\n")
    
    # Keep running
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())