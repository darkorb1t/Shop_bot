import telebot
import psycopg2
from psycopg2 import pool
import datetime
import threading
import time
import random
import string
import pytz # Fixed Timezone support
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
from threading import Thread

# --- কনফিগারেশন (Configuration) ---
# ⚠️ PASTE YOUR REAL TOKEN AND DB URL HERE
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE' 
DB_URL = "YOUR_NEON_DB_URL_HERE"

ADMIN_ID = 6250222523
ADMIN_USERNAME = "@darkorb1t" 

PAYMENT_NUM = "01611026722" 
PAYMENT_METHOD = "bKash (Send Money)"
REFER_BONUS = 1 

bot = telebot.TeleBot(BOT_TOKEN)

# --- 24/7 Server Code ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running Fast & Secure!"

def run():
    # use_reloader=False prevents double execution
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------

# --- 🚀 DATABASE CONNECTION POOL (FIXES LAG) ---
try:
    # Creates a pool of 1-20 open connections to reuse
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 20, DB_URL)
    if db_pool:
        print("✅ Database Pool Created (Fast Mode)")
except Exception as e:
    print(f"❌ DB Pool Error: {e}")

def get_db_connection():
    return db_pool.getconn()

def release_db_connection(conn):
    if conn:
        db_pool.putconn(conn)

