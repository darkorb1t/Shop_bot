import telebot
import psycopg2
import datetime
import threading
import time
import random
import string
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
from threading import Thread

# --- কনফিগারেশন (Configuration) ---
BOT_TOKEN = '8036869041:AAGiSBZ9OrWsiO1EGF6wXiZ4GZ8TYEb9dOQ' 
ADMIN_ID = 6250222523
ADMIN_USERNAME = "@darkorb1t" 

PAYMENT_NUM = "01611026722" 
PAYMENT_METHOD = "bKash (Send Money)"
REFER_BONUS = 1 

# আপনার Neon Database URL
DB_URL = "postgresql://neondb_owner:npg_aLkQSZ6Xz3Ng@ep-super-star-a49zg5kc-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

bot = telebot.TeleBot(BOT_TOKEN)

# --- 24/7 Server Code ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running with Reseller & Auto-Decay System!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------

# --- ভাষা ডাটাবেস (Language Database) ---
LANG_DICT = {
    'bn': {
        'welcome': "স্বাগতম! {name} আপনার অ্যাকাউন্ট রেডি।\nনিচের মেনু থেকে অপশন বেছে নিন:",
        'shop': "🛍️ দোকান (Shop)", 'profile': "👤 প্রোফাইল", 'add_money': "💸 টাকা যোগ করুন (Add Money)",
        'orders': "📦 আমার অর্ডার", 'coupon': "🎁 কুপন", 'refer': "🗣️ রেফার করুন",
        'support': "📞 সাপোর্ট", 'lang_btn': "🌐 ভাষা (Language)",
        'shop_empty': "⚠️ দোকানে বর্তমানে কোনো পণ্য নেই।",
        'shop_title': "🛒 **প্রোডাক্ট লিস্ট:**",
        'buy_btn': "কিনে নিন", 'stock': "স্টক", 'unlimited': "আনলিমিটেড (Unlimited)",
        'profile_title': "👤 **আপনার প্রোফাইল**", 'balance': "ব্যালেন্স",
        'no_orders': "❌ আপনি এখনো কিছু কিনেননি।",
        'order_hist': "📦 **আপনার অর্ডার হিস্ট্রি:**",
        'processing': "প্রসেসিং হচ্ছে...",
        'expired': "⚠️ দুঃখিত, এই বাটনটি মেয়াদোত্তীর্ণ।",
        'low_bal': "❌ আপনার অ্যাকাউন্টে পর্যাপ্ত টাকা নেই!",
        'success': "✅ কেনাকাটা সফল!",
        'data_here': "👇 আপনার ডাটা:",
        'file_cap': "📂 এই নিন আপনার ফাইল। ধন্যবাদ!",
        'stock_out': "⚠️ দুঃখিত! এই আইটেমটি এইমাত্র শেষ হয়ে গেছে।",
        'ask_amount': "💰 **কত টাকা অ্যাড করতে চান?**\n\nশুধুমাত্র সংখ্যা লিখুন (যেমন: 100):",
        'invalid_amount': "❌ ভুল ইনপুট! দয়া করে শুধুমাত্র ইংরেজি সংখ্যা লিখুন (যেমন: 100)।",
        'pay_instruct': "✅ **অনুরোধ: {amount} টাকা**\n━━━━━━━━━━━━\nআপনার {amount} টাকা এই নাম্বারে Send Money করুন:\n\n📞 `{num}` ({method})\n\n⚠️ টাকা পাঠানোর পর নিচের বক্সে **Transaction ID (TrxID)** লিখে পাঠান।",
        'req_sent': "✅ **আপনার রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে!**\nঅ্যাডমিন চেক করে অ্যাপ্রুভ করলে ব্যালেন্স অ্যাড হয়ে যাবে।",
        'deposit_received': "🎉 আপনার অ্যাকাউন্টে {amount} টাকা যোগ করা হয়েছে!",
        'deposit_rejected': "❌ দুঃখিত! আপনার পেমেন্ট রিকোয়েস্ট বাতিল করা হয়েছে।",
        'refer_msg': "🗣️ **রেফার লিংক:**\n`{link}`\n\nকেউ জয়েন করলে পাবেন: **{amount} টাকা**",
        'coupon_ask': "🎟️ **কুপন কোড দিন:**\n\nআপনার কোডটি নিচে লিখুন:",
        'coupon_success': "🎉 কুপন সফল! {amount} টাকা যোগ হয়েছে।",
        'coupon_invalid': "❌ ভুল কোড বা মেয়াদ শেষ।",
        # --- NEW FEATURES ---
        'choose_type': "🔽 আপনি কোন মোডে প্রবেশ করতে চান?",
        'customer': "👤 কাস্টমার (Customer)",
        'reseller': "💼 রিসেলার (Reseller)",
        'reseller_login': "🔐 রিসেলার আইডি দিন:",
        'reseller_pass': "🔑 রিসেলার পাসওয়ার্ড দিন:",
        'login_success': "✅ রিসেলার লগইন সফল!",
        'login_fail': "❌ ভুল তথ্য!",
        'enter_email': "📧 অনুগ্রহ করে আপনার **Gmail Address** দিন (অর্ডার প্রসেসিংয়ের জন্য):",
        'order_processing': "✅ অর্ডার নেওয়া হয়েছে! এডমিন শীঘ্রই আপনাকে ইমেইল বা মেসেজে পণ্য বুঝিয়ে দিবেন।"
    },
    'en': {
        'welcome': "Welcome! {name}, your account is ready.\nSelect an option below:",
        'shop': "🛍️ Shop", 'profile': "👤 Profile", 'add_money': "💸 Add Money",
        'orders': "📦 My Orders", 'coupon': "🎁 Coupon", 'refer': "🗣️ Refer",
        'support': "📞 Support", 'lang_btn': "🌐 Language",
        'shop_empty': "⚠️ Shop is currently empty.",
        'shop_title': "🛒 **Product List:**",
        'buy_btn': "Buy", 'stock': "Stock", 'unlimited': "Unlimited",
        'profile_title': "👤 **Your Profile**", 'balance': "Balance",
        'no_orders': "❌ No orders found.",
        'order_hist': "📦 **Order History:**",
        'processing': "Processing...",
        'expired': "⚠️ Button Expired.",
        'low_bal': "❌ Insufficient Balance!",
        'success': "✅ Purchase Successful!",
        'data_here': "👇 Your Data:",
        'file_cap': "📂 Here is your file.",
        'stock_out': "❌ Stock Out!",
        'ask_amount': "💰 **How much to add?**\n\nEnter amount in numbers (e.g., 100):",
        'invalid_amount': "❌ Invalid input! Enter numbers only.",
        'pay_instruct': "✅ **Request: {amount} tk**\n━━━━━━━━━━━━\nSend {amount} tk to this number:\n\n📞 `{num}` ({method})\n\n⚠️ After sending, please enter the **Transaction ID (TrxID)** below.",
        'req_sent': "✅ **Request Sent!**\nBalance will be added after admin approval.",
        'deposit_received': "🎉 {amount} tk has been added to your account!",
        'deposit_rejected': "❌ Sorry! Your payment request was rejected.",
        'refer_msg': "🗣️ **Refer Link:**\n`{link}`\n\nBonus per invite: **{amount} tk**",
        'coupon_ask': "🎟️ **Enter Coupon Code:**",
        'coupon_success': "🎉 Coupon Redeemed! +{amount}tk",
        'coupon_invalid': "❌ Invalid or Expired Code.",
        # --- NEW FEATURES ---
        'choose_type': "🔽 Select your mode:",
        'customer': "👤 Customer",
        'reseller': "💼 Reseller",
        'reseller_login': "🔐 Enter Reseller ID:",
        'reseller_pass': "🔑 Enter Password:",
        'login_success': "✅ Reseller Login Successful!",
        'login_fail': "❌ Invalid Credentials!",
        'enter_email': "📧 Please enter your **Gmail Address** for the subscription:",
        'order_processing': "✅ Order Received! Admin will contact you shortly."
    },
    # (Other languages kept as they are)
    'ar': {'welcome': "أهلاً {name}!", 'shop': "🛍️ المتجر", 'profile': "👤 الملف", 'add_money': "💸 شحن", 'orders': "📦 طلباتي", 'coupon': "🎁 قسيمة", 'refer': "🗣️ دعوة", 'support': "📞 الدعم", 'lang_btn': "🌐 اللغة", 'shop_empty': "فارغ", 'shop_title': "منتجات", 'buy_btn': "شراء", 'stock': "مخزون", 'unlimited': "غير محدود", 'profile_title': "ملف", 'balance': "رصيد", 'no_orders': "لا يوجد", 'order_hist': "سجل", 'processing': "...", 'expired': "منتهي", 'low_bal': "رصيد منخفض", 'success': "تم", 'data_here': "بيانات:", 'file_cap': "ملف", 'stock_out': "نفذ", 'ask_amount': "كم المبلغ؟", 'invalid_amount': "أرقام فقط", 'pay_instruct': "أرسل {amount} إلى `{num}`. TrxID?", 'req_sent': "تم الإرسال", 'deposit_received': "+{amount}", 'deposit_rejected': "مرفوض", 'refer_msg': "رابط: `{link}`", 'coupon_ask': "كود:", 'coupon_success': "+{amount}", 'coupon_invalid': "خطأ"},
    'hi': {'welcome': "नमस्ते {name}!", 'shop': "🛍️ दुकान", 'profile': "👤 प्रोफ़ाइल", 'add_money': "💸 पैसे डालें", 'orders': "📦 ऑर्डर", 'coupon': "🎁 कूपन", 'refer': "🗣️ रेफर", 'support': "📞 मदद", 'lang_btn': "🌐 भाषा", 'shop_empty': "खाली", 'shop_title': "उत्पाद", 'buy_btn': "खरीदें", 'stock': "स्टॉक", 'unlimited': "असीमित", 'profile_title': "प्रोफ़ाइल", 'balance': "बैलेंस", 'no_orders': "कोई नहीं", 'order_hist': "इतिहास", 'processing': "...", 'expired': "समाप्त", 'low_bal': "कम बैलेंस", 'success': "सफल", 'data_here': "डेटा:", 'file_cap': "फ़ाइल", 'stock_out': "स्टॉक खत्म", 'ask_amount': "राशि?", 'invalid_amount': "संख्या", 'pay_instruct': "{amount} भेजें `{num}` पर. TrxID?", 'req_sent': "भेजा गया", 'deposit_received': "+{amount}", 'deposit_rejected': "अस्वीकृत", 'refer_msg': "लिंक: `{link}`", 'coupon_ask': "कोड:", 'coupon_success': "+{amount}", 'coupon_invalid': "गलत"},
    # (Other languages skipped for brevity, they remain in your original code)
}

