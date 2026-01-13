import logging
import psycopg2
from psycopg2 import pool
import threading
import re
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
(
    SELECT_LANG, 
    SELECT_ROLE, 
    INPUT_RES_LOGIN,  # নতুন (RESELLER_INPUT এর বদলে)
    INPUT_RES_PASS,   # নতুন
    MAIN_STATE, 
    INPUT_MONEY, 
    INPUT_TRX, 
    INPUT_EMAIL, 
    INPUT_COUPON, 
    INPUT_ADMIN_PROD, 
    INPUT_ADMIN_COUPON, 
    INPUT_BROADCAST
) = range(12) # আগে 11 ছিল, এখন 12 হবে


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
        'ask_trx': "✅ **Request: {} Tk**\n━━━━━━━━━━━━\nPlease Send Money to:\n📞 `{01611026722}` (bKash Personal)\n\n⚠️ After sending, please type the **Transaction ID (TrxID)** below:",
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
        'ask_trx': "✅ **অনুরোধ: {} টাকা**\n━━━━━━━━━━━━\nআপনার {} টাকা এই নাম্বারে সেন্ড মানি করুন:\n📞 `{01611026722}` (bKash)\n\n⚠️ টাকা পাঠানোর পর নিচের বক্সে **Transaction ID (TrxID)** লিখে পাঠান।",
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
    uid = user.id
    first_name = user.first_name
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # ১. চেক করি ইউজার আগে থেকেই ডাটাবেসে আছে কিনা
        c.execute("SELECT * FROM users WHERE user_id=%s", (uid,))
        db_user = c.fetchone()
        
        if db_user:
            # === পুরাতন ইউজার (Old User) ===
            # যদি ভাষা সেট করা থাকে (BN বা EN), সরাসরি মেইন মেনু দেখাবো
            if db_user[2] in ['BN', 'EN']:
                await update.message.reply_text(f"👋 Welcome back, **{first_name}**!", parse_mode='Markdown')
                await show_main_menu(update, context)
                db_pool.putconn(conn)
                return MAIN_STATE
        else:
            # === নতুন ইউজার (New User) ===
            # যেহেতু ডাটাবেসে নেই, তাই ইনি নতুন। এখনই রেফারেল চেক করবো।
            
            # ---> রেফারেল বোনাস লজিক <---
            args = context.args
            if args and args[0].startswith('ref_'):
                try:
                    referrer_id = int(args[0].split('_')[1])
                    
                    # নিজের লিংকে নিজে ঢুকলে বোনাস পাবে না
                    if referrer_id != uid:
                        # রেফারারের ব্যালেন্স ১ টাকা বাড়ানো
                        c.execute("UPDATE users SET balance = balance + 1 WHERE user_id=%s", (referrer_id,))
                        conn.commit()
                        
                        # রেফারারকে মেসেজ পাঠানো
                        try:
                            await context.bot.send_message(
                                referrer_id, 
                                f"🎉 **Referral Bonus!**\n\nনতুন ইউজার **{first_name}** আপনার লিংকে জয়েন করেছে।\n💰 আপনার ব্যালেন্সে **1 Tk** যুক্ত হয়েছে!"
                            )
                        except:
                            pass
                except Exception as e:
                    print(f"Refer Error: {e}")

            # ---> নতুন ইউজার তৈরি করা <---
            # create_user ফাংশনের কাজটা এখানেই করে দিচ্ছি যাতে কনফিউশন না থাকে
            # ডিফল্ট ভাষা 'BN' ও রোল 'customer' দিয়ে সেভ করলাম
            c.execute("INSERT INTO users (user_id, first_name, role, balance, lang) VALUES (%s, %s, 'customer', 0, 'BN')", (uid, first_name))
            conn.commit()

    except Exception as e:
        print(f"Start Error: {e}")
    
    finally:
        db_pool.putconn(conn)

    # ৪. ভাষা নির্বাচন (নতুন ইউজার বা যাদের ভাষা সেট নেই তাদের জন্য)
    kb = [[InlineKeyboardButton("English 🇺🇸", callback_data='lang_EN'), InlineKeyboardButton("বাংলা 🇧🇩", callback_data='lang_BN')]]
    
    # সুন্দর ওয়েলকাম মেসেজ
    await update.message.reply_text(
        f"👋 **Welcome to Our Shop!**\n\nHello {first_name}, please select your language to continue:\nআপনার ভাষা নির্বাচন করুন:", 
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='Markdown'
    )
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
async def ask_role_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id)
    lang = db_user[2] if db_user else 'BN'
    
    # ভাষার ওপর ভিত্তি করে টেক্সট
    if lang == 'EN':
        txt = "👤 **Select Identity:**\n\nAre you a Customer or a Reseller?"
        btn_cust = "👤 Customer"
        btn_res = "🔐 Reseller"
    else:
        txt = "👤 **পরিচয় নির্বাচন করুন:**\n\nআপনি কি কাস্টমার নাকি রিসেলার?"
        btn_cust = "👤 কাস্টমার"
        btn_res = "🔐 রিসেলার"

    kb = [
        [InlineKeyboardButton(btn_cust, callback_data='role_customer')],
        [InlineKeyboardButton(btn_res, callback_data='role_reseller')]
    ]
    
    # সেফটি চেক: মেসেজ এডিট হবে নাকি নতুন পাঠাবে
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        except:
             await update.callback_query.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        
    return SELECT_ROLE
    

