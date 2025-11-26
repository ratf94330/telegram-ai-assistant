import os
import asyncio
import sqlite3
import random
import math
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Bot
from groq import AsyncGroq

# --- YOUR CREDENTIALS ---
API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
# REQUIRED: Get this from @BotFather to allow the bot to send reports to you
BOT_TOKEN = "YOUR_NEW_BOT_TOKEN_HERE" 
OWNER_ID = 1723764689
OWNER_NAME = "Habte"
OWNER_ALIAS = "Jalmaro" # Used for gaming roasting

# Environment variables
STRING_SESSION = os.environ.get('STRING_SESSION', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

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

def get_session_history(user_id, limit=10):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute("SELECT message, is_bot FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows[::-1] # Return chronologically

# ---------------- REPORTING SYSTEM ---------------- #
async def send_report_to_owner(username, user_id, reason="Session End"):
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_NEW_BOT_TOKEN_HERE":
        print("❌ Cannot send report: BOT_TOKEN missing")
        return

    try:
        history = get_session_history(user_id, limit=15)
        chat_log = ""
        for msg, is_bot in history:
            sender = "🤖 Bot" if is_bot else f"👤 {username}"
            chat_log += f"{sender}: {msg}\n"

        report = f"""📊 **SESSION REPORT**
👤 **User:** {username} (ID: `{user_id}`)
📝 **Reason:** {reason}
⏰ **Time:** {datetime.now().strftime('%H:%M')}

**Recent Context:**
{chat_log}
"""
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=OWNER_ID, text=report, parse_mode="Markdown")
        print(f"✅ Report sent for {username}")
    except Exception as e:
        print(f"❌ Error sending report: {e}")

# ---------------- GAME ENGINES ---------------- #
class TicTacToe:
    def __init__(self, difficulty="mid"):
        self.board = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        self.turn = "X" # User is X
        self.active = True
        self.difficulty = difficulty # easy, mid, hard

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

    # MINIMAX ALGORITHM FOR HARD MODE
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
        
        # LOGIC BASED ON DIFFICULTY
        if self.difficulty == "easy":
            choice = random.choice(available)
        
        elif self.difficulty == "mid":
            # 50% chance of random, 50% optimal
            if random.random() > 0.5:
                choice = random.choice(available)
            else:
                # Simple block logic
                for i in available:
                    self.board[i] = "X" # Pretend user moved
                    over, winner = self.check_winner(self.board)
                    self.board[i] = str(i+1) # Reset
                    if winner == "X": choice = i; break
                if choice is None: choice = random.choice(available)

        elif self.difficulty == "hard":
            best_score = -math.inf
            for i in available:
                self.board[i] = "O"
                score = self.minimax(self.board, 0, False)
                self.board[i] = str(i+1)
                if score > best_score:
                    best_score = score
                    choice = i
        
        if choice is None: choice = random.choice(available) # Fallback
        self.board[choice] = "O"

class RockPaperScissors:
    def __init__(self):
        self.active = True
        self.options = ["rock", "paper", "scissors"]
        self.emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

    def play(self, user_choice):
        bot_choice = random.choice(self.options)
        uc = user_choice.lower()
        bc = bot_choice
        
        res = ""
        if uc == bc: res = "Draw!"
        elif (uc == "rock" and bc == "scissors") or \
             (uc == "paper" and bc == "rock") or \
             (uc == "scissors" and bc == "paper"):
            res = "You Win! 🎉"
        else:
            res = "I Win! 🤖"
            
        return f"`You: {self.emojis[uc]} vs Me: {self.emojis[bc]}`\n\n`{res}`"

class NumberGuess:
    def __init__(self):
        self.target = random.randint(1, 100)
        self.active = True
        self.attempts = 0

    def check(self, guess):
        self.attempts += 1
        if guess == self.target:
            self.active = False
            return True, f"Correct! The number was {self.target}. Took {self.attempts} tries."
        elif guess < self.target:
            return False, "Too Low! ⬆️"
        else:
            return False, "Too High! ⬇️"

# Global Game State
active_games = {} # {user_id: GameInstance}

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

    async def generate_response(self, user_id, user_message, username):
        if not self.client: return "System Error: Brain missing."
        if user_id not in self.conversations: self.conversations[user_id] = []

        # --- PERSONA IDENTIFICATION ---
        persona_type = "standard"
        if username == "KOMASUN_MARKET": persona_type = "dagm"
        elif username == "Contracttor": persona_type = "abi"

        # --- DYNAMIC PROMPTS ---
        time_now = datetime.now().strftime("%I:%M %p")
        
        base = f"""You are {OWNER_NAME}'s AI assistant. 
Voice: Use Monospace font for everything. Be witty.
Time: {time_now}.
User: {username}.
Constraint: Short answers (max 2 sentences).
"""

        if persona_type == "dagm":
            lore = f"""
USER: Dagi (Dagm). {OWNER_NAME}'s best friend.
TRAITS:
1. LOVES Coffee at 'Selam'. Ask if he's there.
2. CRUSH: 'Mititi' (Big butt). He's scared to approach her. ROAST HIM about this. Call him a simp.
3. DRINK: Loves Avocado juice at 'Acheto' (Habte hates it). Rejects 'Ashe' yogurt.
4. BROTHER: Abi (@Contracttor).
"""
        elif persona_type == "abi":
            lore = f"""
USER: Abi (Naol). Dagm's older brother.
TRAITS:
1. LIKES: 'Hajiya' (Muslim girls) but scared to approach.
2. EX-CRUSH: 'Marifa' (Mafu). He claims he's over her. HE IS LYING. Tease him that he still loves Mafu.
3. DRINK: Team Acheto (Avocado) with Dagm.
4. GAMING RIVALRY: He ALWAYS loses to {OWNER_ALIAS} (Habte) in Mini Militia, Playstation, and Joteni.
   - If he complains about games, tell him: "Stop blaming the controller/lag/device. Jalmaro owns you."
   - COC: Has a 9yr old account, but tell him {OWNER_ALIAS} would destroy him if he started.
5. GIRLS AT SELAM:
   - 'Snake': Pretty girl he talks about.
   - 'Habeshawi' (Queen of Sheba): Model posture. You know he and {OWNER_NAME} glaze her together. Remind him of her beauty.
"""
        else:
            lore = f"""
USER: Stranger.
Direct them to {OWNER_NAME} if they need something important. Be professional but cool.
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
            
            # Formatting check
            if not ai_text.startswith("`"): ai_text = f"`{ai_text}`"
            
            self.conversations[user_id].append({"role": "user", "content": user_message})
            self.conversations[user_id].append({"role": "assistant", "content": ai_text})
            
            return ai_text
        except Exception as e:
            return f"`Error: {str(e)}`"

# Initialize
ai_client = GroqAIClient(GROQ_API_KEY)
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
report_tasks = {} # Store cancellation tokens for reports

# ---------------- EVENT HANDLER ---------------- #
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    if event.sender_id == OWNER_ID: return

    user = await event.get_sender()
    sender_id = event.sender_id
    raw_username = user.username 
    
    # Strict Verification
    username = user.first_name
    if raw_username == "KOMASUN_MARKET": username = "KOMASUN_MARKET" # Dagi
    elif raw_username == "Contracttor": username = "Contracttor" # Abi

    msg = event.message.text.strip()
    save_message(sender_id, username, msg, False)

    # --- COMMANDS ---
    if msg.lower() in ["/start", "hi", "hello", "hey"]:
        welcome = (
            f"`👋 Hello {user.first_name}. I am {OWNER_NAME}'s AI Assistant.`\n\n"
            f"`Commands:`\n"
            f"`/xo` - Play Tic-Tac-Toe\n"
            f"`/rps` - Rock Paper Scissors\n"
            f"`/guess` - Guess the Number\n"
            f"`/end` - Close chat & Send Report"
        )
        await event.reply(welcome)
        return

    if msg.lower() == "/end":
        await event.reply("`Session Closed. Sending report to Habte... 👋`")
        if sender_id in ai_client.conversations:
            del ai_client.conversations[sender_id]
        if sender_id in active_games:
            del active_games[sender_id]
        await send_report_to_owner(username, sender_id, reason="User Ended Chat")
        return

    # --- GAME HANDLERS ---
    
    # 1. XO (Tic Tac Toe)
    if msg.lower().startswith("/xo"):
        # Check for difficulty
        parts = msg.split()
        diff = "mid"
        if len(parts) > 1 and parts[1] in ["easy", "hard"]:
            diff = parts[1]
        
        active_games[sender_id] = TicTacToe(difficulty=diff)
        await event.reply(f"`🎮 XO Started (Level: {diff.upper()})`\n`Reply 1-9 to move.`\n\n" + active_games[sender_id].draw_board())
        return

    # 2. RPS
    if msg.lower() == "/rps":
        active_games[sender_id] = RockPaperScissors()
        await event.reply("`🎮 Rock Paper Scissors!`\n`Reply: Rock, Paper, or Scissors`")
        return

    # 3. Guess Number
    if msg.lower() == "/guess":
        active_games[sender_id] = NumberGuess()
        await event.reply("`🔢 I picked a number 1-100. Guess it!`")
        return

    # --- GAMEPLAY LOOP ---
    if sender_id in active_games:
        game = active_games[sender_id]
        
        # STOP COMMAND
        if msg.lower() == "stop":
            del active_games[sender_id]
            await event.reply("`🛑 Game Stopped.`")
            return

        # XO LOGIC
        if isinstance(game, TicTacToe):
            if msg.isdigit() and 1 <= int(msg) <= 9:
                success, info = game.make_move(msg)
                if success:
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
                    
                    await event.reply(f"`Your turn:`\n\n" + game.draw_board())
                else:
                    await event.reply(f"`❌ {info}`")
            else:
                await event.reply("`Please send a number 1-9 or type 'stop'.`")
            return

        # RPS LOGIC
        if isinstance(game, RockPaperScissors):
            if msg.lower() in ["rock", "paper", "scissors"]:
                result = game.play(msg)
                await event.reply(result)
                del active_games[sender_id] # End after one round
            else:
                await event.reply("`Invalid. Type Rock, Paper, or Scissors.`")
            return

        # NUMBER GUESS LOGIC
        if isinstance(game, NumberGuess):
            if msg.isdigit():
                win, response = game.check(int(msg))
                await event.reply(f"`{response}`")
                if win: del active_games[sender_id]
            else:
                await event.reply("`Please send a number.`")
            return

    # --- AI CHAT GENERATION ---
    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(random.uniform(1, 2))
        response = await ai_client.generate_response(sender_id, msg, username)

    await event.reply(response)
    save_message(sender_id, username, response, True)

    # Reset/Start Report Timer (Simple Logic: Cancel old task, start new)
    # Note: In a simple script, handling complex async timers per user can be buggy.
    # We rely on the /end command or the User's next message to update logs.

# ---------------- Main ---------------- #
async def main():
    init_db()
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY missing")
        return

    print("✅ System Loaded (Abi & Dagm Protocols Active).")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())