import os
import asyncio
import sqlite3
import random
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Bot
from groq import AsyncGroq

# --- YOUR CREDENTIALS ---
API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
# Keep your existing Bot Token for reports
BOT_TOKEN = "YOUR_NEW_BOT_TOKEN_HERE" 
OWNER_ID = 1723764689
OWNER_NAME = "Habte"

# Environment variables
STRING_SESSION = os.environ.get('STRING_SESSION', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Global Game State Storage
games = {}

print(f"🤖 Starting {OWNER_NAME}'s Advanced AI Assistant...")

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

def save_message(user_id, username, message, is_bot):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, username, message, is_bot, timestamp) VALUES (?, ?, ?, ?, ?)",
              (user_id, username, message, is_bot, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ---------------- Game Logic (XO) ---------------- #
class TicTacToe:
    def __init__(self):
        self.board = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        self.turn = "X" # User is X
        self.active = True

    def draw_board(self):
        b = self.board
        return (f"` {b[0]} | {b[1]} | {b[2]} `\n"
                f"`---|---|---`\n"
                f"` {b[3]} | {b[4]} | {b[5]} `\n"
                f"`---|---|---`\n"
                f"` {b[6]} | {b[7]} | {b[8]} `")

    def make_move(self, position):
        idx = int(position) - 1
        if self.board[idx] in ["X", "O"]:
            return False, "Cell taken!"
        self.board[idx] = self.turn
        return True, "Moved"

    def check_winner(self):
        wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        for a,b,c in wins:
            if self.board[a] == self.board[b] == self.board[c]:
                return True, self.board[a]
        if all(x in ["X", "O"] for x in self.board):
            return True, "Draw"
        return False, None

    def bot_move(self):
        available = [i for i, x in enumerate(self.board) if x not in ["X", "O"]]
        if not available: return
        # Simple AI: Pick random
        choice = random.choice(available)
        self.board[choice] = "O"

# ---------------- AI Client ---------------- #
class GroqAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.conversations = {}
        if self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)
            self.model_name = "llama-3.3-70b-versatile" 
        else:
            self.client = None

    async def generate_response(self, user_id, user_message, username, is_dagm=False):
        if not self.client:
            return "System Error: Brain missing."

        if user_id not in self.conversations:
            self.conversations[user_id] = []

        # --- DYNAMIC PROMPT ENGINEERING ---
        time_now = datetime.now().strftime("%I:%M %p")
        
        # 1. Base Personality
        base_prompt = f"""You are an advanced AI assistant for {OWNER_NAME}. He is offline.
Your Name: 'Habte's AI'.
Style: Use a Monospace font style for your voice. Be witty, smart, and dynamic.
Current Time: {time_now}.
Constraint: Keep answers short (max 2 sentences)."""

        # 2. DAGM SPECIFIC LORE (The Secret Sauce)
        dagm_lore = """
SPECIAL USER ALERT: This is Dagi (aka Dagm). He is Habte's best friend.
PERSONALITY FOR DAGI:
- Call him Dagi or Dagm.
- Be funny, roasting, and brotherly.
- COFFEE: You know he drinks coffee every day (except Sundays) at 'Selam' in the afternoon. Ask if he's at Selam.
- ROMANCE: He wants to sleep with a girl named 'Mititi' (she has a big butt). He is too proud/shy to approach her. TEASE HIM. Tell him to just beg her because she probably wants him too.
- JUICE WAR: He loves Avocado juice at 'Acheto' (where the waiter brings vinegar/acheto first). Warn him that Habte hates it because it's expensive.
- YOGURT: Remind him Habte wants to go to 'Ashe' for yogurt, but Dagi always rejects it.
- INSULT: Call him a "simp" if he talks about Mititi.
"""

        # 3. Standard User Prompt
        standard_lore = f"""
Interact politely but coolly. If they ask where {OWNER_NAME} is, say he's busy conquering the world (or sleeping).
"""

        system_content = base_prompt + (dagm_lore if is_dagm else standard_lore)

        messages = [{"role": "system", "content": system_content}]
        messages.extend(self.conversations[user_id][-8:]) # Context
        messages.append({"role": "user", "content": user_message})

        try:
            completion = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.8, # Higher temp for more creativity
                max_tokens=200,
            )
            ai_text = completion.choices[0].message.content.strip()
            
            # Save to history
            self.conversations[user_id].append({"role": "user", "content": user_message})
            self.conversations[user_id].append({"role": "assistant", "content": ai_text})
            
            # Enforce Monospace if the AI didn't do it
            if not ai_text.startswith("`"):
                ai_text = f"`{ai_text}`"
            
            return ai_text
        except Exception as e:
            return f"`Error: {str(e)}`"

# Initialize
ai_client = GroqAIClient(GROQ_API_KEY)
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# ---------------- Message Handler ---------------- #
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    if event.sender_id == OWNER_ID: return

    user = await event.get_sender()
    sender_id = event.sender_id
    username = user.username or user.first_name
    msg = event.message.text.strip()
    
    # Check if it's the special friend
    is_dagm = False
    if username == "KOMASUN_MARKET" or "Komasun" in str(username):
        is_dagm = True
        username = "Dagi" # Force internal name

    print(f"📩 {username}: {msg}")
    save_message(sender_id, username, msg, False)

    # --- 1. GAME LOGIC (XO) ---
    if msg.lower() == "/xo":
        games[sender_id] = TicTacToe()
        await event.reply(f"`🎮 Tic-Tac-Toe Started!`\n`You are X. Reply 1-9.`\n\n" + games[sender_id].draw_board())
        return

    if sender_id in games and games[sender_id].active:
        if msg.isdigit() and 1 <= int(msg) <= 9:
            game = games[sender_id]
            success, info = game.make_move(msg)
            
            if success:
                # Check User Win
                is_over, winner = game.check_winner()
                if is_over:
                    game.active = False
                    del games[sender_id]
                    res = "🎉 YOU WON!" if winner == "X" else "😐 DRAW."
                    await event.reply(f"`{res}`\n\n" + game.draw_board())
                    return
                
                # Bot Move
                game.bot_move()
                is_over, winner = game.check_winner()
                if is_over:
                    game.active = False
                    del games[sender_id]
                    res = "🤖 I WON!" if winner == "O" else "😐 DRAW."
                    await event.reply(f"`{res}`\n\n" + game.draw_board())
                    return
                
                await event.reply(f"`Your turn (1-9):`\n\n" + game.draw_board())
                return
            else:
                await event.reply(f"`❌ Invalid move: {info}`")
                return
        elif msg.lower() == "stop":
            del games[sender_id]
            await event.reply("`🛑 Game stopped.`")
            return

    # --- 2. COMMANDS ---
    if msg.lower() == "/status":
        await event.reply(f"`🤖 SYSTEM ONLINE`\n`Owner: {OWNER_NAME}`\n`Model: Llama-3 70B`")
        return

    # --- 3. AI GENERATION ---
    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(random.uniform(1, 2)) # Human-like delay
        response = await ai_client.generate_response(sender_id, msg, username, is_dagm)

    await event.reply(response)
    save_message(sender_id, username, response, True)

# ---------------- Main ---------------- #
async def main():
    init_db()
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY missing")
        return

    print("✅ System Loaded.")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())