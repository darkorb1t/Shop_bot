import logging
import psycopg2
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# --- CONFIGURATION ---
TOKEN = '8036869041:AAHiFgQ7dQUjjkGt6W-OwZQ5MXFMM8SeWzM'   # টোকেন বসাও
ADMIN_ID = 6250222523            # অ্যাডমিন আইডি
ADMIN_USERNAME = "darkorb1t"
BKASH_NUMBER = "01611026722"
# Neon.tech Database URL (আপনার URL এখানে বসান)
NEON_DB_URL = "postgres://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require"

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
    return psycopg2.connect(NEON_DB_URL)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, first_name TEXT, lang TEXT, role TEXT, balance INTEGER DEFAULT 0)''')
    # Products (Postgres uses SERIAL instead of AUTOINCREMENT)
    c.execute('''CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, type TEXT, name TEXT, description TEXT, price_cust INTEGER, price_res INTEGER, content TEXT, status TEXT DEFAULT 'unsold')''')
    # Resellers
    c.execute('''CREATE TABLE IF NOT EXISTS resellers (res_id TEXT, password TEXT)''')
    # Sales
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, user_id BIGINT, product_name TEXT, price INTEGER, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Coupons
    c.execute('''CREATE TABLE IF NOT EXISTS coupons (code TEXT, percent INTEGER, limit_count INTEGER, used_count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()
  

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
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=%s", (uid,))
    res = c.fetchone()
    conn.close()
    return res

def create_user(user):
    if not get_user(user.id):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO users (user_id, first_name, lang, role) VALUES (%s, %s, 'BN', 'customer')", (user.id, user.first_name))
        conn.commit()
        conn.close()
      

# --- START & LANG ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user)
    print(f"USER_ID: {user.id}") # Copy for Admin
    
    kb = [[InlineKeyboardButton("English 🇺🇸", callback_data='lang_EN'), InlineKeyboardButton("বাংলা 🇧🇩", callback_data='lang_BN')]]
    await update.message.reply_text("Please select your language / ভাষা নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(kb))
    return SELECT_LANG

async def lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = q.data.split('_')[1]
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, q.from_user.id))
    conn.commit()
    conn.close()
    
    return await ask_role_screen(update, context, lang)

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
        conn.close()
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
            conn.close()
            return MAIN_STATE
        else:
            del context.user_data['awaiting_pass']
            await update.message.reply_text("❌ Login Failed! Try again.") # Simplified text
            conn.close()
            # Ekhane abar role screen e pathano jete pare ba input e
            return await start(update, context) 

    c.execute("SELECT * FROM resellers WHERE res_id=%s", (text,))
    if c.fetchone():
        context.user_data['temp_rid'] = text
        context.user_data['awaiting_pass'] = True
        await update.message.reply_text("🔑 Enter Password:")
        conn.close()
        return RESELLER_INPUT
    else:
        await update.message.reply_text("❌ Invalid ID.")
        conn.close()
        return await start(update, context)
      