async def role_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    user_id = q.from_user.id
    conn = get_db_connection()
    c = conn.cursor()

    if d == 'role_customer':
        # ১. কাস্টমার হলে সোজা মেইন মেনুতে
        c.execute("UPDATE users SET role='customer' WHERE user_id=%s", (user_id,))
        conn.commit()
        db_pool.putconn(conn)
        
        await q.edit_message_text("✅ You are now a **Customer**.")
        await show_main_menu(update, context)
        return MAIN_STATE

    elif d == 'role_reseller':
        # ২. রিসেলার হলে লগইন করতে বলবে (আলাদা স্টেটে পাঠাবে)
        db_pool.putconn(conn)
        await q.message.reply_text("🔐 **Reseller Login**\n\nআপনার রিসেলার **ID** দিন:\n(শুধু আইডি লিখুন)")
        return INPUT_RES_LOGIN
        

# স্টেপ ১: আইডি নিবে
async def reseller_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # আইডি সেভ করে রাখলাম পরের ধাপের জন্য
    context.user_data['res_id_attempt'] = text
    
    await update.message.reply_text(f"🆔 ID: `{text}`\n🔑 এবার আপনার **Password** দিন:")
    return INPUT_RES_PASS

# স্টেপ ২: পাসওয়ার্ড নিবে এবং চেক করবে
async def reseller_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    res_id = context.user_data.get('res_id_attempt') # আগের ধাপের আইডি
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # ডাটাবেসে আইডি ও পাসওয়ার্ড মিলছে কিনা চেক
    c.execute("SELECT * FROM resellers WHERE res_id=%s AND password=%s", (res_id, password))
    res = c.fetchone()
    
    if res:
        # লগইন সফল! রোল আপডেট করে মেনু দেখাবে
        c.execute("UPDATE users SET role='reseller' WHERE user_id=%s", (user_id,))
        conn.commit()
        db_pool.putconn(conn)
        
        await update.message.reply_text("✅ **Login Successful!** Welcome Boss.")
        await show_main_menu(update, context)
        return MAIN_STATE
    else:
        # ভুল হলে
        db_pool.putconn(conn)
        await update.message.reply_text("❌ ভুল আইডি বা পাসওয়ার্ড!\nআবার চেষ্টা করতে /start দিন।")
        return ConversationHandler.END
    

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
    
    # বাটন থেকে নাম বের করা (buy_Netflix -> Netflix)
    try:
        name = q.data.split('_', 1)[1]
    except:
        name = q.data.split('_')[1]

    uid = q.from_user.id
    username = q.from_user.username
    u_tag = f"@{username}" if username else "No Username"
    
    user = get_user(uid)
    lang = user[2]
    t = TEXTS[lang]
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # প্রোডাক্ট চেক
    c.execute("SELECT id, type, price_cust, price_res, content FROM products WHERE name=%s AND (status='unsold' OR type='file' OR type='access') LIMIT 1", (name,))
    item = c.fetchone()
    
    if not item: 
        db_pool.putconn(conn)
        return await q.answer("❌ Stock Ended / Out of Stock!", show_alert=True)
    
    pid, ptype, pc, pr, content = item
    
    # প্রাইস ক্যালকুলেশন
    base_price = pr if user[3] == 'reseller' else pc
    discount = context.user_data.get('disc', 0)
    final_price = int(base_price - (base_price * discount / 100))
    
    # ব্যালেন্স চেক
    if user[4] < final_price: 
        db_pool.putconn(conn)
        return await q.answer(t['insufficient'].format(final_price - user[4]), show_alert=True)
        
    # --- FIX: Access Type Logic ---
    if ptype == 'access':
        # এক্সেস প্রোডাক্টের ক্ষেত্রে ব্যালেন্স এখন কাটা হবে না (এডমিন অ্যাপ্রুভ করলে কাটা হবে)
        # ডাটা সেভ করা হচ্ছে যাতে input_email এ ব্যবহার করা যায়
        context.user_data['buying_product'] = name       # <--- এই লাইনটি আগে মিসিং বা ভিন্ন ছিল
        context.user_data['buying_price'] = final_price  # <--- এই লাইনটি আগে মিসিং বা ভিন্ন ছিল
        context.user_data['buying_pid'] = pid            # <--- প্রোডাক্ট আইডিও সেভ রাখলাম (ভবিষ্যতের জন্য)
        
        await q.message.reply_text(t['ask_email'])
        db_pool.putconn(conn)
        return INPUT_EMAIL
    
    # --- Instant Purchase (Account / File) ---
    if ptype == 'account':
        c.execute("UPDATE products SET status='sold' WHERE id=%s", (pid,))
        
    # ১. ব্যালেন্স কাটা
    c.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s", (final_price, uid))
    
    # ২. সেলস রেকর্ড করা
    c.execute("INSERT INTO sales (user_id, product_name, price) VALUES (%s,%s,%s)", (uid, name, final_price))
    conn.commit()
    db_pool.putconn(conn)
    
    # ডিসকাউন্ট রিসেট
    if 'disc' in context.user_data: del context.user_data['disc']
    
    # ৩. এডমিন নোটিফিকেশন
    try:
        await context.bot.send_message(ADMIN_ID, f"📢 **Sold (Instant):** {name}\n👤 Buyer: {u_tag} (`{uid}`)\n💰 Price: {final_price} Tk")
    except:
        pass
    
    # ৪. ইউজারকে ডেলিভারি দেওয়া
    await q.message.reply_text(t['bought'].format(name, content), parse_mode='Markdown') 
    await show_main_menu(update, context)
    return MAIN_STATE
        
  
    
