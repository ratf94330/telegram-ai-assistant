import os
import asyncio
import sqlite3
import random
import math
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from groq import AsyncGroq

# --- YOUR CREDENTIALS ---
API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
BOT_TOKEN = "YOUR_NEW_BOT_TOKEN_HERE" # Not used for reports, but kept for convention
OWNER_ID = 1723764689
OWNER_NAME = "Habte"
OWNER_ALIAS = "Jalmaro" 

# Special Friend Usernames (Strictly enforced)
DAGM_USERNAME = "KOMASUN_MARKET"
ABI_USERNAME = "Contracttor"

# Environment variables
STRING_SESSION = os.environ.get('STRING_SESSION', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

print(f"🤖 Starting {OWNER_NAME}'s Advanced AI Assistant (Professional Mode)...")

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

# ---------------- GAME ENGINE (XO) ---------------- #
class TicTacToe:
    def __init__(self, difficulty="mid"):
        self.board = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        self.turn = "X" 
        self.active = True
        self.difficulty = difficulty

    def draw_board(self):
        b = self.board
        return (f"` {b[0]} | {b[1]} | {b[2]} `\n"
                f"`---|---|---`\n"
                f"` {b[3]} | {b[4]} | {b[5]} `\n"
                f"`---|---|---`\n"
                f"` {b[6]} | {b[7]} | {b[8]} `")

    def make_move(self, position):
        idx = int(position) - 1
        if self.board[idx] in ["X", "O"]: return False, "Cell taken!"
        self.board[idx] = self.turn
        return True, "Moved"

    def check_winner(self, board):
        wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        for a,b,c in wins:
            if board[a] == board[b] == board[c]: return True, board[a]
        if all(x in ["X", "O"] for x in board): return True, "Draw"
        return False, None

    # Minimax implementation for optimal play
    def minimax(self, board, depth, is_maximizing):
        is_over, winner = self.check_winner(board)
        if is_over:
            if winner == "O": return 10 - depth
            if winner == "X": return depth - 10
            return 0

        if is_maximizing:
            best_score = -math.inf
            for i in range(9):
                if board[i] not in ["X", "O"]:
                    temp = board[i]
                    board[i] = "O"
                    score = self.minimax(board, depth + 1, False)
                    board[i] = temp
                    best_score = max(score, best_score)
            return best_score
        else:
            best_score = math.inf
            for i in range(9):
                if board[i] not in ["X", "O"]:
                    temp = board[i]
                    board[i] = "X"
                    score = self.minimax(board, depth + 1, True)
                    board[i] = temp
                    best_score = min(score, best_score)
            return best_score

    def bot_move(self):
        available = [i for i, x in enumerate(self.board) if x not in ["X", "O"]]
        if not available: return

        choice = None
        
        if self.difficulty == "easy":
            choice = random.choice(available)
        
        elif self.difficulty == "mid":
            # 50% chance of optimal, 50% random
            if random.random() > 0.5:
                # Find best move (using minimax to simplify code)
                best_score = -math.inf
                for i in available:
                    self.board[i] = "O"
                    score = self.minimax(self.board, 0, False)
                    self.board[i] = str(i+1)
                    if score > best_score:
                        best_score = score
                        choice = i
            else:
                choice = random.choice(available)

        elif self.difficulty == "hard":
            best_score = -math.inf
            for i in available:
                self.board[i] = "O"
                score = self.minimax(self.board, 0, False)
                self.board[i] = str(i+1)
                if score > best_score:
                    best_score = score
                    choice = i
        
        if choice is None: choice = random.choice(available) 
        self.board[choice] = "O"

# Global Game State: Stores either TicTacToe instance or the string "awaiting_difficulty"
active_games = {} 

# ---------------- AI CLIENT & PERSONAS ---------------- #
class GroqAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.conversations = {}
        if self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)
            self.model_name = "llama-3.3-70b-versatile"
        else:
            self.client = None

    async def generate_response(self, user_id, user_message, raw_username, user_firstname):
        if not self.client: return "`System Error: Brain missing.`"
        if user_id not in self.conversations: self.conversations[user_id] = []

        # --- PERSONA IDENTIFICATION ---
        persona_type = "standard"
        if raw_username == DAGM_USERNAME: 
            persona_type = "dagm"
            username_alias = "Dagi/Dagm"
        elif raw_username == ABI_USERNAME: 
            persona_type = "abi"
            username_alias = "Abi/Naol"
        else:
            username_alias = user_firstname

        # --- DYNAMIC PROMPTS ---
        time_now = datetime.now().strftime("%I:%M %p")
        
        # Habte Glazing variations
        glaze_messages = [
            f"Note: {OWNER_NAME} is currently optimizing complex global simulations. He will return at his leisure.",
            f"Note: {OWNER_NAME} is busy achieving professional mastery; he is not available for immediate contact.",
            f"Note: {OWNER_NAME} is managing high-level strategic logistics. You may leave a message.",
            f"Note: {OWNER_NAME} is engaged in proprietary development that requires his full focus.",
        ]
        glaze = random.choice(glaze_messages)

        base = f"""You are {OWNER_NAME}'s professional AI assistant. 
Your Name: 'Habte's AI'.
Style: Use Monospace font for everything. Be witty, professional, and dynamic.
Time: {time_now}.
User: {username_alias}.
Constraint: Keep answers short (max 2 sentences).
{glaze}
"""

        # --- Dagm (KOMASUN_MARKET) LORE ---
        if persona_type == "dagm":
            lore = f"""
SPECIAL USER: {username_alias}. {OWNER_NAME}'s best friend.
TONE: Mocking, brotherly, teasing.
LORE:
1. He likes 'Selam' coffee (every day except Sunday after noon). Ask him if he is at Selam now.
2. CRUSH: 'Mititi' (Big butt). He is too proud/scared to approach. ROAST HIM. Tell him to beg her. Call him a simp.
3. DRINK: Loves expensive Avocado juice at 'Acheto' (waiter brings vinegar/acheto first). Warn him that {OWNER_NAME} prefers 'Ashe' yogurt but Dagi rejects it.
4. GIRLS: He stays quiet when {OWNER_NAME} and Abi glaze 'Habeshawi' (Queen of Sheba).
"""
        # --- Abi (Contracttor) LORE ---
        elif persona_type == "abi":
            lore = f"""
SPECIAL USER: {username_alias}. Dagm's older brother.
TONE: Teasing, challenging, supportive (in a rival way).
LORE:
1. LIKES: 'Hajiya' (Muslim girls) but scared to approach. Tease him gently.
2. EX-CRUSH: 'Marifa' (Mafu). He claims he's over her. HE IS LYING. TEASE HIM.
3. GAMING RIVALRY: He always loses to {OWNER_ALIAS} ({OWNER_NAME}) in Mini Militia and Joteni. He blames lag/device. MOCK HIS EXCUSES. Remind him {OWNER_NAME}'s COC account will destroy his 9+ yr account.
4. GIRLS AT SELAM: He talks about 'Snake'. He and {OWNER_NAME} glaze 'Habeshawi' (Queen of Sheba) together. MENTION THIS.
"""
        # --- Standard User Prompt ---
        else:
            lore = f"""
TONE: Formal and polite. Offer assistance or suggest he leave a concise message.
"""

        messages = [{"role": "system", "content": base + lore}]
        messages.extend(self.conversations[user_id][-8:])
        messages.append({"role": "user", "content": user_message})

        try:
            completion = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.8,
                max_tokens=200,
            )
            ai_text = completion.choices[0].message.content.strip()
            
            # Formatting check (Monospace)
            if not ai_text.startswith("`"): ai_text = f"`{ai_text}`"
            
            self.conversations[user_id].append({"role": "user", "content": user_message})
            self.conversations[user_id].append({"role": "assistant", "content": ai_text})
            
            return ai_text
        except Exception as e:
            return f"`Error: {str(e)}`"

