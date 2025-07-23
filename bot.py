import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- Configuration ---
# Replace with your actual bot token
TELEGRAM_BOT_TOKEN = "7983901697:AAGQEE8hhaPA-ggkBiydiziiz8M0WPYVTgU"

# Enable logging to see errors, bot activity, and connection tracking
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- In-Memory Data Structures to Manage State (No Database) ---
# This dictionary will store the state of each user: 'idle', 'waiting', or 'chatting'
user_states = {}
# This variable will hold the chat_id of a user waiting for a partner.
# A simple variable is sufficient as we only need to match one pair at a time.
waiting_user = None
# This dictionary will store active chat pairs, e.g., {user1_id: user2_id, user2_id: user1_id}
active_chats = {}


# --- Helper Functions ---

def get_chat_keyboard() -> InlineKeyboardMarkup:
    """Creates an inline keyboard with 'Next' and 'Stop' buttons."""
    keyboard = [
        [
            InlineKeyboardButton("Next", callback_data='next'),
            InlineKeyboardButton("Stop", callback_data='stop'),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command. Welcomes the user and provides clean instructions."""
    user_id = update.effective_chat.id
    welcome_message = (
        "Welcome to the Matchmaking Bot.\n\n"
        "You can connect with a random user and chat anonymously.\n\n"
        "Available commands:\n"
        "/search - Start searching for a chat partner.\n"
        "/stop - End your current chat.\n"
        "/next - Find a new chat partner.\n\n"
        "Type /search to begin."
    )
    # If the user is already in a chat, disconnect them first before showing the welcome message.
    if user_states.get(user_id) == 'chatting':
        await stop_command(update, context)

    user_states[user_id] = 'idle'
    await context.bot.send_message(chat_id=user_id, text=welcome_message)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /search command. Adds a user to the matchmaking queue."""
    global waiting_user
    user_id = update.effective_chat.id

    # Error handling for users already in a chat or queue.
    if user_states.get(user_id) == 'chatting':
        await context.bot.send_message(chat_id=user_id, text="You are already in a chat. Use /stop or /next.")
        return
    if user_states.get(user_id) == 'waiting':
        await context.bot.send_message(chat_id=user_id, text="You are already searching for a partner. Please be patient.")
        return

    # Matchmaking logic
    if waiting_user is None:
        # If no one is waiting, this user becomes the waiting user.
        waiting_user = user_id
        user_states[user_id] = 'waiting'
        await context.bot.send_message(chat_id=user_id, text="Searching for a chat partner... Please wait.")
    else:
        # If someone is waiting, a match is found.
        partner_id = waiting_user
        waiting_user = None  # Reset the waiting queue

        # Connect the two users by mapping their IDs to each other.
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        # Update states for both users to 'chatting'.
        user_states[user_id] = 'chatting'
        user_states[partner_id] = 'chatting'

        # Notify both users that they are connected and show the keyboard.
        reply_markup = get_chat_keyboard()
        await context.bot.send_message(chat_id=user_id, text="You are now connected with a stranger. Say hi!", reply_markup=reply_markup)
        await context.bot.send_message(chat_id=partner_id, text="You are now connected with a stranger. Say hi!", reply_markup=reply_markup)
        logger.info(f"Match found: User {user_id} connected with User {partner_id}")


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /stop. Disconnects a user from a chat or removes them from the queue."""
    global waiting_user
    user_id = update.effective_chat.id
    user_state = user_states.get(user_id)

    if user_state == 'chatting':
        partner_id = active_chats.get(user_id)

        # Notify the partner that the chat has ended.
        if partner_id:
            await context.bot.send_message(chat_id=partner_id, text="Your chat partner has disconnected. Use /search to find a new chat.")
            # Clean up the partner's state and connection data.
            if partner_id in active_chats:
                del active_chats[partner_id]
            user_states[partner_id] = 'idle'

        # Clean up the current user's state and connection data.
        if user_id in active_chats:
            del active_chats[user_id]
        user_states[user_id] = 'idle'

        await context.bot.send_message(chat_id=user_id, text="You have disconnected from the chat. Use /search to start a new one.")
        logger.info(f"User {user_id} disconnected from chat with {partner_id}")

    elif user_state == 'waiting':
        # If the user was waiting, remove them from the queue.
        if waiting_user == user_id:
            waiting_user = None
        user_states[user_id] = 'idle'
        await context.bot.send_message(chat_id=user_id, text="You are no longer searching for a partner.")
        logger.info(f"User {user_id} stopped waiting.")
    else:
        # Handle cases where the user is not in any active state.
        await context.bot.send_message(chat_id=user_id, text="You are not in an active chat or search.")


async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /next command. Disconnects the current chat and finds a new one."""
    global waiting_user
    user_id = update.effective_chat.id
    user_state = user_states.get(user_id)

    if user_state == 'chatting':
        # Disconnect the current chat partner.
        partner_id = active_chats.get(user_id)
        if partner_id:
            await context.bot.send_message(chat_id=partner_id, text="Your chat partner has moved to the next chat. Use /search or /next to find a new one.")
            if partner_id in active_chats:
                del active_chats[partner_id]
            user_states[partner_id] = 'idle'
        
        if user_id in active_chats:
            del active_chats[user_id]
        
        # Immediately search for a new chat partner for the current user.
        await context.bot.send_message(chat_id=user_id, text="Searching for a new chat partner...")
        
        if waiting_user is None:
            # If no one is waiting, this user becomes the new waiting user.
            waiting_user = user_id
            user_states[user_id] = 'waiting'
        else:
            # If someone is waiting, match them immediately.
            new_partner_id = waiting_user
            waiting_user = None

            active_chats[user_id] = new_partner_id
            active_chats[new_partner_id] = user_id

            user_states[user_id] = 'chatting'
            user_states[new_partner_id] = 'chatting'
            
            reply_markup = get_chat_keyboard()
            await context.bot.send_message(chat_id=user_id, text="You are now connected with a new stranger. Say hi!", reply_markup=reply_markup)
            await context.bot.send_message(chat_id=new_partner_id, text="You are now connected with a stranger. Say hi!", reply_markup=reply_markup)
            logger.info(f"Next successful: User {user_id} connected with new User {new_partner_id}")
    else:
        await context.bot.send_message(chat_id=user_id, text="You must be in a chat to use the /next command. Use /search to find a chat first.")


# --- Callback Query Handler ---

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and runs the aporopriate command."""
    query = update.callback_query
    # Answer the callback query to remove the "loading" state from the button
    await query.answer()

    if query.data == 'next':
        await next_command(update, context)
    elif query.data == 'stop':
        await stop_command(update, context)


# --- Message Handler ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all non-command text messages, routing them between connected users."""
    user_id = update.effective_chat.id
    user_state = user_states.get(user_id)

    if user_state == 'chatting':
        partner_id = active_chats.get(user_id)
        if partner_id:
            # Anonymously forward the message to the partner.
            await context.bot.send_message(chat_id=partner_id, text=update.message.text)
        else:
            # This handles an edge case where a partner might have been removed unexpectedly.
            await context.bot.send_message(chat_id=user_id, text="Your partner seems to have disconnected. Use /search to search again.")
            user_states[user_id] = 'idle'
            if user_id in active_chats:
                del active_chats[user_id]
    elif user_state == 'waiting':
        await context.bot.send_message(chat_id=user_id, text="Please wait, we are still searching for a partner for you.")
    else: # 'idle' or None
        await context.bot.send_message(chat_id=user_id, text="You are not connected to anyone. Use /search to start a chat.")


# --- Main Bot Setup ---

def main() -> None:
    """Initializes and starts the Telegram bot."""
    # Create the Application instance with the bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers.
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("next", next_command))

    # Register the callback query handler for the buttons.
    application.add_handler(CallbackQueryHandler(button_callback))

    # Register a message handler for all non-command text messages.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot. It will run until manually stopped (e.g., with Ctrl-C).
    logger.info("Bot is starting and polling for updates...")
    application.run_polling()
    logger.info("Bot has been stopped.")


if __name__ == "__main__":
    main()