# --- Database Connection (PostgreSQL) ---
def get_db_connection():
    return psycopg2.connect(DB_URL)

# --- Initialize Tables & Update Schema (Automatic) ---
def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Basic Tables
                cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, balance INTEGER DEFAULT 0, username TEXT, language TEXT DEFAULT 'en')''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, name TEXT, data TEXT, price INTEGER, is_file INTEGER DEFAULT 0)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, user_id BIGINT, item_name TEXT, price INTEGER, data TEXT, date TEXT, is_file INTEGER DEFAULT 0)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS coupons (code TEXT PRIMARY KEY, amount INTEGER, uses INTEGER)''')
                
                # --- NEW TABLES & COLUMNS FOR UPDATE ---
                # 1. Resellers Table (Stores ID and Password)
                cursor.execute('''CREATE TABLE IF NOT EXISTS resellers (resell_id TEXT PRIMARY KEY, password TEXT, active INTEGER DEFAULT 1)''')
                
                # 2. Update Users Table (Add Reseller Status Column)
                try: cursor.execute("ALTER TABLE users ADD COLUMN is_reseller INTEGER DEFAULT 0")
                except: pass # Ignore if already exists
                
                # 3. Update Products Table (Add Price, Validity, Subscription Columns)
                try: cursor.execute("ALTER TABLE products ADD COLUMN reseller_price INTEGER DEFAULT 0")
                except: pass
                try: cursor.execute("ALTER TABLE products ADD COLUMN validity INTEGER DEFAULT 0") # 0 = Unlimited
                except: pass
                try: cursor.execute("ALTER TABLE products ADD COLUMN is_sub INTEGER DEFAULT 0") # 1 = Ask Gmail
                except: pass
                try: cursor.execute("ALTER TABLE products ADD COLUMN last_update DATE DEFAULT CURRENT_DATE")
                except: pass

                conn.commit()
                print("Database Schema Updated Successfully!")
    except Exception as e:
        print(f"DB Init Error: {e}")

init_db()
  # --- HELPER FUNCTIONS ---
def get_lang_code(user_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT language FROM users WHERE user_id=%s", (user_id,))
                res = cursor.fetchone()
                return res[0] if res else 'en'
    except: return 'en'

def get_str(lang, key, **kwargs):
    ld = LANG_DICT.get(lang, LANG_DICT['en'])
    text = ld.get(key, LANG_DICT['en'].get(key, key))
    try: return text.format(**kwargs)
    except: return text

# Check if user is logged in as Reseller
def is_reseller_mode(user_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT is_reseller FROM users WHERE user_id=%s", (user_id,))
                res = cursor.fetchone()
                return res[0] == 1 if res else False
    except: return False

# --- BACKGROUND TASK: INVENTORY DECAY (Run every 1 hour) ---
def maintenance_loop():
    while True:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Logic: Find items where validity > 0 and last_update != today
                    cursor.execute("SELECT id, price, validity, last_update FROM products WHERE validity > 0")
                    items = cursor.fetchall()
                    today = datetime.date.today()
                    
                    for item in items:
                        pid, price, valid, last_date = item
                        if str(last_date) != str(today):
                            new_valid = valid - 1
                            
                            # Price Decay: 20% off
                            new_price = int(price * 0.8)
                            
                            if new_valid <= 0:
                                # Auto Delete if expired
                                cursor.execute("DELETE FROM products WHERE id=%s", (pid,))
                                print(f"Item {pid} expired and deleted.")
                            else:
                                # Update Price & Date
                                cursor.execute("UPDATE products SET price=%s, validity=%s, last_update=%s WHERE id=%s", 
                                               (new_price, new_valid, today, pid))
                    conn.commit()
        except Exception as e:
            print(f"Maintenance Error: {e}")
        time.sleep(3600) # Check every 1 hour

# Start the background thread
Thread(target=maintenance_loop).start()

# --- BOT COMMANDS: START & LOGIN ---

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        username = message.from_user.username
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT language FROM users WHERE user_id=%s", (user_id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    # New User: Register
                    cursor.execute("INSERT INTO users (user_id, balance, username, language, is_reseller) VALUES (%s, 0, %s, 'en', 0)", (user_id, username))
                    conn.commit()
                    
                    # Referral Logic
                    parts = message.text.split()
                    if len(parts) > 1:
                        try:
                            referrer_id = int(parts[1])
                            if referrer_id != user_id:
                                cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (REFER_BONUS, referrer_id))
                                conn.commit()
                                try: bot.send_message(referrer_id, f"🎉 Refer Bonus: +{REFER_BONUS}tk")
                                except: pass
                        except: pass
                    
                    send_lang_selector(message.chat.id)
                    return
                else:
                    # Existing User: Reset Reseller Mode & Ask Language/Mode again
                    cursor.execute("UPDATE users SET is_reseller=0 WHERE user_id=%s", (user_id,))
                    conn.commit()
                    send_lang_selector(message.chat.id)

    except Exception as e:
        print(f"Start Error: {e}")

def send_lang_selector(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
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

# --- RESELLER LOGIN PROCESS ---
def process_reseller_id(message, lang):
    rid = message.text.strip()
    msg = bot.send_message(message.chat.id, get_str(lang, 'reseller_pass'))
    bot.register_next_step_handler(msg, process_reseller_pass, rid, lang)

def process_reseller_pass(message, rid, lang):
    rpass = message.text.strip()
    with get_db_connection() as conn:
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
              # --- MAIN MENU DISPLAY ---
def show_main_menu(user_id, lang, name):
    is_res = is_reseller_mode(user_id)
    # Add a tag if the user is a reseller
    title_prefix = "💼 [RESELLER] " if is_res else ""
    
    txt = f"{title_prefix}" + get_str(lang, 'welcome', name=name)
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton(get_str(lang, 'shop'), callback_data="shop"),
        InlineKeyboardButton(get_str(lang, 'profile'), callback_data="profile")
    )
    markup.add(
        InlineKeyboardButton(get_str(lang, 'add_money'), callback_data="deposit_request"),
        InlineKeyboardButton(get_str(lang, 'orders'), callback_data="my_orders")
    )
    markup.add(
        InlineKeyboardButton(get_str(lang, 'coupon'), callback_data="redeem_btn"),
        InlineKeyboardButton(get_str(lang, 'refer'), callback_data="refer_link")
    )
    markup.add(
        InlineKeyboardButton(get_str(lang, 'lang_btn'), callback_data="lang_select"),
        InlineKeyboardButton(get_str(lang, 'support'), callback_data="support")
    )
    
    # Admin Panel Button (Only visible to Admin)
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("👑 Admin Panel", callback_data="panel_main"))
        
    bot.send_message(user_id, txt, reply_markup=markup)

# --- CALLBACK HANDLER (BUTTON CLICKS) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        user_id = call.from_user.id
        
        # Language Selection
        if call.data.startswith("set_lang_"):
            new_lang = call.data.split("_")[2]
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE users SET language=%s WHERE user_id=%s", (new_lang, user_id))
                    conn.commit()
            bot.delete_message(call.message.chat.id, call.message.message_id)
            ask_user_type(user_id, new_lang) # After language, ask for Mode (Customer/Reseller)
            return
        
        lang = get_lang_code(user_id)

        # --- MODE SELECTION ---
        if call.data == "mode_customer":
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE users SET is_reseller=0 WHERE user_id=%s", (user_id,))
                    conn.commit()
            show_main_menu(user_id, lang, call.from_user.first_name)
        
        elif call.data == "mode_reseller":
            msg = bot.send_message(user_id, get_str(lang, 'reseller_login'))
            bot.register_next_step_handler(msg, process_reseller_id, lang)

        # --- MENU ACTIONS ---
        elif call.data == "lang_select":
            send_lang_selector(call.message.chat.id)

        elif call.data == "shop":
            show_shop(user_id, lang)
        
        elif call.data.startswith("buy_"):
            prod_id = call.data.split("_")[1]
            check_purchase(user_id, prod_id, lang)

        elif call.data == "refer_link":
            link = f"https://t.me/{bot.get_me().username}?start={user_id}"
            bot.send_message(user_id, get_str(lang, 'refer_msg', link=link, amount=REFER_BONUS), parse_mode="Markdown")
            
        elif call.data == "redeem_btn":
            msg = bot.send_message(user_id, get_str(lang, 'coupon_ask'))
            bot.register_next_step_handler(msg, redeem_process, lang)

        elif call.data == "deposit_request":
            msg = bot.send_message(user_id, get_str(lang, 'ask_amount'))
            bot.register_next_step_handler(msg, process_deposit_amount, lang)

        elif call.data == "support":
             bot.send_message(user_id, f"📞 Support: {ADMIN_USERNAME}")

        # --- ADMIN PANEL BUTTONS ---
        elif call.data == "panel_main":
             if user_id != ADMIN_ID: return
             m = InlineKeyboardMarkup()
             m.add(InlineKeyboardButton("➕ Add Product (Manual)", callback_data="panel_add"))
             m.add(InlineKeyboardButton("⏳ Add Subscription (Canva)", callback_data="panel_sub")) # New
             m.add(InlineKeyboardButton("📉 Add Decaying Item", callback_data="panel_decay")) # New
             m.add(InlineKeyboardButton("👥 Generate Reseller ID", callback_data="panel_gen_resell")) # New
             bot.send_message(user_id, "👑 **Admin Panel**\nSelect an action:", reply_markup=m, parse_mode="Markdown")
        
        # Admin Instructions triggers
        elif call.data == "panel_add":
             bot.send_message(user_id, "📝 **Add Normal Product:**\nFormat: `/addprod Name|Price|Data`")
        elif call.data == "panel_sub":
             bot.send_message(user_id, "📝 **Add Subscription (Canva):**\nFormat: `/addsub Name|Price|Days`\n_(Use 0 days for Unlimited)_")
        elif call.data == "panel_decay":
             bot.send_message(user_id, "📝 **Add Decaying Product:**\nFormat: `/adddecay Name|Price|Days|Data`\n_(Price drops 20% daily, deletes on last day)_")
        elif call.data == "panel_gen_resell":
             bot.send_message(user_id, "⚙️ Click /genresell to create a new ID.")

    except Exception as e:
        print(f"Callback Error: {e}")

# --- SHOP & PURCHASE LOGIC ---
def show_shop(user_id, lang):
    is_res = is_reseller_mode(user_id)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Group by name to show stock counts nicely
            cursor.execute("SELECT id, name, price, reseller_price, validity, is_sub, count(*) as stock FROM products GROUP BY name, price, reseller_price, validity, is_sub")
            items = cursor.fetchall()
    
    if not items:
        bot.send_message(user_id, get_str(lang, 'shop_empty'))
        return

    msg = get_str(lang, 'shop_title') + "\n"
    markup = InlineKeyboardMarkup()
    
    for item in items:
        pid, name, price, r_price, valid, is_sub, stock = item
        
        # Determine Price: Use Reseller Price if user is reseller, otherwise normal price
        final_price = r_price if (is_res and r_price > 0) else price
        
        # Display Text formatting
        validity_txt = f" | ⏳ {valid}d" if valid > 0 else " | ⏳ ∞"
        stock_txt = " (Unltd)" if is_sub else f" (Stock: {stock})"
        
        btn_text = f"{name} - {final_price}tk {validity_txt}{stock_txt}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"buy_{pid}"))
    
    bot.send_message(user_id, msg, reply_markup=markup, parse_mode="Markdown")

def check_purchase(user_id, prod_id, lang):
    is_res = is_reseller_mode(user_id)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Get one item of this type to check details
            cursor.execute("SELECT name FROM products WHERE id=%s", (prod_id,))
            proto = cursor.fetchone()
            if not proto: return
            
            # Find an available item with the same name (FIFO - First In First Out)
            cursor.execute("SELECT id, name, price, reseller_price, data, is_sub FROM products WHERE name=%s LIMIT 1", (proto[0],))
            item = cursor.fetchone()
            
            if not item:
                bot.send_message(user_id, get_str(lang, 'stock_out'))
                return

            pid, name, price, r_price, data, is_sub = item
            
            # Calculate final price
            final_price = r_price if (is_res and r_price > 0) else price
            
            # Check User Balance
            cursor.execute("SELECT balance FROM users WHERE user_id=%s", (user_id,))
            bal = cursor.fetchone()[0]
            
            if bal < final_price:
                bot.send_message(user_id, get_str(lang, 'low_bal'))
                return
            
            # --- SUBSCRIPTION VS NORMAL FLOW ---
            if is_sub == 1:
                # It's a Subscription (like Canva) -> Ask for Gmail
                msg = bot.send_message(user_id, get_str(lang, 'enter_email'))
                bot.register_next_step_handler(msg, process_sub_order, final_price, name, lang)
            else:
                # It's a Normal Item -> Instant Delivery
                process_instant_buy(user_id, pid, final_price, data, name, lang)

def process_sub_order(message, price, name, lang):
    email = message.text
    user_id = message.from_user.id
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Re-check balance to be safe
            cursor.execute("SELECT balance FROM users WHERE user_id=%s", (user_id,))
            bal = cursor.fetchone()[0]
            if bal < price:
                bot.send_message(user_id, get_str(lang, 'low_bal'))
                return
                
            # Deduct Balance
            cursor.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (price, user_id))
            # Log Order (Save Email as Data)
            cursor.execute("INSERT INTO orders (user_id, item_name, price, data, date) VALUES (%s, %s, %s, %s, %s)", 
                           (user_id, name, price, email, str(datetime.date.today())))
            conn.commit()

    bot.send_message(user_id, get_str(lang, 'order_processing'))
    # Notify Admin Immediately
    bot.send_message(ADMIN_ID, f"🔔 **New Subscription Order!**\nUser: {user_id}\nItem: {name}\nPrice: {price}\n📧 **Gmail:** `{email}`", parse_mode="Markdown")

def process_instant_buy(user_id, pid, price, data, name, lang):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (price, user_id))
            cursor.execute("INSERT INTO orders (user_id, item_name, price, data, date) VALUES (%s, %s, %s, %s, %s)", (user_id, name, price, data, str(datetime.date.today())))
            # Delete product from stock
            cursor.execute("DELETE FROM products WHERE id=%s", (pid,))
            conn.commit()
    
    bot.send_message(user_id, get_str(lang, 'success'))
    bot.send_message(user_id, f"{get_str(lang, 'data_here')}\n\n`{data}`", parse_mode="Markdown")
                      # --- ADMIN NEW COMMANDS ---

@bot.message_handler(commands=['genresell'])
def gen_resell(m):
    if m.from_user.id == ADMIN_ID:
        # Generate random ID (R-XXXX) and Password (6 chars)
        rid = "R-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        rpass = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO resellers (resell_id, password) VALUES (%s, %s)", (rid, rpass))
                conn.commit()
        bot.reply_to(m, f"✅ **Reseller Created!**\nID: `{rid}`\nPass: `{rpass}`", parse_mode="Markdown")

@bot.message_handler(commands=['addsub'])
def add_sub(m):
    # Format: /addsub Name|Price|Validity
    if m.from_user.id == ADMIN_ID:
        try:
            n, p, v = m.text.split(' ', 1)[1].split('|')
            # Reseller price is auto-set to 90% of price (You can edit this logic if needed)
            rp = int(int(p) * 0.9) 
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # is_sub=1 marks it as a subscription
                    cursor.execute("INSERT INTO products (name, price, reseller_price, validity, is_sub, data) VALUES (%s, %s, %s, %s, 1, 'Manual')", 
                                   (n.strip(), int(p), rp, int(v)))
                    conn.commit()
            bot.reply_to(m, "✅ Subscription Product Added")
        except: bot.reply_to(m, "Error: Use /addsub Name|Price|Days")

@bot.message_handler(commands=['adddecay'])
def add_decay(m):
    # Format: /adddecay Name|Price|Days|Data
    if m.from_user.id == ADMIN_ID:
        try:
            n, p, v, d = m.text.split(' ', 1)[1].split('|')
            rp = int(int(p) * 0.9)
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # is_sub=0 (Normal), but it has validity, so maintenance_loop will reduce price daily
                    cursor.execute("INSERT INTO products (name, price, reseller_price, validity, is_sub, data, last_update) VALUES (%s, %s, %s, %s, 0, %s, CURRENT_DATE)", 
                                   (n.strip(), int(p), rp, int(v), d.strip()))
                    conn.commit()
            bot.reply_to(m, "✅ Decaying Product Added")
        except: bot.reply_to(m, "Error: Use /adddecay Name|Price|Days|Data")

# --- ORIGINAL HANDLERS (Payment, Coupon, Etc.) ---

def redeem_process(message, lang):
    code = message.text.strip()
    user_id = message.from_user.id
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT amount, uses FROM coupons WHERE code=%s", (code,))
            res = cursor.fetchone()
            if res and res[1] > 0:
                amount = res[0]
                cursor.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount, user_id))
                cursor.execute("UPDATE coupons SET uses=uses-1 WHERE code=%s", (code,))
                conn.commit()
                bot.send_message(user_id, get_str(lang, 'coupon_success', amount=amount))
            else:
                bot.send_message(user_id, get_str(lang, 'coupon_invalid'))

def process_deposit_amount(message, lang):
    try:
        amount = int(message.text)
        txt = get_str(lang, 'pay_instruct', amount=amount, num=PAYMENT_NUM, method=PAYMENT_METHOD)
        msg = bot.send_message(message.chat.id, txt, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_trxid, amount, lang)
    except:
        bot.send_message(message.chat.id, get_str(lang, 'invalid_amount'))

def process_trxid(message, amount, lang):
    trx = message.text
    bot.send_message(ADMIN_ID, f"💰 **Deposit Request:**\nUser: {message.from_user.id}\nAmount: {amount}\nTrxID: `{trx}`", parse_mode="Markdown")
    bot.send_message(message.chat.id, get_str(lang, 'req_sent'))

@bot.message_handler(commands=['addprod'])
def add_prod(m):
    # Standard Product Addition
    if m.from_user.id == ADMIN_ID:
        try:
            n, p, d = m.text.split(' ', 1)[1].split('|')
            rp = int(int(p) * 0.9)
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("INSERT INTO products (name, price, reseller_price, data, is_file) VALUES (%s, %s, %s, %s, 0)", (n.strip(), int(p), rp, d.strip()))
                    conn.commit()
            bot.reply_to(m, "✅ Added")
        except: pass

@bot.message_handler(commands=['addbal'])
def add_bal(m):
    if m.from_user.id == ADMIN_ID:
        try:
            target, am = m.text.split()[1], int(m.text.split()[2])
            uid = int(target) if target.isdigit() else None
            if not uid: 
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT user_id FROM users WHERE username=%s", (target.replace('@',''),))
                        res = cursor.fetchone()
                        if res: uid = res[0]
            if uid:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (am, uid))
                        conn.commit()
                bot.reply_to(m, f"✅ Added {am}tk to {uid}")
                try: bot.send_message(uid, f"🎉 Balance Added: +{am}tk")
                except: pass
        except: bot.reply_to(m, "Error")

@bot.message_handler(commands=['cast'])
def broadcast(message):
    if message.from_user.id == ADMIN_ID:
        msg = message.text.replace('/cast ', '')
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users")
                users = cursor.fetchall()
        for u in users:
            try: bot.send_message(u[0], msg)
            except: pass
        bot.reply_to(message, "✅ Done")

print("Bot Running with Advanced Features...")
keep_alive()
bot.polling()
      
