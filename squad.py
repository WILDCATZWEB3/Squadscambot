import asyncio
import random
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

TOKEN = "7861627277:AAF1UG_Te-mWfSOtxyaTF-phHkhe3euvKGk"
warn_count = {}
pending_verifications = {}

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Hello! 🤖 I'm SquadScamBot.\n\n"
        "🔹 I protect this group from scammers.\n"
        "🔹 I enforce verification before new members can chat.\n"
        "🔹 I restrict link sharing (except for admins).\n\n"
        "Use /help to see all available commands."
    )

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🛠️ **SquadScamBot Commands:**\n\n"
        "/start - Introduce the bot\n"
        "/help - Show this help message\n"
        "/rules - Show group rules\n"
        "/report - Report a scammer"
    )

async def rules(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "📜 **Group Rules:**\n"
        "1️⃣ No spamming\n"
        "2️⃣ No scam links\n"
        "3️⃣ Be respectful\n"
        "4️⃣ Only admins can post links"
    )

async def report(update: Update, context: CallbackContext):
    await update.message.reply_text("📢 Report received! An admin will check it soon.")

async def welcome(update: Update, context: CallbackContext):
    for member in update.message.new_chat_members:
        user_id = member.id
        first_name = member.first_name
        num1, num2 = random.randint(1, 10), random.randint(1, 10)
        correct_answer = num1 + num2

        options = [correct_answer, correct_answer + random.randint(1, 5), correct_answer - random.randint(1, 5)]
        random.shuffle(options)

        pending_verifications[user_id] = correct_answer

        keyboard = [
            [InlineKeyboardButton(str(option), callback_data=f"verify|{user_id}|{option}")]
            for option in options
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"👋 Welcome {first_name}! Please solve this to verify:\n\n"
            f"{num1} + {num2} = ?",
            reply_markup=reply_markup
        )

        await context.bot.restrict_chat_member(
            update.message.chat_id, user_id, ChatPermissions(can_send_messages=False)
        )

async def verify_user(update: Update, context: CallbackContext):
    query = update.callback_query
    _, user_id, chosen_answer = query.data.split("|")
    user_id = int(user_id)
    chosen_answer = int(chosen_answer)

    correct_answer = pending_verifications.get(user_id)

    if correct_answer is None:
        await query.answer("Verification expired. Please rejoin.")
        return

    if chosen_answer == correct_answer:
        chat_id = query.message.chat_id
        await context.bot.restrict_chat_member(
            chat_id, user_id, ChatPermissions(can_send_messages=True, can_send_other_messages=True)
        )
        await query.edit_message_text("✅ Verification successful! You can now chat.")
        del pending_verifications[user_id]  # Remove verified user
    else:
        await query.answer("❌ Wrong answer. Try again!")

async def detect_links(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    user = update.message.from_user
    message = update.message

    chat_member = await context.bot.get_chat_member(chat_id, user_id)

    if chat_member.status in ["administrator", "creator"]:
        return  

    if user.id in warn_count:
        warn_count[user.id] += 1
    else:
        warn_count[user.id] = 1

    if warn_count[user.id] < 3:
        await update.message.reply_text(f"⚠️ Warning {warn_count[user.id]}/3: No links allowed, {user.first_name}.")
        await update.message.delete()
    else:
        await update.message.reply_text(f"🚫 {user.first_name}, restricted for 5 minutes due to repeated violations.")
        await context.bot.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
        await asyncio.sleep(300)
        await context.bot.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=True))
        await update.message.reply_text(f"✅ {user.first_name}, you are now unrestricted.")

async def pin_admin_messages(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    chat_member = await context.bot.get_chat_member(chat_id, user_id)
    if chat_member.status in ["administrator", "creator"]:
        await context.bot.pin_chat_message(chat_id, update.message.message_id)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("report", report))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CallbackQueryHandler(verify_user, pattern=r"^verify\|\d+\|\d+$"))
    
    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), detect_links))
    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("text_link"), detect_links))
    app.add_handler(MessageHandler(filters.TEXT & filters.FORWARDED, pin_admin_messages))

    print("✅ SquadScamBot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
