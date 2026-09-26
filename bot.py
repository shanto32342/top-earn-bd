import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- CONFIGURATION ---
BOT_TOKEN = "8643610358:AAEX7KII2wZC3lPoDKkJ28yMmQhyXYHqUcA"  # BotFather থেকে পাওয়া টোকেন দাও
ADMIN_ID = 8643610358  # তোমার নিজের Telegram Numeric ID দাও
SUPPORT_USERNAME = "SHANTOBD71"  # @ ছাড়া তোমার ইউজারনেম

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        balance REAL DEFAULT 0,
                        total_earnings REAL DEFAULT 0,
                        total_withdrawn REAL DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_user(user_id, username=""):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def update_balance(user_id, amount):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ?, total_earnings = total_earnings + ? WHERE user_id = ?", (amount, max(0, amount), user_id))
    conn.commit()
    conn.close()

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.username)
    
    keyboard = [
        [InlineKeyboardButton("📂 Submit File (.xls)", callback_data="submit_file")],
        [InlineKeyboardButton("💰 My Balance", callback_data="my_balance"), InlineKeyboardButton("💳 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile"), InlineKeyboardButton("☎️ Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ]
    
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"স্বাগতম {user.first_name}! নিচের মেনু থেকে অপশন বেছে নিন:", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "my_balance":
        user = get_user(user_id)
        await query.message.reply_text(f"💵 আপনার বর্তমান ব্যালেন্স: {user[2]} টাকা")

    elif query.data == "profile":
        user = get_user(user_id)
        text = (f"👤 **প্রোফাইল তথ্য**\n\n"
                f"🆔 ID: `{user[0]}`\n"
                f"💰 বর্তমান ব্যালেন্স: {user[2]} টাকা\n"
                f"📈 মোট আয়: {user[3]} টাকা\n"
                f"📤 মোট উত্তোলন: {user[4]} টাকা")
        await query.message.reply_text(text, parse_mode="Markdown")

    elif query.data == "submit_file":
        await query.message.reply_text("📁 অনুগ্রহ করে আপনার `.xls` বা `.xlsx` এক্সেল ফাইলটি এখানে পাঠালুন।")

    elif query.data == "withdraw":
        user = get_user(user_id)
        if user[2] < 20:
            await query.message.reply_text("⚠️ উত্তোলনের জন্য সর্বনিম্ন ২০ টাকা ব্যালেন্স থাকতে হবে।")
        else:
            context.user_data['state'] = 'awaiting_withdraw'
            await query.message.reply_text("উত্তোলনের জন্য লিখুন:\n`মেথড(bKash/Nagad) নাম্বার পরিমাণ`\n\nউদাহরণ:\n`bKash 01700000000 50`", parse_mode="Markdown")

    elif query.data == "admin_panel" and user_id == ADMIN_ID:
        await query.message.reply_text("⚙️ **এডমিন প্যানেল Command List:**\n\n"
                                       "1. কারোর ব্যালেন্স বাড়াতে:\n`/addbal <USER_ID> <AMOUNT>`\n"
                                       "উদাহরণ: `/addbal 123456789 50`")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.file_name.endswith(('.xls', '.xlsx')):
        await update.message.reply_text("✅ আপনার ফাইল সফলভাবে জমা হয়েছে! এডমিন এটি চেক করবেন।")
        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=doc.file_id,
            caption=f"📂 **নতুন ফাইল জমা হয়েছে!**\nইউজার: @{update.effective_user.username}\nID: `{update.effective_user.id}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ শুধু মাত্র `.xls` বা `.xlsx` ফাইল অ্যালাউড।")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') == 'awaiting_withdraw':
        text = update.message.text
        context.user_data['state'] = None
        
        await update.message.reply_text("✅ আপনার উইথড্র রিকোয়েস্ট সফলভাবে পাঠানো হয়েছে!")
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚨 **নতুন Withdraw Request!**\n\nইউজার: @{update.effective_user.username}\nID: `{update.effective_user.id}`\nতথ্য: {text}",
            parse_mode="Markdown"
        )

async def admin_add_bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        update_balance(target_id, amount)
        await update.message.reply_text(f"✅ User `{target_id}` এর ব্যালেন্সে {amount} টাকা যোগ করা হয়েছে।")
        await context.bot.send_message(chat_id=target_id, text=f"🎉 আপনার অ্যাকাউন্টে {amount} টাকা যোগ করা হয়েছে!")
    except Exception as e:
        await update.message.reply_text("❌ ফরম্যাট ভুল! লিখুন: `/addbal <USER_ID> <AMOUNT>`")

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addbal", admin_add_bal))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    app.run_polling()