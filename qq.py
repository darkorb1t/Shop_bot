import logging
import psycopg2
import random
import string
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# --- CONFIGURATION ---
TOKEN = '8036869041:AAHiFgQ7dQUjjkGt6W-OwZQ5MXFMM8SeWzM'   # আপনার টোকেন
ADMIN_ID = 6250222523            # অ্যাডমিন আইডি
ADMIN_USERNAME = "darkorb1t"
BKASH_NUMBER = "01611026722"

# Neon.tech Database URL
NEON_DB_URL = "postgres://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require"

# --- FAKE SERVER (For 24/7 Uptime) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_server)
    t.start()

# --- STATES ---
(SELECT_LANG, SELECT_ROLE, RESELLER_INPUT, 
 MAIN_STATE, 
 INPUT_MONEY, INPUT_TRX, INPUT_EMAIL, INPUT_COUPON, 
 INPUT_ADMIN_PROD, INPUT_ADMIN_COUPON, INPUT_BROADCAST) = range(11)

# --- DATABASE CONNECTION ---
def get_db_connection():
    return psycopg2.connect(NEON_DB_URL)

# --- INITIALIZE DATABASE ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, first_name TEXT, lang TEXT, role TEXT, balance INTEGER DEFAULT 0)''')
    # Products (Changed AUTOINCREMENT to SERIAL for Postgres)
    c.execute('''CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, type TEXT, name TEXT, description TEXT, price_cust INTEGER, price_res INTEGER, content TEXT, status TEXT DEFAULT 'unsold')''')
    # Resellers
    c.execute('''CREATE TABLE IF NOT EXISTS resellers (res_id TEXT, password TEXT)''')
    # Sales (Changed AUTOINCREMENT to SERIAL)
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, user_id BIGINT, product_name TEXT, price INTEGER, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Coupons
    c.execute('''CREATE TABLE IF NOT EXISTS coupons (code TEXT, percent INTEGER, limit_count INTEGER, used_count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# --- TEXTS (NO CHANGE) ---
TEXTS = {
    'EN': {
        'welcome': "👋 Welcome **{}**!\n\nSelect Access Role:",
        'menu_title': "👑 **Main Menu**\nChoose an option below:",
        'btn_shop': "🛒 Buy Products",
        'btn_profile': "👤 My Profile",
        'btn_add': "💰 Add Balance",
        'btn_orders': "📦 My Orders",
        'btn_sup': "☎️ Support / Help",
        'btn_lang': "🌐 Change Language",
        'stock_empty': "❌ Stock Empty!",
        'insufficient': "❌ Need {} BDT more!",
        'bought': "✅ **Purchased!**\n📦 Item: {}\n📝 Data: `{}`\n(Saved in 'My Orders')",
        'ask_email': "📧 Enter your Email:",
        'email_sent': "✅ Request Sent to Admin!",
        'dep_ask': "💰 Enter Amount (e.g. 50):",
        'dep_info': "💸 Send {} Tk to `{}`.\nEnter TrxID:",
        'req_sent': "✅ Deposit Request Sent!",
        'profile': "👤 **User:** {}\n🆔 **ID:** `{}`\n💰 **Balance:** `{} BDT`\n🎭 **Role:** {}",
        'my_orders': "📦 **Your Last 5 Orders:**\n\n{}",
        'no_orders': "❌ You haven't bought anything yet."
    },
    'BN': {
        'welcome': "👋 স্বাগতম **{}**!\n\nকিভাবে একসেস নিতে চান?",
        'menu_title': "👑 **মেইন মেনু**\nনিচের অপশন থেকে বেছে নিন:",
        'btn_shop': "🛒 পণ্য কিনুন",
        'btn_profile': "👤 আমার প্রোফাইল",
        'btn_add': "💰 টাকা যোগ করুন",
        'btn_orders': "📦 আমার অর্ডার",
        'btn_sup': "☎️ সাপোর্ট / সাহায্য",
        'btn_lang': "🌐 ভাষা পরিবর্তন",
        'stock_empty': "❌ স্টক শেষ!",
        'insufficient': "❌ আরো {} টাকা প্রয়োজন!",
        'bought': "✅ **ক্রয় সফল!**\n📦 পণ্য: {}\n📝 তথ্য: `{}`\n('আমার অর্ডার' মেনুতে সেভ আছে)",
        'ask_email': "📧 আপনার ইমেইল দিন:",
        'email_sent': "✅ অ্যাডমিনের কাছে রিকোয়েস্ট গেছে!",
        'dep_ask': "💰 টাকার পরিমাণ লিখুন (যেমন: 50):",
        'dep_info': "💸 {} টাকা এই নাম্বারে পাঠান: `{}`।\nনিচে TrxID দিন:",
        'req_sent': "✅ রিকোয়েস্ট পাঠানো হয়েছে!",
        'profile': "👤 **নাম:** {}\n🆔 **আইডি:** `{}`\n💰 **ব্যালেন্স:** `{} টাকা`\n🎭 **রোল:** {}",
        'my_orders': "📦 **আপনার শেষ ৫টি অর্ডার:**\n\n{}",
        'no_orders': "❌ আপনি এখনো কিছু কেনেননি."
    }
}

# --- HELPERS ---
def get_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_or_update_user(user, lang='BN'):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=%s", (user.id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, first_name, lang, role) VALUES (%s, %s, %s, 'customer')", (user.id, user.first_name, lang))
    else:
        c.execute("UPDATE users SET first_name=%s WHERE user_id=%s", (user.first_name, user.id))
    conn.commit()
    conn.close()

# --- START FLOW ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_or_update_user(user)
    print(f"USER ID: {user.id}") 
    
    kb = [
        [InlineKeyboardButton("English 🇺🇸", callback_data='lang_EN')],
        [InlineKeyboardButton("বাংলা 🇧🇩", callback_data='lang_BN')]
    ]
    await update.message.reply_text("Please Select Language / ভাষা নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(kb))
    return SELECT_LANG

async def language_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, query.from_user.id))
    conn.commit()
    conn.close()
    
    t = TEXTS[lang]
    kb = [
        [InlineKeyboardButton("👤 Customer (কাস্টমার)", callback_data='role_customer')],
        [InlineKeyboardButton("🔐 Reseller (রিসেলার)", callback_data='role_reseller')]
    ]
    await query.message.edit_text(t['welcome'].format(update.effective_user.first_name), reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    return SELECT_ROLE

async def role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    role = query.data.split('_')[1]
    uid = query.from_user.id
    
    if role == 'reseller':
        await query.message.reply_text("🔐 Enter Reseller ID:")
        return RESELLER_ID_INPUT
    else:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET role='customer' WHERE user_id=%s", (uid,))
        conn.commit()
        conn.close()
        await show_main_menu(update, context)
        return MAIN_MENU

# --- RESELLER LOGIN ---
async def res_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_id'] = update.message.text
    await update.message.reply_text("🔑 Enter Password:")
    return RESELLER_PASS_INPUT

async def res_pass_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rid = context.user_data.get('temp_id')
    pwd = update.message.text
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM resellers WHERE res_id=%s AND password=%s", (rid, pwd))
    
    if c.fetchone():
        c.execute("UPDATE users SET role='reseller' WHERE user_id=%s", (update.effective_user.id,))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ Login Success!")
        await show_main_menu(update, context)
        return MAIN_MENU
    else:
        conn.close()
        await update.message.reply_text("❌ Fail! Try again (/start)")
        return RESELLER_ID_INPUT

# --- MAIN MENU ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    lang = user[2]
    t = TEXTS[lang]
    
    kb = [
        [InlineKeyboardButton(t['btn_shop'], callback_data='menu_shop')],
        [InlineKeyboardButton(t['btn_profile'], callback_data='menu_prof')],
        [InlineKeyboardButton(t['btn_add'], callback_data='menu_add')],
        [InlineKeyboardButton(t['btn_orders'], callback_data='menu_orders')],
        [InlineKeyboardButton(t['btn_sup'], callback_data='menu_sup')],
        [InlineKeyboardButton(t['btn_lang'], callback_data='menu_lang')]
    ]
    
    msg = t['menu_title']
    if update.callback_query:
        await update.callback_query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

# --- MENU HANDLER ---
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = get_user(query.from_user.id)
    lang = user[2]
    t = TEXTS[lang]

    if data == "menu_prof":
        await query.message.reply_text(t['profile'].format(user[1], user[0], user[4], user[3]), parse_mode='Markdown')
        return MAIN_MENU
        
    elif data == "menu_add":
        await query.message.reply_text(t['dep_ask'])
        return ADD_MONEY_AMOUNT
        
    elif data == "menu_sup":
        await query.message.reply_text(f"Admin: @{ADMIN_USERNAME}")
        return MAIN_MENU

    elif data == "menu_lang":
        await start(query, context)
        return SELECT_LANG

    elif data == "menu_orders":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT product_name, content, date FROM orders WHERE user_id=%s ORDER BY id DESC LIMIT 5", (user[0],))
        orders = c.fetchall()
        conn.close()
        
        if not orders:
            await query.message.reply_text(t['no_orders'])
        else:
            msg = ""
            for o in orders:
                msg += f"📦 {o[0]}\n📄 {o[1]}\n🕒 {o[2]}\n\n"
            await query.message.reply_text(t['my_orders'].format(msg))
        return MAIN_MENU

    elif data == "menu_shop":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name, COUNT(*), price_cust, price_res FROM products WHERE status='unsold' GROUP BY name, price_cust, price_res")
        stock = c.fetchall()
        conn.close()
        
        if not stock:
            await query.message.reply_text(t['stock_empty'])
            return MAIN_MENU
        
        kb = []
        for p in stock:
            price = p[3] if user[3] == 'reseller' else p[2]
            kb.append([InlineKeyboardButton(f"{p[0]} | ৳{price} | Stock: {p[1]}", callback_data=f"buy_{p[0]}")])
        
        await query.message.reply_text("🛒 **Shop:**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return MAIN_MENU

# --- BUY & DEPOSIT ---
async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    name = q.data.split('_')[1]
    uid = q.from_user.id
    user = get_user(uid)
    lang = user[2]
    t = TEXTS[lang]
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, type, price_cust, price_res, content FROM products WHERE name=%s AND status='unsold' LIMIT 1", (name,))
    item = c.fetchone()
    
    if not item:
        conn.close()
        await q.answer(t['stock_empty'], show_alert=True)
        return MAIN_MENU
        
    pid, ptype, pc, pr, content = item
    cost = pr if user[3] == 'reseller' else pc
    
    if user[4] < cost:
        conn.close()
        await q.answer(t['insufficient'].format(cost - user[4]), show_alert=True)
        return MAIN_MENU

    if ptype == 'access':
        conn.close()
        context.user_data['buy_pid'] = pid
        context.user_data['buy_cost'] = cost
        await q.message.reply_text(t['ask_email'])
        return GET_USER_EMAIL
    
    c.execute("UPDATE products SET status='sold' WHERE id=%s", (pid,))
    c.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s", (cost, uid))
    c.execute("INSERT INTO orders (user_id, product_name, content) VALUES (%s,%s,%s)", (uid, name, content))
    conn.commit()
    conn.close()
    
    await context.bot.send_message(ADMIN_ID, f"📢 Sale: {name} to {user[1]}")
    await q.message.reply_text(t['bought'].format(name, content), parse_mode='Markdown')
    return MAIN_MENU

# --- EMAIL & DEPOSIT STEPS ---
async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text
    pid = context.user_data['buy_pid']
    cost = context.user_data['buy_cost']
    uid = update.effective_user.id
    
    kb = [[InlineKeyboardButton("✅ Grant", callback_data=f"g_{uid}_{pid}_{cost}"), InlineKeyboardButton("❌ Reject", callback_data=f"f_{uid}")]]
    await context.bot.send_message(ADMIN_ID, f"Access Req:\nUser: {uid}\nEmail: {email}\nCost: {cost}", reply_markup=InlineKeyboardMarkup(kb))
    
    user = get_user(uid)
    await update.message.reply_text(TEXTS[user[2]]['email_sent'])
    return MAIN_MENU

async def get_amt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = int(update.message.text)
        context.user_data['amt'] = amt
        u = get_user(update.effective_user.id)
        await update.message.reply_text(TEXTS[u[2]]['dep_info'].format(amt, BKASH_NUMBER), parse_mode='Markdown')
        return ADD_MONEY_TRX
    except: return ADD_MONEY_AMOUNT

async def get_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx = update.message.text
    amt = context.user_data['amt']
    uid = update.effective_user.id
    kb = [[InlineKeyboardButton("Approve", callback_data=f"ok_{uid}_{amt}"), InlineKeyboardButton("Reject", callback_data=f"no_{uid}")]]
    await context.bot.send_message(ADMIN_ID, f"Dep: {amt}\nTrx: {trx}", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("✅ Request Sent!")
    return MAIN_MENU

# --- ADMIN ACTIONS ---
async def admin_act(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    conn = get_db_connection()
    c = conn.cursor()
    
    if d.startswith('ok'):
        _, u, a = d.split('_')
        c.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (int(a), int(u)))
        conn.commit()
        await context.bot.send_message(int(u), f"✅ Added {a} Tk")
        await q.edit_message_text(f"Approved {a}")
    elif d.startswith('g'):
        _, u, p, a = d.split('_')
        c.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (int(a), int(u)))
        c.execute("UPDATE products SET status='sold' WHERE id=%s", (int(p),))
        c.execute("INSERT INTO orders (user_id, product_name, content) VALUES (%s, 'Access Product', 'Check Email')",(int(u),))
        conn.commit()
        await context.bot.send_message(int(u), "✅ Access Granted! Check Email.")
        await q.edit_message_text("Granted.")
    else:
        u = d.split('_')[1]
        await context.bot.send_message(int(u), "❌ Rejected.")
        await q.edit_message_text("Rejected.")
    
    conn.close()

# --- ADMIN COMMANDS ---
async def admin_pnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    kb = [[InlineKeyboardButton("➕ Add Product", callback_data='adm_p')], [InlineKeyboardButton("🆔 Make Reseller", callback_data='adm_r')]]
    await update.message.reply_text("Admin Panel", reply_markup=InlineKeyboardMarkup(kb))

async def admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data
    if d == 'adm_p':
        await update.callback_query.message.reply_text("Fmt: Type|Name|CustP|ResP|Data\nEx: text|Netflx|100|80|u:p")
        return ADMIN_ADD_PRODUCT
    elif d == 'adm_r':
        res = ''.join(random.choices(string.digits, k=10))
        pas = ''.join(random.choices(string.ascii_letters, k=8))
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO resellers (res_id, password) VALUES (%s,%s)", (res, pas))
        conn.commit()
        conn.close()
        
        await update.callback_query.message.reply_text(f"ID: `{res}`\nPass: `{pas}`", parse_mode='Markdown')

async def save_prod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        p = update.message.text.split('|')
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO products (type,name,price_cust,price_res,content) VALUES (%s,%s,%s,%s,%s)", (p[0],p[1],int(p[2]),int(p[3]),p[4]))
        conn.commit()
        conn.close()
        await update.message.reply_text("Added.")
    except: await update.message.reply_text("Error.")
    return ADMIN_ADD_PRODUCT

def main():
    # Init DB
    init_db()
    # Start Fake Server
    keep_alive()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('admin', admin_pnl))
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_LANG: [CallbackQueryHandler(language_choice, pattern='^lang_')],
            SELECT_ROLE: [CallbackQueryHandler(role_handler, pattern='^role_')],
            RESELLER_ID_INPUT: [MessageHandler(filters.TEXT, res_id_input)],
            RESELLER_PASS_INPUT: [MessageHandler(filters.TEXT, res_pass_input)],
            MAIN_MENU: [CallbackQueryHandler(menu_callback, pattern='^menu_'), CallbackQueryHandler(buy_handler, pattern='^buy_')],
            ADD_MONEY_AMOUNT: [MessageHandler(filters.TEXT, get_amt)],
            ADD_MONEY_TRX: [MessageHandler(filters.TEXT, get_trx)],
            GET_USER_EMAIL: [MessageHandler(filters.TEXT, get_email)],
            ADMIN_ADD_PRODUCT: [MessageHandler(filters.TEXT, save_prod)]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    app.add_handler(conv)
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_cb, pattern='adm_')],
        states={ADMIN_ADD_PRODUCT: [MessageHandler(filters.TEXT, save_prod)]},
        fallbacks=[CommandHandler('start', start)]
    ))
    app.add_handler(CallbackQueryHandler(admin_act, pattern='^(ok|no|g|f)_'))
    
    print("Bot Running 24/7 with NeonDB...")
    app.run_polling()

if __name__ == '__main__':
    main()