# --- INPUTS ---
async def input_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ইনপুট থেকে স্পেস সরানো হচ্ছে
    text = update.message.text.strip()
    user = update.effective_user
    
    # ভাষা চেক করা (যাতে মেসেজ সেই ভাষায় যায়)
    db_user = get_user(user.id)
    lang = db_user[2] if db_user else 'BN'
    
    # যদি ইউজার চ্যাট থেকে বের হতে চায়
    if text.lower() in ['cancel', 'back', '/cancel']:
        await update.message.reply_text("❌ Cancelled.")
        await show_main_menu(update, context)
        return MAIN_STATE

    # নাম্বার চেকিং
    if not text.isdigit():
        await update.message.reply_text("⚠️ **Invalid Amount!**\n\nPlease enter only numbers (e.g. 100, 500).\nদয়া করে শুধুমাত্র সংখ্যা লিখুন।")
        return INPUT_MONEY
        
    amount = int(text)
    
    if amount < 10: 
        await update.message.reply_text("⚠️ Minimum deposit is 10 Tk.")
        return INPUT_MONEY

    # ডাটা সেভ রাখা
    context.user_data['dep_amount'] = amount
    
    # --- পেমেন্ট নাম্বার ও মেসেজ ---
    payment_number = "01611026722"  # <--- এখানে আপনার নাম্বার বসান (bKash/Nagad)
    
    if lang == 'EN':
        msg = (
            f"✅ **Request:** {amount} Tk\n"
            f"━━━━━━━━━━━━\n"
            f"Please Send Money to:\n"
            f"📞 `{payment_number}` (bKash)\n\n"
            f"⚠️ After sending, please enter the **Transaction ID (TrxID)** below:"
        )
    else:
        msg = (
            f"✅ **অনুরোধ:** {amount} টাকা\n"
            f"━━━━━━━━━━━━\n"
            f"আপনার {amount} টাকা এই নাম্বারে সেন্ড মানি করুন:\n"
            f"📞 `{payment_number}` (bKash)\n\n"
            f"⚠️ টাকা পাঠানোর পর নিচের বক্সে **Transaction ID (TrxID)** লিখে পাঠান:"
        )
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    return INPUT_TRX
    
    

