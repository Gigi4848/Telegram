from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "7983901697:AAGQEE8hhaPA-ggkBiydiziiz8M0WPYVTgU"

# Memory
waiting_users = []  # (user_id, age, gender)
active_chats = {}
user_ages = {}
user_genders = {}
user_age_pref = {}
user_gender_pref = {}
awaiting_age_input = set()
awaiting_gender_input = set()

# Keyboards
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("Start Searching")],
        [KeyboardButton("Stop")],
        [KeyboardButton("Toggle Age Matching")],
        [KeyboardButton("Toggle Gender Matching")]
    ],
    resize_keyboard=True
)

gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("Male")],
        [KeyboardButton("Female")],
        [KeyboardButton("Other")]
    ],
    resize_keyboard=True
)

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user_age_pref[user_id] = user_age_pref.get(user_id, False)
    user_gender_pref[user_id] = user_gender_pref.get(user_id, False)
    await update.message.reply_text(
        "Welcome to Anonymous Chat Bot.\nUse the buttons below to begin.",
        reply_markup=main_keyboard
    )

# Toggle age matching
async def toggle_age_matching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    current = user_age_pref.get(user_id, False)
    user_age_pref[user_id] = not current

    if user_age_pref[user_id] and user_id not in user_ages:
        awaiting_age_input.add(user_id)
        await update.message.reply_text("Age-based matching enabled. Please enter your age:")
    else:
        status = "ON" if user_age_pref[user_id] else "OFF"
        await update.message.reply_text(f"Age-based matching is now {status}.", reply_markup=main_keyboard)

# Toggle gender matching
async def toggle_gender_matching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    current = user_gender_pref.get(user_id, False)
    user_gender_pref[user_id] = not current

    if user_gender_pref[user_id] and user_id not in user_genders:
        awaiting_gender_input.add(user_id)
        await update.message.reply_text("Gender-based matching enabled. Please select your gender:", reply_markup=gender_keyboard)
    else:
        status = "ON" if user_gender_pref[user_id] else "OFF"
        await update.message.reply_text(f"Gender-based matching is now {status}.", reply_markup=main_keyboard)

# Start Searching
async def start_searching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id

    if user_id in active_chats:
        await update.message.reply_text("You're already in a chat. Use Stop to leave.")
        return

    if any(uid == user_id for uid, _, _ in waiting_users):
        await update.message.reply_text("You're already searching.")
        return

    # Check required fields
    if user_age_pref.get(user_id) and user_id not in user_ages:
        awaiting_age_input.add(user_id)
        await update.message.reply_text("Please enter your age first.")
        return

    if user_gender_pref.get(user_id) and user_id not in user_genders:
        awaiting_gender_input.add(user_id)
        await update.message.reply_text("Please select your gender:", reply_markup=gender_keyboard)
        return

    my_age = user_ages.get(user_id, None)
    my_gender = user_genders.get(user_id, None)
    use_age = user_age_pref.get(user_id, False)
    use_gender = user_gender_pref.get(user_id, False)

    match_found = False

    for i, (partner_id, partner_age, partner_gender) in enumerate(waiting_users):
        if use_age and (partner_age is None or my_age is None or abs(my_age - partner_age) > 3):
            continue
        if use_gender and (partner_gender == my_gender):
            continue

        # Match found
        waiting_users.pop(i)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        await context.bot.send_message(chat_id=partner_id, text="Partner found. Say hi!", reply_markup=main_keyboard)
        await context.bot.send_message(chat_id=user_id, text="Partner found. Say hi!", reply_markup=main_keyboard)
        match_found = True
        break

    if not match_found:
        waiting_users.append((user_id, my_age, my_gender))
        await update.message.reply_text("Searching for a partner...", reply_markup=main_keyboard)

# Stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="Your partner has left the chat.", reply_markup=main_keyboard)
        await context.bot.send_message(chat_id=user_id, text="You have left the chat.", reply_markup=main_keyboard)
    else:
        waiting_users[:] = [(uid, age, gen) for uid, age, gen in waiting_users if uid != user_id]
        await update.message.reply_text("Stopped searching or not in a chat.", reply_markup=main_keyboard)

# Handle messages
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    text = update.message.text.strip()

    if text == "Start Searching":
        await start_searching(update, context)
        return
    elif text == "Stop":
        await stop(update, context)
        return
    elif text == "Toggle Age Matching":
        await toggle_age_matching(update, context)
        return
    elif text == "Toggle Gender Matching":
        await toggle_gender_matching(update, context)
        return

    # Handle age input
    if user_id in awaiting_age_input:
        try:
            age = int(text)
            if 10 <= age <= 100:
                user_ages[user_id] = age
                awaiting_age_input.remove(user_id)
                await update.message.reply_text("Age saved. You can now start searching.", reply_markup=main_keyboard)
            else:
                await update.message.reply_text("Enter a valid age between 10 and 100.")
        except:
            await update.message.reply_text("Enter a valid number.")
        return

    # Handle gender input
    if user_id in awaiting_gender_input:
        if text in ["Male", "Female", "Other"]:
            user_genders[user_id] = text
            awaiting_gender_input.remove(user_id)
            await update.message.reply_text("Gender saved. You can now start searching.", reply_markup=main_keyboard)
        else:
            await update.message.reply_text("Please choose a valid gender option.", reply_markup=gender_keyboard)
        return

    if user_id in active_chats:
        partner_id = active_chats.get(user_id)
        if partner_id:
            try:
                await context.bot.copy_message(
                    chat_id=partner_id,
                    from_chat_id=user_id,
                    message_id=update.message.message_id
                )
            except:
                await update.message.reply_text("Failed to forward message.")
    else:
        await update.message.reply_text("You are not in a chat. Tap Start Searching to begin.", reply_markup=main_keyboard)

# Main entry
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
