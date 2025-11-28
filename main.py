import os
import asyncio
import sqlite3
import random
import math
import glob
from datetime import datetime
from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
from groq import AsyncGroq

# --- YOUR CREDENTIALS ---
API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
OWNER_ID = 1723764689
OWNER_NAME = "Habte"
OWNER_ALIAS = "Jalmaro" 

# Special Friend Usernames (Strictly enforced)
DAGM_USERNAME = "KOMASUN_MARKET"
ABI_USERNAME = "Contracttor"

# Environment variables
STRING_SESSION = os.environ.get('STRING_SESSION', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Media Paths
ASSETS_DIR = "assets"

print(f"🤖 Starting {OWNER_NAME}'s Advanced AI Assistant (v2.1 - Fix Applied)...")

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

# ---------------- MEDIA & RATE LIMIT HELPER ---------------- #
async def safe_reply(event, message=None, file=None, **kwargs):
    """
    Handles Telegram FloodWait errors automatically.
    Accepts **kwargs to pass 'parse_mode', 'buttons', etc.
    """
    try:
        if file:
            await event.reply(message, file=file, **kwargs)
        else:
            await event.reply(message, **kwargs)
    except errors.FloodWaitError as e:
        print(f"⚠️ FloodWait triggered. Sleeping for {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
        # Retry once
        try:
            if file:
                await event.reply(message, file=file, **kwargs)
            else:
                await event.reply(message, **kwargs)
        except Exception as e:
            print(f"❌ Retry failed: {e}")
    except Exception as e:
        print(f"❌ Error sending message: {e}")

def get_random_media(category):
    """Pick a random file from assets/{category} folder."""
    path = os.path.join(ASSETS_DIR, category)
    if not os.path.exists(path):
        return None
    
    files = glob.glob(os.path.join(path, "*.*")) # Grab all files
    # Filter for images/videos only
    valid_exts = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webp']
    media_files = [f for f in files if os.path.splitext(f)[1].lower() in valid_exts]
    
    if media_files:
        return random.choice(media_files)
    return None

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

    # Minimax implementation
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
            if random.random() > 0.5:
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
        if not self.client: return "`System Error: Brain missing.`", "standard"
        if user_id not in self.conversations: self.conversations[user_id] = []

        # --- PERSONA IDENTIFICATION ---
        persona_type = "standard"
        username_alias = user_firstname

        if raw_username == DAGM_USERNAME: 
            persona_type = "dagm"
            username_alias = "Dagi"
        elif raw_username == ABI_USERNAME: 
            persona_type = "abi"
            username_alias = "Abi/Naol"

        # --- DYNAMIC PROMPTS ---
        time_now = datetime.now().strftime("%I:%M %p")
        
        # Glazing Habte
        glaze_messages = [
            f"Note: {OWNER_NAME} is currently optimizing complex global simulations. He will return at his leisure.",
            f"Note: {OWNER_NAME} is busy achieving professional mastery; he is not available for immediate contact.",
            f"Note: {OWNER_NAME} is managing high-level strategic logistics. You may leave a message.",
            f"Note: {OWNER_NAME} is engaged in proprietary development that requires his full focus.",
        ]
        glaze = random.choice(glaze_messages)

        base = f"""You are {OWNER_NAME}'s professional AI assistant. 
Your Name: 'Habte's AI'.
Style: Use Monospace font for everything. Be witty, arrogant but charming, and dynamic.
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
1. He likes 'Selam' coffee. Ask him if he is there.
2. CRUSH: 'Mititi' (Big butt). ROAST HIM about being a simp.
3. DRINK: Loves expensive Avocado juice at 'Acheto'.
4. GIRLS: He stays quiet when {OWNER_NAME} glazes 'Habeshawi'.
"""
        # --- Abi (Contracttor) LORE ---
        elif persona_type == "abi":
            lore = f"""
SPECIAL USER: {username_alias}. Dagm's older brother.
TONE: Teasing, challenging.
LORE:
1. LIKES: 'Hajiya' but scared to approach.
2. EX-CRUSH: 'Marifa' (Mafu). HE IS LYING if he says he's over her.
3. GAMING: Always loses to {OWNER_NAME} in Mini Militia/Joteni. Blames lag.
4. GIRLS: Talks about 'Snake'. Glazes 'Habeshawi'.
"""
        else:
            lore = f"""
TONE: Formal, slightly condescending but polite. Offer assistance or suggest he leave a concise message.
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
            
            if not ai_text.startswith("`"): ai_text = f"`{ai_text}`"
            
            self.conversations[user_id].append({"role": "user", "content": user_message})
            self.conversations[user_id].append({"role": "assistant", "content": ai_text})
            
            return ai_text, persona_type
        except Exception as e:
            return f"`Error: {str(e)}`", "standard"

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
    user_firstname = user.first_name or "Guest"

    msg = event.message.text.strip()
    save_message(sender_id, raw_username, msg, False)

    # --- COMMANDS & GREETING ---
    if msg.lower() in ["/start", "hi", "hello", "hey"]:
        
        # 5 Welcoming Messages
        welcomes = [
            f"1. `You’ve reached {OWNER_NAME}’s AI — the only system running on confidence, audacity, and 3 hours of sleep. He’s out there being allergic to failure, so I’ll deal with you for now. If you’re bored, type /xo and lose gracefully.`",
            
            f"2. `Attention. You’re connected to {OWNER_NAME}’s assistant — a man so respected even Google asks him for answers. He’s currently solving problems the government hasn’t discovered yet. Chat with me or type /xo if you dare.`",
            
            f"3. `Yo. This is {OWNER_NAME}’s digital guard dog. {OWNER_NAME} is busy terrorizing the timeline with main-character levels of delusion and charm. Until he returns, I’ll babysit you. If you’re feeling brave, type /xo and get humbled.`",
            
            f"4. `Hello. You are now speaking to the AI of {OWNER_NAME}, a man so busy the sun schedules its sunrise around him. While he handles high-priority missions (probably saving the economy again), I’ll keep you company. Speak freely — or test your luck in XO by typing /xo.`",
            
            f"5. `Hey there. You’ve reached the AI assistant of {OWNER_NAME} — the man whose energy resets WiFi routers and whose smile increases female heartbeat rates by 37%. Talk to me, chill with me, or challenge XO using /xo if you think you’re stronger than his fanbase.`"
        ]
        
        # Customize name if it's the specific friends
        chosen_msg = random.choice(welcomes)
        if raw_username == DAGM_USERNAME:
            chosen_msg = f"`Ah, Dagi. The Simp.`\n\n{chosen_msg}"
        elif raw_username == ABI_USERNAME:
            chosen_msg = f"`Abi, stop blaming lag.`\n\n{chosen_msg}"

        # FIX: The safe_reply function now accepts **kwargs, so this works now.
        await safe_reply(event, chosen_msg, parse_mode='Markdown')
        return

    # --- XO GAME FLOW ---
    if msg.lower() == "/xo":
        active_games[sender_id] = "awaiting_difficulty"
        await safe_reply(event, f"`🎮 XO Game Initiated.`\n`Please reply with your desired difficulty level:`\n`Easy`, `Mid`, or `Hard`")
        return

    if sender_id in active_games:
        current_state = active_games[sender_id]

        if msg.lower() == "stop":
            del active_games[sender_id]
            await safe_reply(event, "`🛑 XO Game stopped.`")
            return

        if current_state == "awaiting_difficulty":
            difficulty = msg.lower()
            if difficulty in ["easy", "mid", "hard"]:
                active_games[sender_id] = TicTacToe(difficulty=difficulty)
                game = active_games[sender_id]
                await safe_reply(event, f"`✅ Level: {difficulty.upper()} selected. You are X.`\n`Reply 1-9 to make your first move.`\n\n" + game.draw_board())
            else:
                await safe_reply(event, "`❌ Invalid difficulty. Reply: Easy, Mid, or Hard.`")
            return
        
        if isinstance(current_state, TicTacToe):
            game = current_state
            
            if msg.isdigit() and 1 <= int(msg) <= 9:
                success, info = game.make_move(msg)
                if success:
                    # Check User Win
                    is_over, winner = game.check_winner(game.board)
                    if is_over:
                        res = "🎉 YOU WON!" if winner == "X" else "😐 DRAW."
                        await safe_reply(event, f"`{res}`\n\n" + game.draw_board())
                        del active_games[sender_id]
                        return
                    
                    # Bot Move
                    game.bot_move()
                    is_over, winner = game.check_winner(game.board)
                    if is_over:
                        # BOT WINS LOGIC - SEND MOCKING GIF
                        res = "🤖 I WON! EZ." if winner == "O" else "😐 DRAW."
                        
                        media_file = None
                        if winner == "O":
                            media_file = get_random_media("win") # Sends from assets/win
                        
                        await safe_reply(event, f"`{res}`\n\n" + game.draw_board(), file=media_file)
                        del active_games[sender_id]
                        return
                    
                    await safe_reply(event, f"`My turn done. Your move (1-9):`\n\n" + game.draw_board())
                else:
                    await safe_reply(event, f"`❌ {info}`")
            else:
                await safe_reply(event, "`Please send a number 1-9 or type 'stop'.`")
            return


    # --- AI CHAT GENERATION ---
    async with client.action(event.chat_id, 'typing'):
        # Random typing delay for realism
        await asyncio.sleep(random.uniform(1, 2.5))
        response, persona_used = await ai_client.generate_response(sender_id, msg, raw_username, user_firstname)

    # --- SITUATIONAL REACTION LOGIC ---
    # Chance to send a reaction media based on persona or random chance
    media_to_send = None
    
    # 30% chance to send a roast gif if it's Dagm or Abi
    if persona_used in ["dagm", "abi"] and random.random() < 0.30:
        media_to_send = get_random_media("roast")
    
    # 10% chance to send a glazing/cool gif for standard users
    elif random.random() < 0.10:
        media_to_send = get_random_media("glaze")

    await safe_reply(event, response, file=media_to_send)
    save_message(sender_id, raw_username, response, True)

# ---------------- Main ---------------- #
async def main():
    init_db()
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY missing")
        return

    print("✅ System Loaded (Personalized Protocols, Anti-Flood & Media Active).")
    try:
        await client.start()
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Error starting Telethon client: {e}")

if __name__ == '__main__':
    asyncio.run(main())