async def input_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx = update.message.text.strip()
    user = update.effective_user
    uid = user.id
    
    # এমাউন্ট নেওয়া (input_money ফাংশনে আমরা 'dep_amount' সেভ করেছিলাম)
    # যদি আগের কোডে 'amt' থাকে, তাই সেফটির জন্য দুটোই চেক করছি
    amt = context.user_data.get('dep_amount', context.user_data.get('amt', 0))
    
    # --- ফিক্স: বাটন ফরম্যাট ---
    # Approve হতে হবে: ok_dep_UID_Amount
    # Reject হতে হবে: no_dep_UID
    kb = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"ok_dep_{uid}_{amt}"), 
         InlineKeyboardButton("❌ Reject", callback_data=f"no_dep_{uid}")]
    ]
    
    # এডমিনকে নোটিফিকেশন পাঠানো
    await context.bot.send_message(
        ADMIN_ID, 
        f"🔔 **New Deposit Request!**\n\n👤 User: {user.first_name} (`{uid}`)\n💰 Amount: {amt} Tk\n📝 TrxID: `{trx}`", 
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode='Markdown'
    )
    
    # ইউজারকে কনফার্মেশন মেসেজ
    try:
        # আপনার আগের লজিক অনুযায়ী ভাষা চেক
        db_user = get_user(uid)
        lang = db_user[2] if db_user else 'BN'
        await update.message.reply_text(TEXTS[lang]['req_sent'])
    except:
        await update.message.reply_text("✅ **Request Sent!**\nঅ্যাডমিন চেক করে ব্যালেন্স অ্যাড করে দিবেন।")
    
    # মেইন মেনুতে ফেরত পাঠানো
    await show_main_menu(update, context)
    return MAIN_STATE
    

