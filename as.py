import logging
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

# --- CONFIGURATION ---
BOT_TOKEN = ""
DB_URL = "" 
ADMIN_ID = 6250222523 # Tomar Telegram ID (get from @userinfobot)
BKASH_NUMBER = "01611026722"

# --- STATES ---
SELECT_LANG, SELECT_ROLE, RESELLER_LOGIN, ADD_MONEY_AMOUNT, ADD_MONEY_TRX = range(5)

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DB FUNCTIONS ---
def get_db():
    return psycopg2.connect(DB_URL)

def get_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    u = cur.fetchone()
    conn.close()
    return u

def create_user(user_id, username):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id, username) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING", (user_id, username))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
    conn.commit()
    conn.close()

# --- START & MENU ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        await admin_panel(update, context)
        return
    
    create_user(user.id, user.username)
    keyboard = [[InlineKeyboardButton("English 🇺🇸", callback_data='lang_en'), InlineKeyboardButton("বাংলা 🇧🇩", callback_data='lang_bn')]]
    await update.message.reply_text("Please select language / ভাষা নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_LANG

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btns = [
        [InlineKeyboardButton("স্টক (Stock)", callback_data='adm_stock'), InlineKeyboardButton("সেলস (Sales)", callback_data='adm_sales')],
        [InlineKeyboardButton("পেমেন্ট রিকোয়েস্ট", callback_data='adm_pay_req')] # New button later
    ]
    await context.bot.send_message(update.effective_chat.id, "👑 স্বাগতম বস!\nএডমিন প্যানেল:", reply_markup=InlineKeyboardMarkup(btns))

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    context.user_data['lang'] = lang
    
    # Update DB language
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang = %s WHERE user_id = %s", (lang, query.from_user.id))
    conn.commit()
    conn.close()

    text = "স্বাগতম! আপনি কি হিসেবে একসেস নিতে চান?" if lang == 'bn' else "Welcome! Select your role:"
    btns = [[InlineKeyboardButton("Customer", callback_data='role_customer'), InlineKeyboardButton("Reseller", callback_data='role_reseller')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(btns))
    return SELECT_ROLE

async def role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role = query.data.split('_')[1]
    if role == 'reseller':
        await query.message.reply_text("Enter Reseller ID:")
        return RESELLER_LOGIN
    await show_menu(update, context)
    return ConversationHandler.END

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    lang = user[2] if user else 'bn' # 2 is lang column
    
    if lang == 'bn':
        txt = "নিচের মেনু থেকে অপশন বেছে নিন:"
        btns = [
            [InlineKeyboardButton("দোকান 🛒", callback_data='menu_shop')],
            [InlineKeyboardButton("আমার প্রোফাইল 👤", callback_data='menu_profile'), InlineKeyboardButton("টাকা যোগ করুন 💰", callback_data='menu_addmoney')],
            [InlineKeyboardButton("সাপোর্ট 📞", callback_data='menu_support')]
        ]
    else:
        txt = "Select Option:"
        btns = [
            [InlineKeyboardButton("Shop 🛒", callback_data='menu_shop')],
            [InlineKeyboardButton("Profile 👤", callback_data='menu_profile'), InlineKeyboardButton("Add Money 💰", callback_data='menu_addmoney')],
            [InlineKeyboardButton("Support 📞", callback_data='menu_support')]
        ]
    
    if update.callback_query:
        await update.callback_query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(btns))
    else:
        await context.bot.send_message(update.effective_chat.id, txt, reply_markup=InlineKeyboardMarkup(btns))

# --- ADD MONEY LOGIC ---
async def add_money_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("💰 কত টাকা অ্যাড করতে চান?\nশুধুমাত্র সংখ্যা লিখুন (যেমন: 50, 100):")
    return ADD_MONEY_AMOUNT

async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text)
        context.user_data['amount'] = amount
        msg = (
            f"✅ অনুরোধ: {amount} টাকা\n"
            "━━━━━━━━━━━━\n"
            f"আপনার {amount} টাকা এই নাম্বারে Send Money করুন:\n\n"
            f"📞 `{BKASH_NUMBER}` (bKash)\n\n"
            "⚠️ টাকা পাঠানোর পর নিচের বক্সে Transaction ID (TrxID) লিখে পাঠান।"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
        return ADD_MONEY_TRX
    except ValueError:
        await update.message.reply_text("⚠️ ভুল ইনপুট। দয়া করে শুধুমাত্র ইংরেজি সংখ্যা লিখুন (যেমন: 100)।")
        return ADD_MONEY_AMOUNT

async def receive_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx_id = update.message.text
    amount = context.user_data['amount']
    user = update.effective_user
    
    # Save to DB
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO transactions (user_id, amount, trx_id) VALUES (%s, %s, %s) RETURNING id", (user.id, amount, trx_id))
    trx_db_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ আপনার রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে!\nঅ্যাডমিন চেক করে অ্যাপ্রুভ করলে ব্যালেন্স অ্যাড হয়ে যাবে।")

    # Notify Admin
    admin_msg = (
        "🔔 **New Deposit Request**\n"
        f"User: @{user.username} (ID: `{user.id}`)\n"
        f"Amount: {amount} Taka\n"
        f"TrxID: `{trx_id}`"
    )
    # Callback data format: action_trxDbId_userId_amount
    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"pay_yes_{trx_db_id}_{user.id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"pay_no_{trx_db_id}_{user.id}_{amount}")
        ]
    ]
    await context.bot.send_message(ADMIN_ID, admin_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    return ConversationHandler.END

# --- ADMIN ACTION HANDLER ---
async def admin_payment_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_') # ['pay', 'yes', 'trxId', 'userId', 'amount']
    
    action = data[1]
    trx_db_id = data[2]
    user_id = int(data[3])
    amount = int(data[4])
    
    conn = get_db()
    cur = conn.cursor()
    
    if action == 'yes':
        # Approve
        cur.execute("UPDATE transactions SET status = 'approved' WHERE id = %s", (trx_db_id,))
        cur.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
        conn.commit()
        
        await query.edit_message_text(f"✅ Approved Request #{trx_db_id}\nAdded {amount} tk to {user_id}")
        try:
            await context.bot.send_message(user_id, f"✅ আপনার {amount} টাকার পেমেন্ট সফল হয়েছে! ব্যালেন্স চেক করুন।")
        except:
            pass # User might have blocked bot
            
    else:
        # Reject
        cur.execute("UPDATE transactions SET status = 'rejected' WHERE id = %s", (trx_db_id,))
        conn.commit()
        await query.edit_message_text(f"❌ Rejected Request #{trx_db_id}")
        try:
            await context.bot.send_message(user_id, "❌ আপনার পেমেন্ট রিকোয়েস্ট বাতিল করা হয়েছে। প্রয়োজনে অ্যাডমিনের সাথে যোগাযোগ করুন।")
        except:
            pass
            
    conn.close()

# --- OTHER HANDLERS ---
async def menu_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == 'menu_profile':
        await query.answer()
        user = get_user(query.from_user.id)
        # user tuple: (id, username, lang, balance, role, joined)
        bal = user[3]
        role = user[4]
        await query.message.reply_text(f"👤 **Profile**\n🆔 ID: `{query.from_user.id}`\n💰 Balance: {bal} Taka\n🏷 Role: {role.upper()}", parse_mode='Markdown')

    elif data == 'menu_shop':
        await query.answer("দোকান শীঘ্রই আসছে! (Next Update)")
        
    elif data == 'menu_support':
        await query.answer()
        await query.message.reply_text(f"Support: @{update.effective_user.username}") # Change to admin user

# --- MAIN ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation for Add Money
    add_money_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_money_start, pattern='^menu_addmoney$')],
        states={
            ADD_MONEY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
            ADD_MONEY_TRX: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_trx)],
        },
        fallbacks=[CommandHandler('start', start)]
    )

    # Conversation for Start
    start_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_LANG: [CallbackQueryHandler(language_handler, pattern='^lang_')],
            SELECT_ROLE: [CallbackQueryHandler(role_handler, pattern='^role_')],
            RESELLER_LOGIN: [MessageHandler(filters.TEXT, start)] # Placeholder
        },
        fallbacks=[CommandHandler('start', start)]
    )

    app.add_handler(add_money_conv)
    app.add_handler(start_conv)
    app.add_handler(CallbackQueryHandler(admin_payment_action, pattern='^pay_'))
    app.add_handler(CallbackQueryHandler(menu_actions, pattern='^menu_'))

    print("Bot is running...")
    app.run_polling()