# --- ভাষা ডাটাবেস (Friendly Tone Updated) ---
LANG_DICT = {
    'bn': {
        'welcome': "আসসালামু আলাইকুম, {name}! ❤️\nআমাদের সেবা নিতে আপনাকে স্বাগতম। আপনি আজ কি করতে চান?",
        'shop': "🛍️ কেনাকাটা (Shop)", 'profile': "👤 আমার প্রোফাইল", 'add_money': "💸 ব্যালেন্স অ্যাড",
        'orders': "📦 আমার অর্ডার", 'coupon': "🎁 কুপন", 'refer': "🗣️ রেফার",
        'support': "📞 হেল্পলাইন", 'lang_btn': "🌐 ভাষা (Language)",
        'shop_empty': "দুঃখিত প্রিয়! 😔 দোকানে এই মুহূর্তে কোনো পণ্য নেই।",
        'shop_title': "🛒 **আমাদের কালেকশন:**\nপছন্দের পণ্যটি বেছে নিন 👇",
        'buy_btn': "কিনে নিন", 'stock': "স্টক", 'unlimited': "আনলিমিটেড",
        'profile_title': "👤 **আপনার প্রোফাইল ডিটেইলস:**", 'balance': "ব্যালেন্স",
        'no_orders': "আপনি এখনো আমাদের থেকে কিছু কেনেননি। 🥺",
        'order_hist': "📦 **আপনার অর্ডার হিস্ট্রি:**",
        'processing': "প্রসেসিং হচ্ছে...",
        'expired': "⚠️ মেয়াদোত্তীর্ণ!",
        'low_bal': "দুঃখিত! আপনার ব্যালেন্স পর্যাপ্ত নেই। 😔 দয়া করে টাকা অ্যাড করুন।",
        'success': "আলহামদুলিল্লাহ! আপনার কেনাকাটা সফল হয়েছে। ❤️",
        'data_here': "👇 এই নিন আপনার পণ্য:",
        'file_cap': "📂 এই নিন আপনার ফাইল। ধন্যবাদ!",
        'stock_out': "ওহ নো! 🥺 এই আইটেমটি এইমাত্র শেষ হয়ে গেছে।",
        'ask_amount': "💰 **কত টাকা অ্যাড করতে চান?**\n(উদাহরণ: 100)",
        'invalid_amount': "প্রিয় গ্রাহক, দয়া করে শুধু ইংরেজি সংখ্যা লিখুন (যেমন: 100)।",
        'pay_instruct': "✅ **অনুরোধ: {amount} টাকা**\n━━━━━━━━━━━━\nআপনার {amount} টাকা এই নাম্বারে Send Money করুন:\n\n📞 `{num}` ({method})\n\n⚠️ টাকা পাঠানোর পর নিচের বক্সে **Transaction ID (TrxID)** লিখে পাঠান।",
        'req_sent': "✅ আপনার রিকোয়েস্ট পেয়েছি! এডমিন চেক করে খুব দ্রুত ব্যালেন্স দিয়ে দেবেন।",
        'deposit_received': "🎉 অভিনন্দন! আপনার ব্যালেন্স {amount} টাকা যোগ হয়েছে।",
        'deposit_rejected': "❌ দুঃখিত! আপনার পেমেন্ট রিকোয়েস্ট বাতিল করা হয়েছে।",
        'refer_msg': "🗣️ **রেফার লিংক:**\n`{link}`\n\nকেউ জয়েন করলে পাবেন: **{amount} টাকা**",
        'coupon_ask': "🎟️ **আপনার কুপন কোডটি দিন:**",
        'coupon_success': "🎉 কুপন সফল! {amount} টাকা বোনাস পেয়েছেন।",
        'coupon_invalid': "দুঃখিত, এই কোডটি ভুল বা মেয়াদ শেষ।",
        'choose_type': "🔽 আপনি কোন মোডে প্রবেশ করতে চান?",
        'customer': "👤 কাস্টমার",
        'reseller': "💼 রিসেলার",
        'reseller_login': "🔐 রিসেলার আইডি দিন:",
        'reseller_pass': "🔑 পাসওয়ার্ড দিন:",
        'login_success': "স্বাগতম বস! 😎 লগইন সফল।",
        'login_fail': "উফ! তথ্য ভুল হয়েছে।",
        'enter_email': "📧 সাবস্ক্রিপশনের জন্য আপনার **Gmail Address** দিন:",
        'order_processing': "✅ অর্ডার নেওয়া হয়েছে! এডমিন শীঘ্রই আপনাকে বুঝিয়ে দিবেন।"
    },
    'en': {
        'welcome': "Hello there, {name}! 👋\nWelcome to our store. How can I help you today?",
        'shop': "🛍️ Shop", 'profile': "👤 Profile", 'add_money': "💸 Add Funds",
        'orders': "📦 My Orders", 'coupon': "🎁 Coupon", 'refer': "🗣️ Refer",
        'support': "📞 Support", 'lang_btn': "🌐 Language",
        'shop_empty': "Sorry dear! 😔 The shop is currently empty.",
        'shop_title': "🛒 **Available Products:**\nChoose what you need 👇",
        'buy_btn': "Buy", 'stock': "Stock", 'unlimited': "Unlimited",
        'profile_title': "👤 **Your Profile Details:**", 'balance': "Balance",
        'no_orders': "You haven't purchased anything yet. 🥺",
        'order_hist': "📦 **Order History:**",
        'processing': "Processing...",
        'expired': "⚠️ Expired.",
        'low_bal': "Oops! Insufficient Balance! Please add funds. 😊",
        'success': "Yay! Purchase Successful! ❤️",
        'data_here': "👇 Here is your item:",
        'file_cap': "📂 Here is your file.",
        'stock_out': "Oh no! 🥺 Item just went out of stock.",
        'ask_amount': "💰 **How much to add?**\n(e.g., 100)",
        'invalid_amount': "❌ Invalid input! Numbers only.",
        'pay_instruct': "✅ **Request: {amount} tk**\n━━━━━━━━━━━━\nSend {amount} tk to:\n\n📞 `{num}` ({method})\n\n⚠️ Then enter the **Transaction ID (TrxID)** below.",
        'req_sent': "✅ Request Sent! Balance will be added shortly.",
        'deposit_received': "🎉 {amount} tk has been added to your account!",
        'deposit_rejected': "❌ Payment Rejected.",
        'refer_msg': "🗣️ **Refer Link:**\n`{link}`\n\nBonus: **{amount} tk**",
        'coupon_ask': "🎟️ **Enter Coupon Code:**",
        'coupon_success': "🎉 Coupon Redeemed! +{amount}tk",
        'coupon_invalid': "❌ Invalid Code.",
        'choose_type': "🔽 Select Mode:",
        'customer': "👤 Customer",
        'reseller': "💼 Reseller",
        'reseller_login': "🔐 Enter Reseller ID:",
        'reseller_pass': "🔑 Enter Password:",
        'login_success': "Welcome Boss! 😎 Login Successful!",
        'login_fail': "❌ Invalid Credentials!",
        'enter_email': "📧 Enter your **Gmail Address**:",
        'order_processing': "✅ Order Received! Admin will contact you."
    },
    # Placeholders for other languages to prevent crashes (You can translate these later)
    'ar': {'welcome': "Ahlan {name}!", 'shop': "🛍️ Shop", 'profile': "👤 Profile", 'shop_empty': "Empty", 'low_bal': "Low Balance", 'success': "Success", 'shop_title': "Products", 'balance': "Balance"},
    'hi': {'welcome': "Namaste {name}!", 'shop': "🛍️ Shop", 'profile': "👤 Profile", 'shop_empty': "Empty", 'low_bal': "Low Balance", 'success': "Success", 'shop_title': "Products", 'balance': "Balance"},
    'es': {'welcome': "Hola {name}!", 'shop': "🛍️ Shop", 'profile': "👤 Profile", 'shop_empty': "Empty", 'low_bal': "Low Balance", 'success': "Success", 'shop_title': "Products", 'balance': "Balance"},
    'fr': {'welcome': "Bonjour {name}!", 'shop': "🛍️ Shop", 'profile': "👤 Profile", 'shop_empty': "Empty", 'low_bal': "Low Balance", 'success': "Success", 'shop_title': "Products", 'balance': "Balance"},
    'ru': {'welcome': "Privet {name}!", 'shop': "🛍️ Shop", 'profile': "👤 Profile", 'shop_empty': "Empty", 'low_bal': "Low Balance", 'success': "Success", 'shop_title': "Products", 'balance': "Balance"},
    'pt': {'welcome': "Ola {name}!", 'shop': "🛍️ Shop", 'profile': "👤 Profile", 'shop_empty': "Empty", 'low_bal': "Low Balance", 'success': "Success", 'shop_title': "Products", 'balance': "Balance"},
    'id': {'welcome': "Halo {name}!", 'shop': "🛍️ Shop", 'profile': "👤 Profile", 'shop_empty': "Empty", 'low_bal': "Low Balance", 'success': "Success", 'shop_title': "Products", 'balance': "Balance"},
    'zh': {'welcome': "Ni Hao {name}!", 'shop': "🛍️ Shop", 'profile': "👤 Profile", 'shop_empty': "Empty", 'low_bal': "Low Balance", 'success': "Success", 'shop_title': "Products", 'balance': "Balance"}
}