async def input_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # এই try-except ব্লক এরর ধরতে সাহায্য করবে
    try:
        user = update.effective_user
        email = update.message.text.strip()
        
        # --- লজিক ১: ইউজার যদি বের হতে চায় ---
        if email.lower() in ['/cancel', 'cancel', 'back']:
            await update.message.reply_text("❌ Process Cancelled.")
            await show_main_menu(update, context)
            return MAIN_STATE

        # --- লজিক ২: ইমেইল ভ্যালিডেশন ---
        # import re না থাকলে এখানে ক্র্যাশ করবে, তাই উপরে import re অবশ্যই দিবেন
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            kb_back = [[InlineKeyboardButton("🔙 Cancel / Back", callback_data='menu_main')]]
            await update.message.reply_text(
                "⚠️ **Invalid Email!**\n\nদয়া করে একটি সঠিক ইমেইল এড্রেস দিন (যেমন: `abc@gmail.com`)।", 
                reply_markup=InlineKeyboardMarkup(kb_back),
                parse_mode='Markdown'
            )
            return INPUT_EMAIL
            
        # --- লজিক ৩: সব ঠিক থাকলে অর্ডার প্রসেস ---
        product_name = context.user_data.get('buying_product')
        price = context.user_data.get('buying_price')
        pid = context.user_data.get('buying_pid') # প্রোডাক্ট আইডিও লাগবে
        
        # --- ফিক্স: বাটন ফরম্যাট আপডেট ---
        # Approve: g_UserID_PID_Price (যাতে এডমিন প্যানেল নাম খুঁজে পায়)
        # Reject: no_acc_UserID
        kb = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"g_{user.id}_{pid}_{price}"), 
             InlineKeyboardButton("❌ Reject", callback_data=f"no_acc_{user.id}")]
        ]
        
        await context.bot.send_message(
            ADMIN_ID, 
            f"🔔 **New Access Order!**\n\n👤 User: {user.first_name} (`{user.id}`)\n📦 Item: {product_name}\n📧 Email: `{email}`\n💰 Paid: {price} Tk", 
            reply_markup=InlineKeyboardMarkup(kb), 
            parse_mode='Markdown'
        )
        
        await update.message.reply_text("✅ **Request Sent!**\nআপনার ইমেইল এড্রেসটি এডমিনের কাছে পাঠানো হয়েছে। শীঘ্রই অ্যাপ্রুভ করা হবে।")
        await show_main_menu(update, context)
        return MAIN_STATE

    except Exception as e:
        print(f"Email Error: {e}") 
        await update.message.reply_text(f"⚠️ Error: {e}")
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
            await admin_start(update, context)
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
    q = update.callback_query
    await q.answer()
    d = q.data
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # --- ১. প্রোডাক্ট অ্যাপ্রুভ (Access Grant) ---
        # বাটন ফরম্যাট: g_UserID_PID_Price (যেমন: g_12345_5_100)
        if d.startswith('g_'):
            parts = d.split('_')
            # parts[0]=g, parts[1]=uid, parts[2]=pid, parts[3]=price
            u = int(parts[1])
            pid = int(parts[2])
            cost = int(parts[3])
            
            # ১. ব্যালেন্স কাটা
            c.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (cost, u))
            
            # ২. প্রোডাক্ট নাম ডাটাবেস থেকে বের করা (Item: None ফিক্স)
            c.execute("SELECT name FROM products WHERE id=%s", (pid,))
            res = c.fetchone()
            p_name = res[0] if res else "Unknown Item"
            
            # ৩. সেলস টেবিলে রেকর্ড করা
            c.execute("INSERT INTO sales (user_id, product_name, price) VALUES (%s,%s,%s)", (u, p_name, cost))
            conn.commit()
            
            # ৪. ইউজারনেম বের করা (এডমিন লগের জন্য)
            try:
                chat = await context.bot.get_chat(u)
                uname = f"@{chat.username}" if chat.username else "No Username"
            except:
                uname = "Unknown"
            
            # ৫. মেসেজ পাঠানো
            # এডমিনকে লগ
            await context.bot.send_message(ADMIN_ID, f"📢 **Sold (Access Granted):** {p_name}\n👤 To: {uname} (`{u}`)\n💰 Price: {cost} Tk")
            
            # ইউজারকে ডেলিভারি মেসেজ
            await context.bot.send_message(u, f"✅ **Order Approved!**\n📦 Item: **{p_name}**\n\nআপনার ইমেইল বা ইনবক্স চেক করুন, শীঘ্রই এক্সেস দেওয়া হবে।")
            
            # এডমিন প্যানেলের মেসেজ এডিট
            await q.edit_message_text(f"✅ Granted: {p_name} to {uname}")

        # --- ২. ডিপোজিট অ্যাপ্রুভ (Balance Add) ---
        # বাটন ফরম্যাট: ok_dep_UserID_Amount
        elif d.startswith('ok_dep_'):
            parts = d.split('_')
            u = int(parts[2])
            a = int(parts[3])
            
            c.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (a, u))
            conn.commit()
            
            await context.bot.send_message(u, f"🎉 **Deposit Successful!**\n💰 Added: {a} Tk")
            await q.edit_message_text(f"✅ Approved {a} Tk for User `{u}`")

        # --- ৩. প্রোডাক্ট রিজেক্ট (Product Reject) ---
        # বাটন ফরম্যাট: no_acc_UserID
        elif d.startswith('no_acc_'):
            u = int(d.split('_')[2])
            await context.bot.send_message(u, "❌ **Order Rejected.**\nদুঃখিত, আপনার প্রোডাক্ট অর্ডারটি বাতিল করা হয়েছে।")
            await q.edit_message_text(f"❌ Product Request Rejected for `{u}`")

        # --- ৪. ডিপোজিট রিজেক্ট (Deposit Reject) ---
        # বাটন ফরম্যাট: no_dep_UserID
        elif d.startswith('no_dep_'):
            u = int(d.split('_')[2])
            await context.bot.send_message(u, "❌ **Deposit Rejected.**\nআপনার পেমেন্ট রিকোয়েস্টটি বাতিল করা হয়েছে।")
            await q.edit_message_text(f"❌ Deposit Rejected for `{u}`")

    except Exception as e:
        print(f"Admin Access Error: {e}")
        # ক্র্যাশ না করে এরর দেখাবে (সেফটি)
        try:
            await q.message.reply_text(f"⚠️ Error Processing: {str(e)}")
        except:
            pass
        
    finally:
        db_pool.putconn(conn)
                            
    
      
        
