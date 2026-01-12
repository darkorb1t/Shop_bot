import logging
import psycopg2
from psycopg2 import pool
import threading
import random
import string
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.request import HTTPXRequest 

# --- CONFIGURATION ---
TOKEN = '8036869041:AAHiFgQ7dQUjjkGt6W-OwZQ5MXFMM8SeWzM'   # টোকেন বসাও
ADMIN_ID = 6250222523            # অ্যাডমিন আইডি
ADMIN_USERNAME = "darkorb1t"
BKASH_NUMBER = "01611026722"
# Neon.tech Database URL (আপনার URL এখানে বসান)
NEON_DB_URL = "postgres://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require"
# Create a connection pool (Min 1, Max 20 connections)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 20, NEON_DB_URL)

# --- FAKE SERVER (For 24/7) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

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

# --- DATABASE ---
def get_db_connection():
    try:
        # পুল থেকে কানেকশন নেওয়া
        conn = db_pool.getconn()
        
        # কানেকশন তাজা আছে কিনা চেক করা (Health Check)
        if conn.closed:
            db_pool.putconn(conn, close=True) # মরা কানেকশন ফেলে দেওয়া
            return db_pool.getconn() # নতুন কানেকশন নেওয়া
            
        # ডাবল চেক: সার্ভার কি কানেকশন কেটে দিয়েছে?
        with conn.cursor() as c:
            c.execute("SELECT 1") # পিং করা
            
        return conn
        
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        # যদি কোনো কারণে কানেকশন মরে গিয়ে থাকে, জোর করে নতুন কানেকশন তৈরি করা
        try:
            return psycopg2.connect(NEON_DB_URL)
        except:
            # একদমই উপায় না থাকলে আবার পুল ট্রাই করা
            return db_pool.getconn()
            
    
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Check connection health
    try:
        c.execute("SELECT 1")
    except psycopg2.OperationalError:
        # If connection died, get a new one
        conn = get_db_connection()
        c = conn.cursor()
        
    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, first_name TEXT, lang TEXT, role TEXT, balance INTEGER DEFAULT 0)''')
    # Products
    c.execute('''CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, type TEXT, name TEXT, description TEXT, price_cust INTEGER, price_res INTEGER, content TEXT, status TEXT DEFAULT 'unsold')''')
    # Resellers
    c.execute('''CREATE TABLE IF NOT EXISTS resellers (res_id TEXT, password TEXT)''')
    # Sales
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, user_id BIGINT, product_name TEXT, price INTEGER, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Coupons
    c.execute('''CREATE TABLE IF NOT EXISTS coupons (code TEXT, percent INTEGER, limit_count INTEGER, used_count INTEGER DEFAULT 0)''')
        # ডাটাবেসের সব নামের আন্ডারস্কোর মুছে স্পেস করে দিবে
    c.execute("UPDATE products SET name = REPLACE(name, '_', ' ')")
    
    conn.commit()
    db_pool.putconn(conn)
    
    
  

# --- TEXTS ---
TEXTS = {
    'EN': {
        'welcome_msg': "👋 **Hello Dear {}!**\n\nWelcome to our Digital Shop. We are delighted to have you here.\n\nYour account is fully ready! 🚀\nHow would you like to proceed?",
        'role_btn_cust': "👤 Customer Login",
        'role_btn_res': "🔐 Reseller Login",
        'res_ask_id': "🔐 **Reseller Login**\n\nPlease enter your **Reseller ID**:",
        'res_ask_pass': "🔑 **Password Required**\n\nPlease enter your Password:",
        'res_fail': "❌ **Login Failed!**\nIncorrect ID or Password. Please select your role again.",
        'menu_btns': ["🛒 Shop", "👤 My Profile", "💰 Add Money", "🎟 Coupon", "🤝 Refer", "☎️ Support"],
        'menu_title': "🌹 **Main Menu**\nChoose an option below:",
        'shop_empty': "😔 **Sorry!**\nThe shop is currently empty. Please come back later.",
        'buy_btn': "⚡ Buy Now ({} Tk)",
        'insufficient': "😔 **Insufficient Balance!**\nYou need **{} Tk** more to purchase this item.",
        'bought': "🎉 **Congratulations!**\nPurchase Successful.\n\n📦 **Item:** {}\n📝 **Details:**\n`{}`\n\nThank you for being with us! ❤️",
        'ask_money': "💳 **Add Balance**\n\nDear User, how much money do you want to add?\nPlease write the amount (e.g., 50, 100):",
        'ask_trx': "✅ **Request: {} Tk**\n━━━━━━━━━━━━\nPlease Send Money to:\n📞 `{}` (bKash Personal)\n\n⚠️ After sending, please type the **Transaction ID (TrxID)** below:",
        'req_sent': "✅ **Request Submitted!**\n\nYour deposit request has been sent to the Admin. Please wait for confirmation. ⏳",
        'profile': "👤 **User Profile**\n\nName: {}\nID: `{}`\n💰 Balance: `{} Tk`\n🎭 Role: {}",
        'ask_email': "📧 **Email Required**\n\nTo access this product, please provide your **Email Address**:",
        'email_sent': "✅ **Request Sent!**\nAdmin will check and grant access shortly.",
        'coupon_ask': "🎟 **Redeem Coupon**\n\nPlease enter your Coupon Code:",
        'coupon_applied': "✅ **Awesome!**\nCoupon Applied. You will get **{}% Discount** on your next purchase! 🥳",
        'support': "📞 **Support Center**\n\nFor any help, contact our Admin:\n👤 @{}"
    },
    'BN': {
        'welcome_msg': "আসসালামু আলাইকুম, প্রিয় **{}**! ❤️\n\nআমাদের ডিজিটাল শপে আপনাকে স্বাগতম।\nআপনার অ্যাকাউন্ট ব্যবহারের জন্য প্রস্তুত।\n\nআপনি কিভাবে একসেস নিতে চান?",
        'role_btn_cust': "👤 কাস্টমার",
        'role_btn_res': "🔐 রিসেলার",
        'res_ask_id': "🔐 **রিসেলার লগইন**\n\nঅনুগ্রহ করে আপনার **রিসেলার আইডি** দিন:",
        'res_ask_pass': "🔑 **পাসওয়ার্ড প্রয়োজন**\n\nদয়া করে আপনার পাসওয়ার্ড দিন:",
        'res_fail': "❌ **লগইন ব্যর্থ হয়েছে!**\nভুল আইডি বা পাসওয়ার্ড। অনুগ্রহ করে আবার রোল নির্বাচন করুন।",
        'menu_btns': ["🛒 দোকান", "👤 আমার প্রোফাইল", "💰 টাকা যোগ করুন", "🎟 কুপন", "🤝 রেফার করুন", "☎️ সাপোর্ট"],
        'menu_title': "🌹 **মেইন মেনু**\nনিচের অপশন থেকে বেছে নিন:",
        'shop_empty': "😔 **দুঃখিত!**\nবর্তমানে দোকানে কোনো পণ্য নেই। অনুগ্রহ করে পরে আবার চেক করুন।",
        'buy_btn': "⚡ কিনুন ({} টাকা)",
        'insufficient': "😔 **পর্যাপ্ত ব্যালেন্স নেই!**\nএই পণ্যটি কিনতে আপনার আরো **{} টাকা** প্রয়োজন।",
        'bought': "🎉 **অভিনন্দন!**\nআপনার ক্রয় সফল হয়েছে।\n\n📦 **পণ্য:** {}\n📝 **তথ্য:**\n`{}`\n\nআমাদের সাথে থাকার জন্য ধন্যবাদ! ❤️",
        'ask_money': "💳 **টাকা যোগ করুন**\n\nপ্রিয় গ্রাহক, আপনি কত টাকা অ্যাড করতে চান?\nটাকার পরিমাণ লিখুন (যেমন: 50, 100):",
        'ask_trx': "✅ **অনুরোধ: {} টাকা**\n━━━━━━━━━━━━\nআপনার {} টাকা এই নাম্বারে সেন্ড মানি করুন:\n📞 `{}` (bKash)\n\n⚠️ টাকা পাঠানোর পর নিচের বক্সে **Transaction ID (TrxID)** লিখে পাঠান।",
        'req_sent': "✅ **অনুরোধ জমা হয়েছে!**\n\nআপনার রিকোয়েস্টটি অ্যাডমিনের কাছে পাঠানো হয়েছে। অনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন। ⏳",
        'profile': "👤 **প্রোফাইল**\n\nনাম: {}\nআইডি: `{}`\n💰 ব্যালেন্স: `{} টাকা`\n🎭 রোল: {}",
        'ask_email': "📧 **ইমেইল প্রয়োজন**\n\nএই পণ্যটি একসেস করতে আপনার **ইমেইল এড্রেস** দিন:",
        'email_sent': "✅ **রিকোয়েস্ট পাঠানো হয়েছে!**\nঅ্যাডমিন চেক করে পারমিশন দিয়ে দিবেন।",
        'coupon_ask': "🎟 **কুপন ব্যবহার**\n\nআপনার কুপন কোডটি লিখুন:",
        'coupon_applied': "✅ **দারুণ!**\nকুপন চালু হয়েছে। পরবর্তী কেনাকাটায় আপনি **{}% ডিসকাউন্ট** পাবেন! 🥳",
        'support': "📞 **সাপোর্ট**\n\nযেকোনো প্রয়োজনে যোগাযোগ করুন:\n👤 @{}"
    }
}

# --- HELPERS ---
def get_user(uid):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=%s", (uid,))
        res = c.fetchone()
        return res
    except psycopg2.OperationalError:
        # প্রথমবার ফেইল করলে কানেকশন রিসেট করে আবার চেষ্টা করবে
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=%s", (uid,))
        res = c.fetchone()
        return res
    finally:
        try:
            db_pool.putconn(conn)
        except:
            pass
          
def create_user(user):
    # আগে চেক করি ইউজার আছে কিনা
    if get_user(user.id):
        return

    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO users (user_id, first_name, lang, role) VALUES (%s, %s, 'BN', 'customer')", (user.id, user.first_name))
        conn.commit()
    except psycopg2.OperationalError:
        # ইনসার্ট ফেইল করলে আবার চেষ্টা
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO users (user_id, first_name, lang, role) VALUES (%s, %s, 'BN', 'customer')", (user.id, user.first_name))
        conn.commit()
    finally:
        try:
            db_pool.putconn(conn)
        except:
            pass
          
      

# --- START & LANG ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # ১. সেইফ ইউজার ক্রিয়েশন (Safe User Creation)
    try:
        create_user(user)
    except Exception as e:
        print(f"DB Login Error: {e}") 
    
    # ২. ইউজার ডাটা চেক করা
    db_user = get_user(user.id)

    # ৩. স্মার্ট চেক: যদি ইউজার আগে থেকেই থাকে এবং ভাষা সেট করা থাকে
    # (db_user[2] হলো ভাষা কলাম)
    if db_user and db_user[2] in ['BN', 'EN']:
        # ওয়েলকাম মেসেজ দিয়ে সরাসরি মেইন মেনু
        await update.message.reply_text(f"👋 Welcome back, **{user.first_name}**!", parse_mode='Markdown')
        await show_main_menu(update, context)
        return MAIN_STATE

    # ৪. যদি নতুন ইউজার হয় অথবা ভাষা সেট করা না থাকে, তাহলে বাটন দেখাবে
    kb = [[InlineKeyboardButton("English 🇺🇸", callback_data='lang_EN'), InlineKeyboardButton("বাংলা 🇧🇩", callback_data='lang_BN')]]
    await update.message.reply_text("Please select your language / ভাষা নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(kb))
    return SELECT_LANG
    

async def lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lang_code = query.data.split('_')[1] 
    user_id = query.from_user.id

    # ডাটাবেসে ভাষা আপডেট করা
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang_code, user_id))
    conn.commit()
    db_pool.putconn(conn)

    # কনফার্মেশন মেসেজ
    if lang_code == 'EN':
        await query.edit_message_text("✅ Language set to **English**!", parse_mode='Markdown')
    else:
        await query.edit_message_text("✅ ভাষা **বাংলা** সিলেক্ট করা হয়েছে!", parse_mode='Markdown')
        
    # --- পরিবর্তন: মেনুর বদলে এখন রোল সিলেক্ট করতে বলবে ---
    await ask_role_screen(update, context)
    return SELECT_ROLE
    
    
    

# --- ROLE & LOGIN ---
async def ask_role_screen(update: Update, context, lang):
    t = TEXTS[lang]
    user_name = update.effective_user.first_name
    kb = [[InlineKeyboardButton(t['role_btn_cust'], callback_data='role_cust'), InlineKeyboardButton(t['role_btn_res'], callback_data='role_res')]]
    msg_text = t['welcome_msg'].format(user_name)
    if update.callback_query: await update.callback_query.message.edit_text(msg_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else: await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    return SELECT_ROLE

async def role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    
    # Lang check for text (Optional optimization: pass lang if possible, else fetch)
    # Ekhane simple rakha holo logic thik rekhe
    
    if data == 'role_cust':
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET role='customer' WHERE user_id=%s", (uid,))
        conn.commit()
        db_pool.putconn(conn)  # <-- Fixed
        await show_main_menu(update, context)
        return MAIN_STATE
        
    elif data == 'role_res':
        # Reseller e kono DB update nei, tai direct input e pathano holo
        await q.message.reply_text("🔐 Enter Reseller ID:") # Text ta language onujayi dynamic kora jay
        return RESELLER_INPUT

async def reseller_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    
    if text.startswith('/'): return await start(update, context)

    conn = get_db_connection()
    c = conn.cursor()

    if 'awaiting_pass' in context.user_data:
        rid = context.user_data['temp_rid']
        c.execute("SELECT * FROM resellers WHERE res_id=%s AND password=%s", (rid, text))
        if c.fetchone():
            c.execute("UPDATE users SET role='reseller' WHERE user_id=%s", (uid,))
            conn.commit()
            del context.user_data['awaiting_pass']
            await update.message.reply_text("✅ Login Successful! Welcome Boss.")
            await show_main_menu(update, context)
            db_pool.putconn(conn)  # <-- Fixed
            return MAIN_STATE
        else:
            del context.user_data['awaiting_pass']
            await update.message.reply_text("❌ Login Failed! Try again.") # Simplified text
            db_pool.putconn(conn)  # <-- Fixed
            # Ekhane abar role screen e pathano jete pare ba input e
            return await start(update, context) 

    c.execute("SELECT * FROM resellers WHERE res_id=%s", (text,))
    if c.fetchone():
        context.user_data['temp_rid'] = text
        context.user_data['awaiting_pass'] = True
        await update.message.reply_text("🔑 Enter Password:")
        db_pool.putconn(conn)  # <-- Fixed
        return RESELLER_INPUT
    else:
        await update.message.reply_text("❌ Invalid ID.")
        db_pool.putconn(conn)  # <-- Fixed
        return await start(update, context)
        

# --- MENU & NAVIGATION ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id)
    
    lang = db_user[2] if db_user else 'BN'
    role = db_user[3] if db_user else 'customer'
    balance = db_user[4] if db_user else 0

    if lang == 'EN':
        txt = f"🏠 **Main Menu**\n\n👤 User: {user.first_name}\n💰 Balance: {balance} BDT\n\nSelect an option:"
        btn_shop = "📦 Shop"
        btn_profile = "👤 Profile"
        btn_deposit = "💰 Deposit"
        btn_coupon = "🎟 Redeem Coupon"
        btn_refer = "🤝 Refer & Earn"
        btn_support = "☎️ Support"
        btn_reseller = "🔐 Reseller Panel"
        btn_change = "🔄 Change Language / Role"
    else:
        txt = f"🏠 **মেইন মেনু**\n\n👤 ইউজার: {user.first_name}\n💰 ব্যালেন্স: {balance} BDT\n\nঅপশন সিলেক্ট করুন:"
        btn_shop = "📦 শপ / কেনাকাটা"
        btn_profile = "👤 প্রোফাইল"
        btn_deposit = "💰 ডিপোজিট"
        btn_coupon = "🎟 কুপন ব্যবহার"
        btn_refer = "🤝 রেফার ও আর্ন"
        btn_support = "☎️ সাপোর্ট"
        btn_reseller = "🔐 রিসেলার প্যানেল"
        btn_change = "🔄 ভাষা / রোল পরিবর্তন"

    kb = [
        [InlineKeyboardButton(btn_shop, callback_data='menu_stock'), InlineKeyboardButton(btn_profile, callback_data='menu_profile')],
        [InlineKeyboardButton(btn_deposit, callback_data='menu_deposit'), InlineKeyboardButton(btn_coupon, callback_data='menu_coupon')],
        [InlineKeyboardButton(btn_refer, callback_data='menu_refer'), InlineKeyboardButton(btn_support, callback_data='menu_support')]
    ]

    if role in ['reseller', 'admin']:
        kb.append([InlineKeyboardButton(btn_reseller, callback_data='menu_reseller_panel')])

    # ফিক্স: বাটনের আইডি 'menu_' দিয়ে শুরু হতে হবে
    kb.append([InlineKeyboardButton(btn_change, callback_data='menu_reset')])

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        except:
             await update.callback_query.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        
        
    
async def universal_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    
    user = get_user(uid)
    lang = user[2]
    t = TEXTS[lang]
    
    conn = get_db_connection()
    c = conn.cursor()

    try:
        # --- ১. ভাষা/রোল পরিবর্তন (ফিক্সড আইডি: menu_reset) ---
        if d == 'menu_reset':
            kb = [[InlineKeyboardButton("English 🇺🇸", callback_data='lang_EN'), InlineKeyboardButton("বাংলা 🇧🇩", callback_data='lang_BN')]]
            await q.message.reply_text("Please select your language / ভাষা নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(kb))
            return SELECT_LANG

        # --- ২. মেইন মেনু ---
        elif d == 'menu_back' or d == 'menu_main':
            await show_main_menu(update, context)
            return MAIN_STATE

        # --- ৩. রিসেলার প্যানেল ---
        elif d == 'menu_reseller_panel':
            kb_res = [
                # ফিক্স: এখানেও আইডি 'menu_reset' করা হলো
                [InlineKeyboardButton("🔄 Change Language / Role", callback_data='menu_reset')],
                [InlineKeyboardButton("🏠 Back to Shop", callback_data='menu_main')]
            ]
            await q.edit_message_text("🔐 **Reseller Panel**\n\nঅপশন সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb_res), parse_mode='Markdown')
            return MAIN_STATE

        # --- ৪. শপ / কেনাকাটা ---
        elif d == 'menu_stock': 
            c.execute("SELECT DISTINCT ON (name) name, description, price_cust, price_res, type FROM products WHERE status='unsold' OR type='file' OR type='access'")
            prods = c.fetchall()
            
            if not prods:
                kb_back = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
                await q.message.reply_text(t['shop_empty'], reply_markup=InlineKeyboardMarkup(kb_back))
            else:
                await q.message.reply_text("🛒 **SHOP ITEMS:**", parse_mode='Markdown')
                for p in prods:
                    name, desc, pc, pr, ptype = p
                    price = pr if user[3] == 'reseller' else pc
                    kb = [[InlineKeyboardButton(t['buy_btn'].format(price), callback_data=f"buy_{name}")]]
                    await context.bot.send_message(uid, f"📦 **{name}**\n📄 {desc}\n💰 Price: {price} Tk", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
                
                kb_back = [[InlineKeyboardButton("🔙 Back to Shop Menu", callback_data="menu_back")]]
                await context.bot.send_message(uid, "👇 কেনাকাটা শেষ হলে মেনুতে ফিরে যান:", reply_markup=InlineKeyboardMarkup(kb_back))
            return MAIN_STATE

        # --- ৫. অন্যান্য বাটন ---
        elif d == 'menu_profile':
            kb_back = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
            await q.message.reply_text(t['profile'].format(user[1], uid, user[4], user[3]), parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb_back))
            
        elif d == 'menu_deposit':
            await q.message.reply_text(t['ask_money'])
            return INPUT_MONEY

        elif d == 'menu_coupon':
            await q.message.reply_text(t['coupon_ask'])
            return INPUT_COUPON

        elif d == 'menu_refer':
            kb_back = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
            link = f"https://t.me/{context.bot.username}?start=ref_{uid}"
            await q.message.reply_text(f"🤝 **Refer Link:**\n`{link}`\n\n🎁 Bonus: 1 Tk per refer!", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb_back))

        elif d == 'menu_support':
            kb_back = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
            await q.message.reply_text(t['support'].format(ADMIN_USERNAME), reply_markup=InlineKeyboardMarkup(kb_back))

    except Exception as e:
        print(f"Menu Error: {e}")
        await q.message.reply_text("⚠️ Something went wrong!")
        
    finally:
        db_pool.putconn(conn)
    
    return MAIN_STATE
                                                                                                   
                                                        

# --- BUY LOGIC ---
async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    name = q.data.split('_')[1]
    uid = q.from_user.id
    username = q.from_user.username
    u_tag = f"@{username}" if username else "No Username"
    
    user = get_user(uid)
    lang = user[2]
    t = TEXTS[lang]
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, type, price_cust, price_res, content FROM products WHERE name=%s AND (status='unsold' OR type='file' OR type='access') LIMIT 1", (name,))
    item = c.fetchone()
    
    if not item: 
        db_pool.putconn(conn)
        return await q.answer("❌ Stock Ended!", show_alert=True)
    
    pid, ptype, pc, pr, content = item
    base_price = pr if user[3] == 'reseller' else pc
    discount = context.user_data.get('disc', 0)
    final_price = int(base_price - (base_price * discount / 100))
    
    if user[4] < final_price: 
        db_pool.putconn(conn)
        return await q.answer(t['insufficient'].format(final_price - user[4]), show_alert=True)
        
    if ptype == 'access':
        # Access type e sales record ekhon hobe na, admin grant korle hobe
        context.user_data['buy_data'] = (pid, final_price, name)
        await q.message.reply_text(t['ask_email'])
        db_pool.putconn(conn)
        return INPUT_EMAIL
    
    if ptype == 'account':
        c.execute("UPDATE products SET status='sold' WHERE id=%s", (pid,))
        
    # Instant Purchase Logic
    c.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s", (final_price, uid))
    c.execute("INSERT INTO sales (user_id, product_name, price) VALUES (%s,%s,%s)", (uid, name, final_price))
    conn.commit()
    db_pool.putconn(conn)
    
    if 'disc' in context.user_data: del context.user_data['disc']
    
    # --- FIX FOR ISSUE 2 ---
    await context.bot.send_message(ADMIN_ID, f"📢 **Sold (Instant):** {name}\n👤 Buyer: {u_tag} (`{uid}`)")
    
    await q.message.reply_text(t['bought'].format(name, content), parse_mode='Markdown') 
    await show_main_menu(update, context)
    return MAIN_STATE
  
    
# --- INPUTS ---
async def input_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = int(update.message.text)
        context.user_data['amt'] = amt
        u = get_user(update.effective_user.id)
        await update.message.reply_text(TEXTS[u[2]]['ask_trx'].format(amt, amt, BKASH_NUMBER), parse_mode='Markdown')
        return INPUT_TRX
    except: 
        await update.message.reply_text("⚠️ Only Numbers (e.g. 50). Try again:")
        return INPUT_MONEY

async def input_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx = update.message.text
    amt = context.user_data['amt']
    uid = update.effective_user.id
    kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"ok_{uid}_{amt}"), InlineKeyboardButton("❌ Reject", callback_data=f"no_{uid}")]]
    await context.bot.send_message(ADMIN_ID, f"🔔 **Deposit**\nUser: {uid}\nAmt: {amt}\nTrx: `{trx}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    await update.message.reply_text(TEXTS[get_user(uid)[2]]['req_sent'])
    return MAIN_STATE

async def input_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text
    pid, cost, name = context.user_data['buy_data']
    uid = update.effective_user.id
    username = update.effective_user.username
    u_tag = f"@{username}" if username else "No Username"
    
    # Callback data te username pass kora possible na (limit thake), tai pore fetch korbo
    kb = [[InlineKeyboardButton("✅ Grant", callback_data=f"g_{uid}_{pid}_{cost}"), InlineKeyboardButton("❌ Reject", callback_data=f"f_{uid}")]]
    
    # --- FIX FOR ISSUE 4 ---
    msg = f"⚠️ **Access Req**\n👤 User: {u_tag}\n🆔 ID: `{uid}`\n📦 Item: {name}\n📧 Email: `{email}`"
    
    await context.bot.send_message(ADMIN_ID, msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    await update.message.reply_text(TEXTS[get_user(uid)[2]]['email_sent'])
    return MAIN_STATE
  

async def input_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT * FROM coupons WHERE code=%s", (code,))
    res = c.fetchone()
    
    if res and res[3] < res[2]:
        context.user_data['disc'] = res[1]
        c.execute("UPDATE coupons SET used_count=used_count+1 WHERE code=%s", (code,))
        conn.commit()
        # Note: Ekhane user lang fetch kora jete pare dynamic text er jonne
        await update.message.reply_text("✅ Coupon Applied! Discount added.")
    else: 
        await update.message.reply_text("❌ Invalid or Expired Coupon!")
    
    db_pool.putconn(conn) # <-- Fixed
    return MAIN_STATE
    

# --- UNIVERSAL ADMIN PANEL ---
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        # সারি ১: স্টক এবং সেলস রিপোর্ট
        [InlineKeyboardButton("📦 Stock Report", callback_data='adm_stock'), InlineKeyboardButton("📈 Sales Report", callback_data='adm_sales')],
        # সারি ২: প্রোডাক্ট অ্যাড এবং ডিলিট
        [InlineKeyboardButton("➕ Add Product", callback_data='adm_add'), InlineKeyboardButton("❌ Delete Product", callback_data='adm_del')],
        # সারি ৩: ইউজার ব্যালেন্স এবং রিসেলার লিস্ট (নতুন)
        [InlineKeyboardButton("👥 Users & Balance", callback_data='adm_users'), InlineKeyboardButton("🔐 Reseller List", callback_data='adm_res_list')],
        # সারি ৪: রিসেলার তৈরি এবং কুপন
        [InlineKeyboardButton("➕ Add Reseller", callback_data='adm_add_res'), InlineKeyboardButton("🎟 Add Coupon", callback_data='adm_coupon')],
        # সারি ৫: ব্রডকাস্ট এবং ব্যাক
        [InlineKeyboardButton("📢 Broadcast", callback_data='adm_cast')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='menu_main')]
    ]
    
    # মেসেজ এডিট অথবা সেন্ড (সেফটি সহ - যাতে ক্র্যাশ না করে)
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text("👑 **Admin Panel**\nঅপশন সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        else:
            await update.message.reply_text("👑 **Admin Panel**\nঅপশন সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    except:
        # যদি এডিট করতে না পারে, নতুন করে পাঠাবে
        await update.effective_message.reply_text("👑 **Admin Panel**\nঅপশন সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        
    return MAIN_STATE
    

async def universal_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer() # বাটন লোডিং বন্ধ করতে
    d = q.data
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # --- ১. ব্যাক বাটন ---
        if d == 'adm_back' or d == 'adm_panel':
            await admin_panel(update, context)
            return MAIN_STATE

        # --- ২. প্রোডাক্ট অ্যাড ---
        elif d == 'adm_add':
            await q.message.reply_text("📝 **Add Product (Bulk)**\nFormat: `Type|Name|Desc|CustP|ResP|Content`\n\nTypes: `file`, `account`, `access`", parse_mode='Markdown')
            return INPUT_ADMIN_PROD
            
        # --- ৩. রিসেলার তৈরি (Add Reseller) ---
        elif d == 'adm_add_res':
            # অটোমেটিক আইডি পাসওয়ার্ড জেনারেট
            res_id = ''.join(random.choices(string.digits, k=10))
            pas = ''.join(random.choices(string.digits, k=8))
            
            c.execute("INSERT INTO resellers (res_id, password) VALUES (%s, %s)", (res_id, pas))
            conn.commit()
            
            # ব্যাক বাটন সহ রেজাল্ট দেখানো
            kb_back = [[InlineKeyboardButton("🔙 Back to Panel", callback_data='adm_panel')]]
            await q.message.edit_text(f"✅ **New Reseller Created**\n\n🆔 ID: `{res_id}`\n🔑 Pass: `{pas}`", 
                                      reply_markup=InlineKeyboardMarkup(kb_back), 
                                      parse_mode='Markdown')
            
        # --- ৪. রিসেলার লিস্ট দেখা (নতুন) ---
        elif d == 'adm_res_list':
            c.execute("SELECT res_id, password FROM resellers")
            resellers = c.fetchall()
            
            if not resellers:
                msg = "❌ No Resellers found."
            else:
                msg = "🔐 **All Resellers List:**\n\n"
                for r in resellers:
                    msg += f"👤 ID: `{r[0]}` | 🔑 Pass: `{r[1]}`\n"
            
            kb_back = [[InlineKeyboardButton("🔙 Back to Panel", callback_data='adm_panel')]]
            await q.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb_back), parse_mode='Markdown')

        # --- ৫. ইউজার ব্যালেন্স দেখা (নতুন) ---
        elif d == 'adm_users':
            # টপ ৫০ জন ইউজার যাদের ব্যালেন্স আছে
            c.execute("SELECT user_id, first_name, balance FROM users WHERE balance > 0 ORDER BY balance DESC LIMIT 50")
            users = c.fetchall()
            
            if not users:
                msg = "👥 **User Balances:**\nNo users with balance found."
            else:
                msg = "👥 **User Balances (Top 50):**\n\n"
                for u in users:
                    msg += f"🆔 `{u[0]}` | 👤 {u[1]} | 💰 {u[2]} Tk\n"
            
            msg += "\n⚠️ **To Remove Balance:**\nUse: `/cut user_id amount`\nExample: `/cut 123456 100`"
            
            kb_back = [[InlineKeyboardButton("🔙 Back to Panel", callback_data='adm_panel')]]
            await q.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb_back), parse_mode='Markdown')

        # --- ৬. প্রোডাক্ট ডিলিট ---
        elif d == 'adm_del':
            c.execute("SELECT DISTINCT name FROM products")
            names = c.fetchall()
            if not names:
                await q.message.edit_text("❌ No products to delete.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='adm_panel')]]))
            else:
                # ডিলিট বাটন লিস্ট তৈরি
                kb = [[InlineKeyboardButton(f"❌ {n[0]}", callback_data=f"del_{n[0]}")] for n in names]
                kb.append([InlineKeyboardButton("🔙 Back to Panel", callback_data='adm_panel')])
                await q.message.edit_text("👇 Select Product to DELETE:", reply_markup=InlineKeyboardMarkup(kb))
            
        # --- ৭. স্টক রিপোর্ট ---
        elif d == 'adm_stock':
            c.execute("SELECT name, COUNT(*) FROM products WHERE status='unsold' GROUP BY name")
            rows = c.fetchall()
            msg = "📦 **Current Stock:**\n\n" + "\n".join([f"▫️ {r[0]}: {r[1]} pcs" for r in rows])
            if not rows: msg = "📦 **Stock is Empty!**"
            
            await q.message.edit_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='adm_panel')]]), parse_mode='Markdown')
            
        # --- ৮. সেলস রিপোর্ট ---
        elif d == 'adm_sales':
            c.execute("SELECT product_name, price, date FROM sales ORDER BY id DESC LIMIT 15")
            rows = c.fetchall()
            if not rows: 
                msg = "📉 **No Sales Yet**"
            else:
                msg = "📈 **Recent Sales (Last 15):**\n\n"
                for r in rows:
                    date_short = str(r[2]).split('.')[0]
                    msg += f"▫️ {r[0]} - {r[1]} Tk \n   `{date_short}`\n"
            
            await q.message.edit_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='adm_panel')]]), parse_mode='Markdown')
            
        # --- ৯. ব্রডকাস্ট ---
        elif d == 'adm_cast':
            await q.message.reply_text("📢 Enter Message to Broadcast:")
            return INPUT_BROADCAST
            
        # --- ১০. কুপন ---
        elif d == 'adm_coupon' or d == 'adm_coup':
            await q.message.reply_text("🎟 Enter Coupon Details:\nFormat: `CODE | Percent | Limit`", parse_mode='Markdown')
            return INPUT_ADMIN_COUPON
            
    except Exception as e:
        print(f"Error in Admin Handler: {e}") 
        await q.message.reply_text(f"⚠️ Error: {e}")
        
    finally:
        db_pool.putconn(conn) # কানেকশন সেফলি ফেরত যাবে
        
    return MAIN_STATE
    
            
                

# --- ADMIN ACTIONS ---
async def admin_save_prod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.split('\n')
    
    conn = get_db_connection() # Added Connection
    c = conn.cursor()
    
    count = 0
    for line in lines:
        try:
            p = [x.strip() for x in line.split('|')]
            # FIXED: ? -> %s
            c.execute("INSERT INTO products (type,name,description,price_cust,price_res,content) VALUES (%s,%s,%s,%s,%s,%s)", (p[0],p[1],p[2],int(p[3]),int(p[4]),p[5]))
            count+=1
        except: pass
    conn.commit()
    db_pool.putconn(conn) # <-- Fixed (Connection returned to pool)
    
    await update.message.reply_text(f"✅ Added {count} items.")
    return await admin_start(update, context)
    
async def admin_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.callback_query.data.split('_')[1]
    
    conn = get_db_connection() # Added Connection
    c = conn.cursor()
    
    # FIXED: ? -> %s
    c.execute("DELETE FROM products WHERE name=%s", (name,))
    conn.commit()
    db_pool.putconn(conn) # <-- Fixed
    
    await update.callback_query.message.edit_text(f"🗑 Deleted: {name}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='adm_back')]]))
    return MAIN_STATE
                               

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection() # Added Connection
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM users")
    count = 0
    for u in c.fetchall():
        try:
            await context.bot.send_message(u[0], update.message.text)
            count+=1
        except: pass
    
    db_pool.putconn(conn) # <-- Fixed
    await update.message.reply_text(f"✅ Sent to {count}.")
    return await admin_start(update, context)

# কমান্ড: /cut user_id amount
async def cut_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # সিকিউরিটি চেক: শুধু এডমিন এই কমান্ড দিতে পারবে
    if user.id != ADMIN_ID: 
        return 
    
    try:
        # কমান্ড থেকে ডাটা নেওয়া (যেমন: /cut 123456 100)
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("⚠️ Format error! Use: `/cut user_id amount`")
            return

        target_id = int(args[0])
        amount = int(args[1])
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # ১. ব্যালেন্স চেক করা (যে মাইনাস হবে কিনা)
        c.execute("SELECT balance FROM users WHERE user_id=%s", (target_id,))
        res = c.fetchone()
        
        if not res:
            await update.message.reply_text("❌ User not found!")
            db_pool.putconn(conn)
            return

        current_balance = res[0]
        new_balance = current_balance - amount
        
        # ২. ব্যালেন্স আপডেট করা
        c.execute("UPDATE users SET balance = %s WHERE user_id = %s", (new_balance, target_id))
        conn.commit()
        db_pool.putconn(conn)
        
        await update.message.reply_text(f"✅ Cut **{amount} Tk** from User `{target_id}`.\n💰 New Balance: {new_balance} Tk", parse_mode='Markdown')
        
        # ৩. ইউজারকে নোটিশ দেওয়া (অপশনাল)
        try:
            await context.bot.send_message(target_id, f"⚠️ Admin removed {amount} Tk from your balance.\n💰 Current Balance: {new_balance} Tk")
        except:
            pass
        
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")
    

async def admin_save_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        p = [x.strip() for x in update.message.text.split('|')]
        
        conn = get_db_connection() # Added Connection
        c = conn.cursor()
        
        # FIXED: ? -> %s
        c.execute("INSERT INTO coupons VALUES (%s,%s,%s,0)", (p[0], int(p[1]), int(p[2])))
        conn.commit()
        db_pool.putconn(conn) # <-- Fixed
        
        await update.message.reply_text("✅ Coupon Created!")
    except: await update.message.reply_text("Error.")
    return await admin_start(update, context)
        

async def admin_deposit_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data
    conn = get_db_connection()
    c = conn.cursor()
    
    if d.startswith('ok'):
        _, u_str, a_str = d.split('_')
        u, a = int(u_str), int(a_str)
        c.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (a, u))
        conn.commit()
        await context.bot.send_message(u, f"🎉 Balance Added: {a} Tk")
        await update.callback_query.edit_message_text(f"✅ Approved {a} Tk")
        
    elif d.startswith('g'):
        _, u_str, pid_str, cost_str = d.split('_')
        u, pid, cost = int(u_str), int(pid_str), int(cost_str)
        
        # 1. Balance kete neya
        c.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (cost, u))
        
        # 2. Product name ber kora (Sales table er jonno)
        c.execute("SELECT name FROM products WHERE id=%s", (pid,))
        p_res = c.fetchone()
        p_name = p_res[0] if p_res else "Unknown Item"
        
        # 3. --- FIX FOR ISSUE 3 (Sales Table Update) ---
        c.execute("INSERT INTO sales (user_id, product_name, price) VALUES (%s,%s,%s)", (u, p_name, cost))
        conn.commit()
        
        # 4. User info ber kora (Username er jonno)
        try:
            chat_info = await context.bot.get_chat(u)
            username = f"@{chat_info.username}" if chat_info.username else "No Username"
        except:
            username = "Unknown"

        # 5. --- FIX FOR ISSUE 1 (Admin Notification) ---
        await context.bot.send_message(ADMIN_ID, f"📢 **Sold (Access Granted):** {p_name}\n👤 Sold to: {username} (`{u}`)")
        
        await context.bot.send_message(u, f"✅ **Approved!**\n📦 Item: {p_name}\nআপনার ইমেইল অথবা ইনবক্স চেক করুন।")
        await update.callback_query.edit_message_text(f"✅ Granted: {p_name} to {username}")
        
        else: 
        # রিজেক্ট লজিক (Reject Logic)
        try:
            # বাটন থেকে ইউজার আইডি বের করা (Format: no_USERID)
            target_user_id = int(d.split('_')[1])
            
            # ইউজারকে মেসেজ পাঠানো
            await context.bot.send_message(target_user_id, "❌ আপনার ডিপোজিট রিকোয়েস্টটি বাতিল (Reject) করা হয়েছে।")
        except:
            pass
            
        await update.callback_query.edit_message_text("❌ Rejected.")
    
    db_pool.putconn(conn) # এটা যেমন ছিল তেমনই থাকবে
        
      
        
# --- MAIN ---
def main():
    init_db()
    keep_alive()
    
    # কানেকশন টাইমআউট বাড়ানো হলো (৬০ সেকেন্ড)
    req = HTTPXRequest(connect_timeout=60, read_timeout=60)
    
    # অ্যাপ বিল্ডার আপডেট করা হলো
    app = Application.builder().token(TOKEN).request(req).build()
    
    # --- HANDLERS ---
    menu_h = CallbackQueryHandler(universal_menu_handler, pattern='^menu_')
    admin_h = CallbackQueryHandler(universal_admin_handler, pattern='^adm_')
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_LANG: [CallbackQueryHandler(lang_choice, pattern='^lang_')],
            SELECT_ROLE: [CallbackQueryHandler(ask_role_screen, pattern='^back_'), CallbackQueryHandler(role_handler, pattern='^role_')],
            RESELLER_INPUT: [MessageHandler(filters.TEXT, reseller_input)],
            MAIN_STATE: [
                menu_h, 
                admin_h, 
                CallbackQueryHandler(buy_handler, pattern='^buy_'), 
                CallbackQueryHandler(admin_delete_confirm, pattern='^del_')
            ],
            INPUT_MONEY: [MessageHandler(filters.TEXT, input_money), menu_h, admin_h],
            INPUT_TRX: [MessageHandler(filters.TEXT, input_trx), menu_h, admin_h],
            INPUT_EMAIL: [MessageHandler(filters.TEXT, input_email), menu_h, admin_h],
            INPUT_COUPON: [MessageHandler(filters.TEXT, input_coupon), menu_h, admin_h],
            INPUT_ADMIN_PROD: [MessageHandler(filters.TEXT, admin_save_prod), admin_h, menu_h],
            INPUT_ADMIN_COUPON: [MessageHandler(filters.TEXT, admin_save_coupon), admin_h, menu_h],
            INPUT_BROADCAST: [MessageHandler(filters.TEXT, admin_broadcast), admin_h, menu_h]
        },
        fallbacks=[CommandHandler('start', start), CommandHandler('admin', admin_start)]
    )
    # ব্যালেন্স কাটার কমান্ড হ্যান্ডলার
    app.add_handler(CommandHandler("cut", cut_balance))
    
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_deposit_access, pattern='^(ok|no|g|f)_'))
    
    print("Bot Running... (Press Ctrl+C to stop)")
    app.run_polling()

if __name__ == '__main__':
    main()
    