# --- Initialize Tables ---
def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Main Tables
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, balance INTEGER DEFAULT 0, username TEXT, language TEXT DEFAULT 'en', is_reseller INTEGER DEFAULT 0)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, name TEXT, data TEXT, price INTEGER, reseller_price INTEGER DEFAULT 0, validity INTEGER DEFAULT 0, is_sub INTEGER DEFAULT 0, last_update DATE DEFAULT CURRENT_DATE, is_file INTEGER DEFAULT 0)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, user_id BIGINT, item_name TEXT, price INTEGER, data TEXT, date TEXT, is_file INTEGER DEFAULT 0)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS coupons (code TEXT PRIMARY KEY, amount INTEGER, uses INTEGER)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS resellers (resell_id TEXT PRIMARY KEY, password TEXT, active INTEGER DEFAULT 1)''')
            conn.commit()
            print("✅ Database Schema Synced!")
    except Exception as e:
        print(f"DB Init Error: {e}")
    finally:
        release_db_connection(conn)

init_db()

# --- HELPER FUNCTIONS ---
def get_lang_code(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT language FROM users WHERE user_id=%s", (user_id,))
            res = cursor.fetchone()
            return res[0] if res else 'en'
    except: return 'en'
    finally: release_db_connection(conn)

def get_str(lang, key, **kwargs):
    ld = LANG_DICT.get(lang, LANG_DICT['en'])
    text = ld.get(key, LANG_DICT['en'].get(key, key))
    try: return text.format(**kwargs)
    except: return text

def is_reseller_mode(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT is_reseller FROM users WHERE user_id=%s", (user_id,))
            res = cursor.fetchone()
            return res[0] == 1 if res else False
    except: return False
    finally: release_db_connection(conn)

# --- BACKGROUND TASK: INVENTORY DECAY (Fixed for BD Time) ---
def maintenance_loop():
    while True:
        conn = get_db_connection()
        try:
            # Fix: Use Bangladesh Timezone
            bd_tz = pytz.timezone('Asia/Dhaka')
            today = datetime.datetime.now(bd_tz).date()
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, price, validity, last_update FROM products WHERE validity > 0")
                items = cursor.fetchall()
                
                for item in items:
                    pid, price, valid, last_date = item
                    if str(last_date) != str(today):
                        new_valid = valid - 1
                        # Price Decay: 20% off
                        new_price = int(price * 0.8)
                        
                        if new_valid <= 0:
                            cursor.execute("DELETE FROM products WHERE id=%s", (pid,))
                        else:
                            cursor.execute("UPDATE products SET price=%s, validity=%s, last_update=%s WHERE id=%s", 
                                           (new_price, new_valid, today, pid))
                conn.commit()
        except Exception as e:
            print(f"Maintenance Error: {e}")
        finally:
            release_db_connection(conn)
        time.sleep(3600) # Check every 1 hour

Thread(target=maintenance_loop).start()

# --- BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def start(message):
    conn = get_db_connection()
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT language FROM users WHERE user_id=%s", (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                cursor.execute("INSERT INTO users (user_id, balance, username, language, is_reseller) VALUES (%s, 0, %s, 'en', 0)", (user_id, username))
                conn.commit()
                # Referral
                parts = message.text.split()
                if len(parts) > 1 and parts[1].isdigit():
                        ref_id = int(parts[1])
                        if ref_id != user_id:
                            cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (REFER_BONUS, ref_id))
                            conn.commit()
                            try: bot.send_message(ref_id, f"🎉 Refer Bonus: +{REFER_BONUS}tk")
                            except: pass
                send_lang_selector(message.chat.id)
            else:
                cursor.execute("UPDATE users SET is_reseller=0 WHERE user_id=%s", (user_id,))
                conn.commit()
                send_lang_selector(message.chat.id)
    except Exception as e: print(e)
    finally: release_db_connection(conn)

def send_lang_selector(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
        InlineKeyboardButton("🇧🇩 বাংলা", callback_data="set_lang_bn"),
        InlineKeyboardButton("🇸🇦 العربية", callback_data="set_lang_ar"),
        InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="set_lang_hi"),
        InlineKeyboardButton("🇪🇸 Español", callback_data="set_lang_es"),
        InlineKeyboardButton("🇫🇷 Français", callback_data="set_lang_fr"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru"),
        InlineKeyboardButton("🇵🇹 Português", callback_data="set_lang_pt"),
        InlineKeyboardButton("🇮🇩 Bahasa", callback_data="set_lang_id"),
        InlineKeyboardButton("🇨🇳 中文", callback_data="set_lang_zh")
    )
    bot.send_message(chat_id, "🌍 **Please Select Your Language:**\n🌍 **আপনার ভাষা নির্বাচন করুন:**", reply_markup=markup, parse_mode="Markdown")

def ask_user_type(user_id, lang):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(get_str(lang, 'customer'), callback_data="mode_customer"))
    markup.add(InlineKeyboardButton(get_str(lang, 'reseller'), callback_data="mode_reseller"))
    bot.send_message(user_id, get_str(lang, 'choose_type'), reply_markup=markup)

def process_reseller_id(message, lang):
    if message.content_type != 'text': return
    rid = message.text.strip()
    msg = bot.send_message(message.chat.id, get_str(lang, 'reseller_pass'))
    bot.register_next_step_handler(msg, process_reseller_pass, rid, lang)

def process_reseller_pass(message, rid,lang):
    if message.content_type != 'text': return
    rpass = message.text.strip()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM resellers WHERE resell_id=%s AND password=%s", (rid, rpass))
            res = cursor.fetchone()
            if res:
                cursor.execute("UPDATE users SET is_reseller=1 WHERE user_id=%s", (message.from_user.id,))
                conn.commit()
                bot.send_message(message.chat.id, get_str(lang, 'login_success'))
                show_main_menu(message.from_user.id, lang, message.from_user.first_name)
            else:
                bot.send_message(message.chat.id, get_str(lang, 'login_fail'))
                ask_user_type(message.from_user.id, lang)
    finally: release_db_connection(conn)

def show_main_menu(user_id, lang, name):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT is_reseller FROM users WHERE user_id=%s", (user_id,))
            res = cursor.fetchone()
            is_res = res[0] if res else 0

        title_prefix = "💼 [RESELLER] " if is_res else ""
        txt = f"{title_prefix}" + get_str(lang, 'welcome', name=name)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton(get_str(lang, 'shop'), callback_data="shop"),
                   InlineKeyboardButton(get_str(lang, 'profile'), callback_data="profile"))
        markup.add(InlineKeyboardButton(get_str(lang, 'add_money'), callback_data="deposit_request"),
                   InlineKeyboardButton(get_str(lang, 'orders'), callback_data="my_orders"))
        markup.add(InlineKeyboardButton(get_str(lang, 'coupon'), callback_data="redeem_btn"),
                   InlineKeyboardButton(get_str(lang, 'refer'), callback_data="refer_link"))
        markup.add(InlineKeyboardButton(get_str(lang, 'lang_btn'), callback_data="lang_select"),
                   InlineKeyboardButton(get_str(lang, 'support'), callback_data="support"))
        
        if user_id == ADMIN_ID:
            markup.add(InlineKeyboardButton("👑 Admin Panel", callback_data="panel_main"))
            
        bot.send_message(user_id, txt, reply_markup=markup)
    finally: release_db_connection(conn)

# --- CALLBACK HANDLER (Fixed & Optimized) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    conn = get_db_connection() # Grab connection from pool
    try:
        user_id = call.from_user.id
        
        if call.data.startswith("set_lang_"):
            new_lang = call.data.split("_")[2]
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET language=%s WHERE user_id=%s", (new_lang, user_id))
                conn.commit()
            bot.delete_message(call.message.chat.id, call.message.message_id)
            ask_user_type(user_id, new_lang)
            return
        
        lang = get_lang_code(user_id)

        if call.data == "mode_customer":
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET is_reseller=0 WHERE user_id=%s", (user_id,))
                conn.commit()
            show_main_menu(user_id, lang, call.from_user.first_name)
        
        elif call.data == "mode_reseller":
            msg = bot.send_message(user_id, get_str(lang, 'reseller_login'))
            bot.register_next_step_handler(msg, process_reseller_id, lang)

        elif call.data == "shop":
            show_shop(user_id, lang, conn) # Pass connection to save time
        
        # --- FIX: Profile Button Logic Added ---
        elif call.data == "profile":
            with conn.cursor() as c:
                c.execute("SELECT username, balance, is_reseller FROM users WHERE user_id=%s", (user_id,))
                ud = c.fetchone()
            
            role = "👑 Reseller" if ud[2] else "👤 Customer"
            msg = f"{get_str(lang, 'profile_title')}\n\n📛 **Name:** {ud[0]}\n💳 **{get_str(lang, 'balance')}:** {ud[1]}tk\n🏷️ **Role:** {role}"
            bot.send_message(user_id, msg, parse_mode="Markdown")

        elif call.data.startswith("buy_"):
            prod_id = call.data.split("_")[1]
            check_purchase(user_id, prod_id, lang, conn)

        elif call.data == "deposit_request":
            msg = bot.send_message(user_id, get_str(lang, 'ask_amount'))
            bot.register_next_step_handler(msg, process_deposit_amount, lang)
            
        elif call.data == "redeem_btn":
            msg = bot.send_message(user_id, get_str(lang, 'coupon_ask'))
            bot.register_next_step_handler(msg, redeem_process, lang)
            
        elif call.data == "refer_link":
             link = f"https://t.me/{bot.get_me().username}?start={user_id}"
             bot.send_message(user_id, get_str(lang, 'refer_msg', link=link, amount=REFER_BONUS), parse_mode="Markdown")

        elif call.data == "support":
             bot.send_message(user_id, f"📞 Support: {ADMIN_USERNAME}")

        # Admin Panel
        elif call.data == "panel_main" and user_id == ADMIN_ID:
             m = InlineKeyboardMarkup()
             m.add(InlineKeyboardButton("➕ Add Product", callback_data="panel_add"))
             m.add(InlineKeyboardButton("⏳ Add Sub", callback_data="panel_sub"))
             m.add(InlineKeyboardButton("📉 Add Decay", callback_data="panel_decay"))
             m.add(InlineKeyboardButton("👥 Gen Reseller", callback_data="panel_gen_resell"))
             bot.send_message(user_id, "👑 **Admin Panel**", reply_markup=m, parse_mode="Markdown")
        
        elif call.data == "panel_add": bot.send_message(user_id, "Use: `/addprod Name|Price|Data`")
        elif call.data == "panel_sub": bot.send_message(user_id, "Use: `/addsub Name|Price|Days`")
        elif call.data == "panel_decay": bot.send_message(user_id, "Use: `/adddecay Name|Price|Days|Data`")
        elif call.data == "panel_gen_resell": bot.send_message(user_id, "Click /genresell")

    except Exception as e:
        print(f"Callback Error: {e}")
    finally:
        release_db_connection(conn) # Close connection

# --- SHOP LOGIC (Fixed SQL Group By) ---
def show_shop(user_id, lang, conn):
    is_res = is_reseller_mode(user_id)
    with conn.cursor() as cursor:
        # FIX: Using MAX(id) to select a valid ID while grouping
        cursor.execute("""
            SELECT MAX(id), name, price, reseller_price, validity, is_sub, count(*) 
            FROM products 
            GROUP BY name, price, reseller_price, validity, is_sub
        """)
        items = cursor.fetchall()
    
    if not items:
        bot.send_message(user_id, get_str(lang, 'shop_empty'))
        return

    msg = get_str(lang, 'shop_title')
    markup = InlineKeyboardMarkup()
    
    for item in items:
        pid, name, price, r_price, valid, is_sub, stock = item
        final_price = r_price if (is_res and r_price > 0) else price
        
        validity_txt = f"⏳{valid}d" if valid > 0 else "♾️"
        stock_txt = "✅" if is_sub else f"📦{stock}"
        
        btn_text = f"{name} | {final_price}tk | {validity_txt} | {stock_txt}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"buy_{pid}"))
    
    bot.send_message(user_id, msg, reply_markup=markup, parse_mode="Markdown")

def check_purchase(user_id, prod_id, lang, conn):
    with conn.cursor() as cursor:
        # Get Product Name first
        cursor.execute("SELECT name FROM products WHERE id=%s", (prod_id,))
        proto = cursor.fetchone()
        if not proto: return
        
        # Get ONE available item (FIFO)
        cursor.execute("SELECT id, name, price, reseller_price, data, is_sub FROM products WHERE name=%s LIMIT 1", (proto[0],))
        item = cursor.fetchone()
        
        if not item:
            bot.send_message(user_id, get_str(lang, 'stock_out'))
            return

        real_pid, name, price, r_price, data, is_sub = item
        
        # Check Balance
        cursor.execute("SELECT balance, is_reseller FROM users WHERE user_id=%s", (user_id,))
        ud = cursor.fetchone()
        bal, is_res = ud[0], ud[1]
        
        final_price = r_price if (is_res and r_price > 0) else price
        
        if bal < final_price:
            bot.send_message(user_id, get_str(lang, 'low_bal'))
            return
            
        if is_sub == 1:
            msg = bot.send_message(user_id, get_str(lang, 'enter_email'))
            bot.register_next_step_handler(msg, process_sub_order, final_price, name, lang)
        else:
            # Instant Delivery
            cursor.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (final_price, user_id))
            cursor.execute("DELETE FROM products WHERE id=%s", (real_pid,))
            cursor.execute("INSERT INTO orders (user_id, item_name, price, data, date) VALUES (%s, %s, %s, %s, %s)", 
                           (user_id, name, final_price, data, str(datetime.date.today())))
            conn.commit()
            
            bot.send_message(user_id, get_str(lang, 'success'))
            bot.send_message(user_id, f"{get_str(lang, 'data_here')}\n\n`{data}`", parse_mode="Markdown")

def process_sub_order(message, price, name, lang):
    if message.content_type != 'text': return
    email = message.text
    user_id = message.from_user.id
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (price, user_id))
            cursor.execute("INSERT INTO orders (user_id, item_name, price, data, date) VALUES (%s, %s, %s, %s, %s)", 
                           (user_id, name, price, email, str(datetime.date.today())))
            conn.commit()
        bot.send_message(user_id, get_str(lang, 'order_processing'))
        bot.send_message(ADMIN_ID, f"🔔 **New Subscription Order!**\nUser: {user_id}\nItem: {name}\nPrice: {price}\n📧 **Gmail:** `{email}`")
    finally: release_db_connection(conn)

# --- OTHER HANDLERS ---
def redeem_process(message, lang):
    if message.content_type != 'text': return
    code = message.text.strip()
    user_id = message.from_user.id
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT amount, uses FROM coupons WHERE code=%s", (code,))
            res = cursor.fetchone()
            if res and res[1] > 0:
                cursor.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (res[0], user_id))
                cursor.execute("UPDATE coupons SET uses=uses-1 WHERE code=%s", (code,))
                conn.commit()
                bot.send_message(user_id, get_str(lang, 'coupon_success', amount=res[0]))
            else:
                bot.send_message(user_id, get_str(lang, 'coupon_invalid'))
    finally: release_db_connection(conn)

def process_deposit_amount(message, lang):
    if message.content_type != 'text' or not message.text.isdigit():
        bot.send_message(message.chat.id, get_str(lang, 'invalid_amount'))
        return
    amount = int(message.text)
    txt = get_str(lang, 'pay_instruct', amount=amount, num=PAYMENT_NUM, method=PAYMENT_METHOD)
    msg = bot.send_message(message.chat.id, txt, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_trxid, amount, lang)

def process_trxid(message, amount, lang):
    if message.content_type != 'text': return
    trx = message.text
    bot.send_message(ADMIN_ID, f"💰 **Deposit Request:**\nUser: {message.from_user.id}\nAmount: {amount}\nTrxID: `{trx}`", parse_mode="Markdown")
    bot.send_message(message.chat.id, get_str(lang, 'req_sent'))

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['genresell'])
def gen_resell(m):
    if m.from_user.id == ADMIN_ID:
        rid = "R-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        rpass = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO resellers (resell_id, password) VALUES (%s, %s)", (rid, rpass))
                conn.commit()
            bot.reply_to(m, f"✅ **Reseller Created!**\nID: `{rid}`\nPass: `{rpass}`", parse_mode="Markdown")
        finally: release_db_connection(conn)

@bot.message_handler(commands=['addsub'])
def add_sub(m):
    if m.from_user.id == ADMIN_ID:
        try:
            n, p, v = m.text.split(' ', 1)[1].split('|')
            rp = int(int(p) * 0.9) 
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO products (name, price, reseller_price, validity, is_sub, data) VALUES (%s, %s, %s, %s, 1, 'Manual')", 
                               (n.strip(), int(p), rp, int(v)))
                conn.commit()
            release_db_connection(conn)
            bot.reply_to(m, "✅ Subscription Product Added")
        except: pass

@bot.message_handler(commands=['adddecay'])
def add_decay(m):
    if m.from_user.id == ADMIN_ID:
        try:
            n, p, v, d = m.text.split(' ', 1)[1].split('|')
            rp = int(int(p) * 0.9)
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO products (name, price, reseller_price, validity, is_sub, data, last_update) VALUES (%s, %s, %s, %s, 0, %s, CURRENT_DATE)", 
                               (n.strip(), int(p), rp, int(v), d.strip()))
                conn.commit()
            release_db_connection(conn)
            bot.reply_to(m, "✅ Decaying Product Added")
        except: pass

@bot.message_handler(commands=['addprod'])
def add_prod(m):
    if m.from_user.id == ADMIN_ID:
        try:
            n, p, d = m.text.split(' ', 1)[1].split('|')
            rp = int(int(p) * 0.9)
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO products (name, price, reseller_price, data, is_file) VALUES (%s, %s, %s, %s, 0)", (n.strip(), int(p), rp, d.strip()))
                conn.commit()
            release_db_connection(conn)
            bot.reply_to(m, "✅ Added")
        except: pass

print("✅ Bot is Running with Lag Fix, Text Checks & Friendly Tone...")
keep_alive()
bot.polling()