# --- MAIN ---
def main():
    init_db()
    keep_alive()
    
    # কানেকশন টাইমআউট বাড়ানো হলো (৬০ সেকেন্ড)
    req = HTTPXRequest(connect_timeout=60, read_timeout=60)
    
    # অ্যাপ বিল্ডার
    app = Application.builder().token(TOKEN).request(req).build()
    
    # --- HANDLERS (মেনু ও এডমিন প্যাটার্ন) ---
    # 'menu_' দিয়ে শুরু হওয়া সব বাটন (menu_reset সহ) এখানে হ্যান্ডেল হবে
    menu_h = CallbackQueryHandler(universal_menu_handler, pattern='^menu_')
    
    # 'adm_' দিয়ে শুরু হওয়া সব বাটন (adm_users, adm_res_list সহ) এখানে হ্যান্ডেল হবে
    admin_h = CallbackQueryHandler(universal_admin_handler, pattern='^adm_')
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            # ১. ভাষা সিলেকশন
            SELECT_LANG: [CallbackQueryHandler(lang_choice, pattern='^lang_')],
            
            # ২. রোল সিলেকশন (Customer / Reseller)
            SELECT_ROLE: [CallbackQueryHandler(role_choice, pattern='^role_')],
            
            # ৩. রিসেলার লগইন (২ ধাপ: আইডি -> পাসওয়ার্ড) - আপডেটেড এবং নিরাপদ
            INPUT_RES_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, reseller_login)],
            INPUT_RES_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reseller_pass)],
            
            # ৪. মেইন মেনু স্টেট (সব বাটন কাজ করবে)
            MAIN_STATE: [
                menu_h, 
                admin_h, 
                CallbackQueryHandler(buy_handler, pattern='^buy_'), 
                CallbackQueryHandler(admin_delete_confirm, pattern='^del_')
            ],
            
            # ৫. অন্যান্য ইনপুট স্টেটস (টাকা, ট্রানজেকশন, কুপন ইত্যাদি)
            INPUT_MONEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_money), menu_h, admin_h],
            INPUT_TRX: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_trx), menu_h, admin_h],
            INPUT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_email), menu_h, admin_h],
            INPUT_COUPON: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_coupon), menu_h, admin_h],
            
            # ৬. এডমিন ইনপুট স্টেটস
            INPUT_ADMIN_PROD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_prod), admin_h, menu_h],
            INPUT_ADMIN_COUPON: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_coupon), admin_h, menu_h],
            INPUT_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast), admin_h, menu_h]
        },
        # ফলব্যাক: যেকোনো অবস্থায় start বা admin কমান্ড দিলে কাজ করবে
        fallbacks=[CommandHandler('start', start), CommandHandler('admin', admin_start)]
    )
    
    # হ্যান্ডলারগুলো অ্যাপে যুক্ত করা
    app.add_handler(conv)
    
    # ব্যালেন্স কাটার কমান্ড (/cut user amount) - গ্লোবাল হ্যান্ডলার হিসেবে রাখা হলো
    app.add_handler(CommandHandler("cut", cut_balance))
    
    # এডমিন ডিপোজিট অ্যাপ্রুভাল হ্যান্ডলার
    app.add_handler(CallbackQueryHandler(admin_deposit_access, pattern='^(ok|no|g|f)_'))
    
    print("Bot Running... (Press Ctrl+C to stop)")
    app.run_polling()

if __name__ == '__main__':
    main()
    