# --- MENU & NAVIGATION ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    lang = user[2]
    t = TEXTS[lang]
    btns = t['menu_btns']
    kb = [[InlineKeyboardButton(b, callback_data=f"menu_{i}")] for i, b in enumerate(btns)]
    msg = t['menu_title']
    if update.callback_query: await update.callback_query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else: await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def universal_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    uid = q.from_user.id
    user = get_user(uid)
    lang = user[2]
    t = TEXTS[lang]
    
    conn = get_db_connection()
    c = conn.cursor()

    if d == 'menu_0': # Shop Fix for Postgres
        # FIXED: GROUP BY removed, used DISTINCT ON for Postgres
        c.execute("SELECT DISTINCT ON (name) name, description, price_cust, price_res, type FROM products WHERE status='unsold' OR type='file' OR type='access'")
        prods = c.fetchall()
        
        if not prods:
            await q.message.reply_text(t['shop_empty'])
            conn.close()
            return MAIN_STATE
            
        await q.message.reply_text("🛒 **SHOP ITEMS:**", parse_mode='Markdown')
        for p in prods:
            name, desc, pc, pr, ptype = p
            price = pr if user[3] == 'reseller' else pc
            
            txt = f"📦 **{name}**\n\n📄 {desc}\n💰 Price: {price} Tk"
            kb = [[InlineKeyboardButton(t['buy_btn'].format(price), callback_data=f"buy_{name}")]]
            await context.bot.send_message(uid, txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        conn.close()
        return MAIN_STATE
        
    elif d == 'menu_1': 
        await q.message.reply_text(t['profile'].format(user[1], uid, user[4], user[3]), parse_mode='Markdown')
    elif d == 'menu_2': 
        await q.message.reply_text(t['ask_money'])
        conn.close()
        return INPUT_MONEY
    elif d == 'menu_3': 
        await q.message.reply_text(t['coupon_ask'])
        conn.close()
        return INPUT_COUPON
    elif d == 'menu_4': 
        await q.message.reply_text(f"🤝 Refer Link:\n`https://t.me/{context.bot.username}?start=ref_{uid}`\nBonus: 1 Tk", parse_mode='Markdown')
    elif d == 'menu_5': 
        await q.message.reply_text(t['support'].format(ADMIN_USERNAME))
    
    conn.close()
    return MAIN_STATE
    
  

# --- BUY LOGIC ---
async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    name = q.data.split('_')[1]
    uid = q.from_user.id
    user = get_user(uid)
    lang = user[2]
    t = TEXTS[lang]
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, type, price_cust, price_res, content FROM products WHERE name=%s AND (status='unsold' OR type='file' OR type='access') LIMIT 1", (name,))
    item = c.fetchone()
    
    if not item: 
        conn.close()
        return await q.answer("❌ Stock Ended!", show_alert=True)
    
    pid, ptype, pc, pr, content = item
    base_price = pr if user[3] == 'reseller' else pc
    discount = context.user_data.get('disc', 0)
    final_price = int(base_price - (base_price * discount / 100))
    
    if user[4] < final_price: 
        conn.close()
        return await q.answer(t['insufficient'].format(final_price - user[4]), show_alert=True)
        
    if ptype == 'access':
        context.user_data['buy_data'] = (pid, final_price, name)
        await q.message.reply_text(t['ask_email'])
        conn.close()
        return INPUT_EMAIL
    
    if ptype == 'account':
        c.execute("UPDATE products SET status='sold' WHERE id=%s", (pid,))
        
    c.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s", (final_price, uid))
    c.execute("INSERT INTO sales (user_id, product_name, price) VALUES (%s,%s,%s)", (uid, name, final_price))
    conn.commit()
    conn.close()
    
    if 'disc' in context.user_data: del context.user_data['disc']
    await context.bot.send_message(ADMIN_ID, f"📢 Sold: {name} to {uid}")
    await q.message.reply_text(t['bought'].format(name, content), parse_mode='Markdown') 
  
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
    kb = [[InlineKeyboardButton("✅ Grant", callback_data=f"g_{uid}_{pid}_{cost}"), InlineKeyboardButton("❌ Reject", callback_data=f"f_{uid}")]]
    await context.bot.send_message(ADMIN_ID, f"⚠️ **Access Req**\nUser: {uid}\nItem: {name}\nEmail: `{email}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
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
    
    conn.close()
    return MAIN_STATE
  

# --- UNIVERSAL ADMIN PANEL ---
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    kb = [
        [InlineKeyboardButton("📦 Stock", callback_data='adm_stock'), InlineKeyboardButton("📈 Sales", callback_data='adm_sales')],
        [InlineKeyboardButton("📢 Cast", callback_data='adm_cast'), InlineKeyboardButton("➕ Add Prod", callback_data='adm_add')],
        [InlineKeyboardButton("🎟 Coupon", callback_data='adm_coup'), InlineKeyboardButton("🗑 Delete", callback_data='adm_del')],
        [InlineKeyboardButton("🆔 Reseller Gen", callback_data='adm_res')]
    ]
    msg = "👮 **Admin Panel**\nSelect option:"
    if update.callback_query: await update.callback_query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else: await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    return MAIN_STATE

async def universal_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    
    conn = get_db_connection()
    c = conn.cursor()
    
    if d == 'adm_back':
        conn.close()
        return await admin_start(update, context)

    if d == 'adm_add':
        await q.message.reply_text("📝 **Add Product**\nFormat: `Type|Name|Desc|CustP|ResP|Content`", parse_mode='Markdown')
        conn.close()
        return INPUT_ADMIN_PROD
        
    elif d == 'adm_res':
        res, pas = ''.join(random.choices(string.digits,k=10)), ''.join(random.choices(string.digits,k=8))
        # FIXED: Explicit column names added
        c.execute("INSERT INTO resellers (res_id, password) VALUES (%s,%s)", (res, pas))
        conn.commit()
        await q.message.edit_text(f"✅ **Reseller Created**\nID: `{res}`\nPass: `{pas}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='adm_back')]]), parse_mode='Markdown')
        conn.close()
        return MAIN_STATE
        
    elif d == 'adm_del':
        c.execute("SELECT DISTINCT name FROM products")
        names = c.fetchall()
        kb = [[InlineKeyboardButton(f"❌ {n[0]}", callback_data=f"del_{n[0]}")] for n in names]
        kb.append([InlineKeyboardButton("🔙 Back", callback_data='adm_back')])
        await q.message.edit_text("Select Product to DELETE:", reply_markup=InlineKeyboardMarkup(kb))
        conn.close()
        return MAIN_STATE
        
    elif d == 'adm_stock':
        # FIXED: Added explicit grouping for Postgres compatibility
        c.execute("SELECT name, COUNT(*) FROM products WHERE status='unsold' GROUP BY name")
        rows = c.fetchall()
        msg = "📦 **Stock Report:**\n" + "\n".join([f"- {r[0]}: {r[1]}" for r in rows])
        await q.message.edit_text(msg if rows else "Empty", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='adm_back')]]), parse_mode='Markdown')
        conn.close()
        return MAIN_STATE
        
    elif d == 'adm_sales':
        c.execute("SELECT product_name, price, date FROM sales ORDER BY id DESC LIMIT 10")
        rows = c.fetchall()
        if not rows: msg = "📉 **No Sales Yet**"
        else:
            msg = "📈 **Recent Sales:**\n\n"
            for r in rows:
                date_str = str(r[2]).split('.')[0]
                msg += f"▫️ {r[0]} - {r[1]} Tk ({date_str})\n"
        
        await q.message.edit_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='adm_back')]]), parse_mode='Markdown')
        conn.close()
        return MAIN_STATE
        
    elif d == 'adm_cast':
        await q.message.reply_text("📢 Enter Message to Broadcast:")
        conn.close()
        return INPUT_BROADCAST
        
    elif d == 'adm_coup':
        await q.message.reply_text("🎟 Enter: `CODE | Percent | Limit`", parse_mode='Markdown')
        conn.close()
        return INPUT_ADMIN_COUPON
    
    conn.close()
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
    conn.close() # Close Connection
    
    await update.message.reply_text(f"✅ Added {count} items.")
    return await admin_start(update, context)
    
