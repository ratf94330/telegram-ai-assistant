import os
import asyncio
import sqlite3
import random
import math
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from groq import AsyncGroq

# --- YOUR CREDENTIALS ---
API_ID = 26908211
API_HASH = "6233bafd1d0ec5801b8c0e7ad0bf1aaa"
# BOT_TOKEN is required for client.send_message
BOT_TOKEN = "YOUR_NEW_BOT_TOKEN_HERE" 
OWNER_ID = 1723764689
OWNER_NAME = "Habte"
OWNER_ALIAS = "Jalmaro" 

# Special Friend Usernames (Strictly enforced)
DAGM_USERNAME = "KOMASUN_MARKET"
ABI_USERNAME = "Contracttor"

# Environment variables
STRING_SESSION = os.environ.get('STRING_SESSION', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Global States
# State tracking for menu navigation and chat modes
user_states = {} # {user_id: 'MENU' | 'CHAT' | 'LEAVE_MESSAGE' | 'XO_DIFFICULTY' | 'XO_PLAYING'}
active_games = {} # {user_id: TicTacToeInstance}

print(f"🤖 Starting {OWNER_NAME}'s Advanced AI Assistant (Menu System Active)...")

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
    # Existing TicTacToe class remains the same for game logic (omitted for brevity)
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

# ---------------- AI CLIENT & PERSONAS ---------------- #
# (GroqAIClient class remains unchanged - omitted for brevity)
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

ai_client = GroqAIClient(GROQ_API_KEY)
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# ---------------- MENU FUNCTIONS ---------------- #

def get_main_menu_keyboard():
    return client.build_reply_markup([
        [Button.inline("💬 Chat With Assistant", data="chat")],
        [Button.inline("🎮 Play XO Game", data="xo")],
        [Button.inline("📨 Leave a Message for Habte", data="message")],
        [Button.inline("🔙 Close Menu", data="close")]
    ])

def get_chat_keyboard():
    return client.build_reply_markup([
        [Button.inline("🔙 Back to Menu", data="back_to_menu")]
    ])

def get_xo_difficulty_keyboard():
    return client.build_reply_markup([
        [Button.inline("Easy", data="xo_easy"), Button.inline("Mid", data="xo_mid"), Button.inline("Hard", data="xo_hard")],
        [Button.inline("🔙 Back to Menu", data="back_to_menu")]
    ])

async def show_main_menu(entity, message_id=None):
    user_id = entity.id
    user_states[user_id] = 'MENU'
    
    text = (
        f"**Welcome**\n"
        f"I am {OWNER_NAME}'s professional AI assistant — here to help you, guide you, or simply talk while he is busy handling top-priority engagements."
    )
    
    if message_id:
        # Edit the existing message if possible (e.g., coming back from a submenu)
        await client.edit_message(entity, message_id, text, buttons=get_main_menu_keyboard(), parse_mode='md')
    else:
        # Send a new message (e.g., from /start)
        await client.send_message(entity, text, buttons=get_main_menu_keyboard(), parse_mode='md')
    
    # Clear active games or conversation history upon return to menu
    if user_id in active_games: del active_games[user_id]
    if user_id in ai_client.conversations: del ai_client.conversations[user_id]


# ---------------- INLINE BUTTON HANDLER ---------------- #

@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    
    await event.delete() # Remove button message to clean up the chat

    # --- MAIN MENU NAVIGATION ---
    
    if data == "back_to_menu":
        await show_main_menu(event.peer_id)
        return

    elif data == "close":
        await client.send_message(event.peer_id, "`❌ Menu closed. Use /start to reopen.`")
        user_states[user_id] = 'CLOSED'
        return

    # --- STATE TRANSITIONS ---
    
    elif data == "chat":
        user_states[user_id] = 'CHAT'
        await client.send_message(event.peer_id, 
                                  "`💬 Chat Mode Activated. Type your message below. The AI is listening.`",
                                  buttons=get_chat_keyboard())
        return

    elif data == "message":
        user_states[user_id] = 'LEAVE_MESSAGE'
        await client.send_message(event.peer_id, 
                                  "`📨 Please type the message you wish to leave for Habte. I will forward it to him directly.`",
                                  buttons=get_chat_keyboard()) # Using chat keyboard for "Back"
        return

    elif data == "xo":
        user_states[user_id] = 'XO_DIFFICULTY'
        await client.send_message(event.peer_id, 
                                  "`🎮 XO Game Initiated. Please select your desired difficulty level:`",
                                  buttons=get_xo_difficulty_keyboard())
        return

    # --- XO DIFFICULTY SELECTION ---
    
    elif data.startswith("xo_"):
        difficulty = data.split('_')[1]
        
        # Start the game instance
        active_games[user_id] = TicTacToe(difficulty=difficulty)
        user_states[user_id] = 'XO_PLAYING'
        game = active_games[user_id]
        
        await client.send_message(event.peer_id, 
                                  f"`✅ Level: {difficulty.upper()} selected. You are X.`\n`Reply with a number 1-9 to make your first move.`\n\n" + game.draw_board())
        return
    
    await event.answer("Unknown command.")


# ---------------- NEW MESSAGE HANDLER (Text Input) ---------------- #

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_message(event):
    if event.sender_id == OWNER_ID: return # Ignore owner's messages

    user = await event.get_sender()
    sender_id = event.message.peer_id.user_id
    raw_username = user.username 
    user_firstname = user.first_name
    msg = event.message.text.strip()

    # Get user state or default to MENU if unknown
    state = user_states.get(sender_id, 'MENU')
    save_message(sender_id, raw_username, msg, False)

    # --- STATE HANDLERS ---
    
    # 1. Menu Trigger (Only /start)
    if msg.lower() == "/start":
        # Delete the previous menu message if it exists (Telethon handles this implicitly by sending new)
        await show_main_menu(event.peer_id)
        return

    # 2. Leaving a Message for Habte
    if state == 'LEAVE_MESSAGE':
        # Forward the message to the owner
        message_to_forward = f"📬 **New Message for Habte**\nFrom: {user_firstname} (@{raw_username or 'N/A'})\n\n---\n{msg}"
        try:
            await client.send_message(OWNER_ID, message_to_forward, parse_mode='md')
            response = "`Message received and forwarded to Habte's inbox. Thank you for your correspondence.`"
        except Exception:
            response = "`Error: Could not forward the message. Habte's network connection may be offline.`"
        
        await event.reply(response)
        await show_main_menu(event.peer_id) # Transition back to menu
        return

    # 3. XO Gameplay
    if state == 'XO_PLAYING' and sender_id in active_games:
        game = active_games[sender_id]
        
        if msg.lower() == "stop":
            del active_games[sender_id]
            user_states[sender_id] = 'MENU'
            await event.reply("`🛑 XO Game stopped. Returning to Main Menu...`")
            await show_main_menu(event.peer_id)
            return

        if msg.isdigit() and 1 <= int(msg) <= 9:
            success, info = game.make_move(msg)
            if success:
                is_over, winner = game.check_winner(game.board)
                if is_over:
                    res = "🎉 YOU WON!" if winner == "X" else "😐 DRAW."
                    await event.reply(f"`{res}`\n\n" + game.draw_board())
                    del active_games[sender_id]
                    await show_main_menu(event.peer_id)
                    return
                
                # Bot Move
                game.bot_move()
                is_over, winner = game.check_winner(game.board)
                if is_over:
                    res = "🤖 I WON!" if winner == "O" else "😐 DRAW."
                    await event.reply(f"`{res}`\n\n" + game.draw_board())
                    del active_games[sender_id]
                    await show_main_menu(event.peer_id)
                    return
                
                await event.reply(f"`My turn done. Your move (1-9) or type 'stop':`\n\n" + game.draw_board())
            else:
                await event.reply(f"`❌ {info}`")
        else:
            await event.reply("`Please send a number 1-9 or type 'stop'.`")
        return
        
    # 4. AI Chat Mode
    if state == 'CHAT':
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(random.uniform(0.5, 1.5))
            response = await ai_client.generate_response(sender_id, msg, raw_username, user_firstname)
        
        # Add the 'Back to Menu' button to every chat response
        await event.reply(response, buttons=get_chat_keyboard())
        save_message(sender_id, raw_username, response, True)
        return

    # 5. Default/Invalid State Catch (If user types something outside of a known state)
    if state in ['MENU', 'CLOSED', 'XO_DIFFICULTY'] or state not in user_states:
        await event.reply("`I'm currently focused on the menu system. Please use the buttons or type /start to access the main menu.`")
        return


# ---------------- Main ---------------- #
async def main():
    init_db()
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY missing")
        return

    print("✅ System Loaded (Menu System Operational).")
    try:
        # Note: If running as a user account, you might need to handle the BOT_TOKEN
        # to ensure the client connects properly. For a dedicated bot, use BotFather token here.
        await client.start()
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Error starting Telethon client: {e}")

if __name__ == '__main__':
    asyncio.run(main())