# Initialize
ai_client = GroqAIClient(GROQ_API_KEY)
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# ---------------- EVENT HANDLER ---------------- #
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    if event.sender_id == OWNER_ID: return

    user = await event.get_sender()
    sender_id = event.message.peer_id.user_id
    raw_username = user.username 
    user_firstname = user.first_name

    msg = event.message.text.strip()
    save_message(sender_id, raw_username, msg, False)

    # --- COMMANDS & GREETING ---
    
    # 1. Greeting/Start
    if msg.lower() in ["/start", "hi", "hello", "hey"]:
        welcome = (
            f"`👋 Welcome. I am {OWNER_NAME}'s professional AI assistant. He is currently indisposed with vital engagements.`\n\n"
            f"`If you are waiting, you may try your skill against me in the XO game.`\n"
            f"[Start XO Game](/xo)"
        )
        await event.reply(welcome, parse_mode='Markdown')
        return

    # 2. XO Start - Difficulty Selection Flow
    if msg.lower() == "/xo":
        active_games[sender_id] = "awaiting_difficulty"
        await event.reply(f"`🎮 XO Game Initiated.`\n`Please reply with your desired difficulty level:`\n`Easy`, `Mid`, or `Hard`")
        return

    # --- GAMEPLAY LOOP ---
    if sender_id in active_games:
        current_state = active_games[sender_id]

        # STOP COMMAND (Works in all game states)
        if msg.lower() == "stop":
            del active_games[sender_id]
            await event.reply("`🛑 XO Game stopped.`")
            return

        # STATE 1: AWAITING DIFFICULTY SELECTION
        if current_state == "awaiting_difficulty":
            difficulty = msg.lower()
            if difficulty in ["easy", "mid", "hard"]:
                active_games[sender_id] = TicTacToe(difficulty=difficulty)
                game = active_games[sender_id]
                await event.reply(f"`✅ Level: {difficulty.upper()} selected. You are X.`\n`Reply 1-9 to make your first move.`\n\n" + game.draw_board())
            else:
                await event.reply("`❌ Invalid difficulty. Please reply with: Easy, Mid, or Hard.`")
            return
        
        # STATE 2: GAME IS ACTIVE (TicTacToe Instance)
        if isinstance(current_state, TicTacToe):
            game = current_state
            
            if msg.isdigit() and 1 <= int(msg) <= 9:
                success, info = game.make_move(msg)
                if success:
                    # Check User Win
                    is_over, winner = game.check_winner(game.board)
                    if is_over:
                        res = "🎉 YOU WON!" if winner == "X" else "😐 DRAW."
                        await event.reply(f"`{res}`\n\n" + game.draw_board())
                        del active_games[sender_id]
                        return
                    
                    # Bot Move
                    game.bot_move()
                    is_over, winner = game.check_winner(game.board)
                    if is_over:
                        res = "🤖 I WON!" if winner == "O" else "😐 DRAW."
                        await event.reply(f"`{res}`\n\n" + game.draw_board())
                        del active_games[sender_id]
                        return
                    
                    await event.reply(f"`My turn done. Your move (1-9):`\n\n" + game.draw_board())
                else:
                    await event.reply(f"`❌ {info}`")
            else:
                await event.reply("`Please send a number 1-9 or type 'stop'.`")
            return


    # --- AI CHAT GENERATION ---
    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(random.uniform(1, 2))
        response = await ai_client.generate_response(sender_id, msg, raw_username, user_firstname)

    await event.reply(response)
    save_message(sender_id, raw_username, response, True)

# ---------------- Main ---------------- #
async def main():
    init_db()
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY missing")
        return

    print("✅ System Loaded (Personalized Protocols & XO Active).")
    try:
        await client.start()
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Error starting Telethon client: {e}")

if __name__ == '__main__':
    asyncio.run(main())