async def admin_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.callback_query.data.split('_')[1]
    
    conn = get_db_connection() # Added Connection
    c = conn.cursor()
    
    # FIXED: ? -> %s
    c.execute("DELETE FROM products WHERE name=%s", (name,))
    conn.commit()
    conn.close()
    
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
    
    conn.close()
    await update.message.reply_text(f"✅ Sent to {count}.")
    return await admin_start(update, context)
            

async def admin_save_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        p = [x.strip() for x in update.message.text.split('|')]
        
        conn = get_db_connection() # Added Connection
        c = conn.cursor()
        
        # FIXED: ? -> %s
        c.execute("INSERT INTO coupons VALUES (%s,%s,%s,0)", (p[0], int(p[1]), int(p[2])))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ Coupon Created!")
    except: await update.message.reply_text("Error.")
    return await admin_start(update, context)
        

async def admin_deposit_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data
    
    conn = get_db_connection() # Added Connection
    c = conn.cursor()
    
    if d.startswith('ok'):
        _, u, a = d.split('_')
        # FIXED: ? -> %s
        c.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (int(a), int(u)))
        conn.commit()
        await context.bot.send_message(int(u), f"🎉 Balance Added: {a} Tk")
        await update.callback_query.edit_message_text(f"✅ Approved {a} Tk")
        
    elif d.startswith('g'):
        _, u, p, a = d.split('_')
        # FIXED: ? -> %s
        c.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (int(a), int(u)))
        conn.commit()
        await context.bot.send_message(int(u), "✅ Access Granted! Check Email.")
        await update.callback_query.edit_message_text("✅ Granted.")
        
    else: await update.callback_query.edit_message_text("❌ Rejected.")
    
    conn.close() # Close Connection
    
# --- MAIN ---
def main():
    init_db()     # ডাটাবেস তৈরি করবে
    keep_alive()  # ফেক সার্ভার চালাবে
    
    # ... বাকি কোড যেমন আছে তেমনই থাকবে ...
  
    app = Application.builder().token(TOKEN).build()
    menu_h = CallbackQueryHandler(universal_menu_handler, pattern='^menu_')
    admin_h = CallbackQueryHandler(universal_admin_handler, pattern='^adm_')
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_LANG: [CallbackQueryHandler(lang_choice, pattern='^lang_')],
            SELECT_ROLE: [CallbackQueryHandler(ask_role_screen, pattern='^back_'), CallbackQueryHandler(role_handler, pattern='^role_')],
            RESELLER_INPUT: [MessageHandler(filters.TEXT, reseller_input)],
            MAIN_STATE: [menu_h, admin_h, CallbackQueryHandler(buy_handler, pattern='^buy_'), CallbackQueryHandler(admin_delete_confirm, pattern='^del_')],
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
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_deposit_access, pattern='^(ok|no|g|f)_'))
    print("Bot Running...")
    app.run_polling()

if __name__ == '__main__':
    main()
