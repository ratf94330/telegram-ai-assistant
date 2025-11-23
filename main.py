import os
import asyncio
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import requests
from telegram import Bot
import json

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

# Improved Hugging Face AI Client
class FreeAIClient:
    def __init__(self, token):
        self.token = token
        self.conversation_url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        self.summary_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        self.headers = {"Authorization": f"Bearer {token}"}

    def generate_response(self, text):
        try:
            # More natural conversation prompt
            prompt = f"The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.\n\nHuman: {text}\nAI:"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 100,
                    "temperature": 0.9,
                    "do_sample": True,
                    "top_p": 0.95,
                    "repetition_penalty": 1.1
                }
            }
            
            print(f"🤖 Sending request to Hugging Face...")
            response = requests.post(self.conversation_url, headers=self.headers, json=payload, timeout=30)
            print(f"🤖 Response status: {response.status_code}")
            
            result = response.json()
            print(f"🤖 Raw API response: {result}")
            
            if response.status_code == 503:
                return "I'm currently warming up. Please try again in a moment!"
            
            if isinstance(result, list) and len(result) > 0:
                if 'generated_text' in result[0]:
                    full_text = result[0]['generated_text']
                    # Extract the AI response part
                    if "AI:" in full_text:
                        ai_part = full_text.split("AI:")[-1].strip()
                        # Clean up any remaining Human: parts
                        if "Human:" in ai_part:
                            ai_part = ai_part.split("Human:")[0].strip()
                        return ai_part if ai_part else "Hey there! What's on your mind?"
                    return full_text.replace(prompt, "").strip() or "Hey! How can I help you today?"
            
            # If we get here, try a simpler approach
            return self.get_fallback_response(text)
                
        except Exception as e:
            print(f"❌ AI Error: {e}")
            return self.get_fallback_response(text)

    def get_fallback_response(self, text):
        """Generate context-aware fallback responses"""
        text_lower = text.lower().strip()
        
        # Greetings
        if any(word in text_lower for word in ['hi', 'hello', 'hey', 'sup', 'wassup', 'waruup']):
            return "Hey there! 👋 How's your day going?"
        
        # How are you
        elif any(phrase in text_lower for phrase in ['how are you', 'how you', "what's up"]):
            return "I'm doing great! Just here to chat while my owner is away. What about you?"
        
        # Questions
        elif '?' in text:
            return "That's an interesting question! I'm still learning, but I'd love to hear your thoughts on it."
        
        # Short messages
        elif len(text) < 3:
            return "I see you're keeping it short! 😄 What's on your mind?"
        
        # Default friendly response
        else:
            responses = [
                "That's interesting! Tell me more about that.",
                "I appreciate you sharing that with me!",
                "What do you think about that?",
                "That's really cool! I'd love to hear more.",
                "Thanks for the message! What's been on your mind lately?"
            ]
            import random
            return random.choice(responses)

    def summarize_conversation(self, conversation_text):
        try:
            if len(conversation_text) > 500:
                conversation_text = conversation_text[:500]
                
            payload = {"inputs": conversation_text}
            
            response = requests.post(self.summary_url, headers=self.headers, json=payload, timeout=30)
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0 and 'summary_text' in result[0]:
                return result[0]['summary_text']
            return "Had a friendly conversation."
            
        except Exception as e:
            print(f"❌ Summary Error: {e}")
            return "Friendly chat completed."

# Initialize AI client
ai_client = FreeAIClient(HUGGINGFACE_TOKEN)
print("✅ AI Client initialized")

def save_message(user_id, username, message, is_bot):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, username, message, is_bot, timestamp) VALUES (?, ?, ?, ?, ?)",
              (user_id, username, message, is_bot, datetime.now().isoformat()))
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

async def send_report_to_owner(username, user_id):
    """Send conversation summary to owner via bot"""
    try:
        conversation_text = get_recent_conversation(user_id, limit=10)
        summary = ai_client.summarize_conversation(conversation_text)
        
        # Fix Markdown formatting by escaping special characters
        safe_conversation = conversation_text.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
        
        report = f"""📊 *DM CONVERSATION REPORT*

👤 *User*: {username} (ID: {user_id})
📝 *Summary*: {summary}

*Recent Conversation:*
{safe_conversation}

*Report Time*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=OWNER_ID, text=report, parse_mode='Markdown')
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
    
    # For now, respond to all messages
    print(f"   🤖 AI responding to {username}")
    
    # Save incoming message
    save_message(event.sender_id, username, message_text, False)
    
    # Generate AI response
    ai_response = ai_client.generate_response(message_text)
    
    print(f"   💬 AI says: {ai_response}")
    
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