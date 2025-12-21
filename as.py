import telebot
import datetime
from flask import Flask
from threading import Thread
import sqlite3
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- কনফিগারেশন ---
BOT_TOKEN = '8036869041:AAGiSBZ9OrWsiO1EGF6wXiZ4GZ8TYEb9dOQ' 
ADMIN_ID = 6250222523
ADMIN_USERNAME = "@darkorb1t" 

PAYMENT_NUM = "01611026722" 
PAYMENT_METHOD = "bKash (Send Money)"
REFER_BONUS = 1 

bot = telebot.TeleBot(BOT_TOKEN)
db_lock = threading.Lock()

# --- 24/7 Server Code ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------

# --- ১. ভাষা ডাটাবেস (Language Dictionary) ---
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
        'coupon_invalid': "❌ ভুল কোড বা মেয়াদ শেষ।"
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
        'coupon_invalid': "❌ Invalid or Expired Code."
    },
    'ar': {'welcome': "أهلاً {name}!", 'shop': "🛍️ المتجر", 'profile': "👤 الملف", 'add_money': "💸 شحن", 'orders': "📦 طلباتي", 'coupon': "🎁 قسيمة", 'refer': "🗣️ دعوة", 'support': "📞 الدعم", 'lang_btn': "🌐 اللغة", 'shop_empty': "فارغ", 'shop_title': "منتجات", 'buy_btn': "شراء", 'stock': "مخزون", 'unlimited': "غير محدود", 'profile_title': "ملف", 'balance': "رصيد", 'no_orders': "لا يوجد", 'order_hist': "سجل", 'processing': "...", 'expired': "منتهي", 'low_bal': "رصيد منخفض", 'success': "تم", 'data_here': "بيانات:", 'file_cap': "ملف", 'stock_out': "نفذ", 'ask_amount': "كم المبلغ؟", 'invalid_amount': "أرقام فقط", 'pay_instruct': "أرسل {amount} إلى `{num}`. TrxID?", 'req_sent': "تم الإرسال", 'deposit_received': "+{amount}", 'deposit_rejected': "مرفوض", 'refer_msg': "رابط: `{link}`", 'coupon_ask': "كود:", 'coupon_success': "+{amount}", 'coupon_invalid': "خطأ"},
    'hi': {'welcome': "नमस्ते {name}!", 'shop': "🛍️ दुकान", 'profile': "👤 प्रोफ़ाइल", 'add_money': "💸 पैसे डालें", 'orders': "📦 ऑर्डर", 'coupon': "🎁 कूपन", 'refer': "🗣️ रेफर", 'support': "📞 मदद", 'lang_btn': "🌐 भाषा", 'shop_empty': "खाली", 'shop_title': "उत्पाद", 'buy_btn': "खरीदें", 'stock': "स्टॉक", 'unlimited': "असीमित", 'profile_title': "प्रोफ़ाइल", 'balance': "बैलेंस", 'no_orders': "कोई नहीं", 'order_hist': "इतिहास", 'processing': "...", 'expired': "समाप्त", 'low_bal': "कम बैलेंस", 'success': "सफल", 'data_here': "डेटा:", 'file_cap': "फ़ाइल", 'stock_out': "स्टॉक खत्म", 'ask_amount': "राशि?", 'invalid_amount': "संख्या", 'pay_instruct': "{amount} भेजें `{num}` पर. TrxID?", 'req_sent': "भेजा गया", 'deposit_received': "+{amount}", 'deposit_rejected': "अस्वीकृत", 'refer_msg': "लिंक: `{link}`", 'coupon_ask': "कोड:", 'coupon_success': "+{amount}", 'coupon_invalid': "गलत"},
    'es': {'welcome': "Hola {name}!", 'shop': "🛍️ Tienda", 'profile': "👤 Perfil", 'add_money': "💸 Saldo", 'orders': "📦 Pedidos", 'coupon': "🎁 Cupón", 'refer': "🗣️ Referir", 'support': "📞 Soporte", 'lang_btn': "🌐 Idioma", 'shop_empty': "Vacía", 'shop_title': "Productos", 'buy_btn': "Comprar", 'stock': "Stock", 'unlimited': "Ilimitado", 'profile_title': "Perfil", 'balance': "Saldo", 'no_orders': "Nada", 'order_hist': "Historial", 'processing': "...", 'expired': "Expirado", 'low_bal': "Saldo bajo", 'success': "Éxito", 'data_here': "Datos:", 'file_cap': "Archivo", 'stock_out': "Sin stock", 'ask_amount': "¿Monto?", 'invalid_amount': "Números", 'pay_instruct': "Envía {amount} a `{num}`. TrxID?", 'req_sent': "Enviado", 'deposit_received': "+{amount}", 'deposit_rejected': "Rechazado", 'refer_msg': "Link: `{link}`", 'coupon_ask': "Código:", 'coupon_success': "+{amount}", 'coupon_invalid': "Inválido"},
    'fr': {'welcome': "Bonjour {name}!", 'shop': "🛍️ Boutique", 'profile': "👤 Profil", 'add_money': "💸 Ajouter", 'orders': "📦 Commandes", 'coupon': "🎁 Coupon", 'refer': "🗣️ Référer", 'support': "📞 Support", 'lang_btn': "🌐 Langue", 'shop_empty': "Vide", 'shop_title': "Produits", 'buy_btn': "Acheter", 'stock': "Stock", 'unlimited': "Illimité", 'profile_title': "Profil", 'balance': "Solde", 'no_orders': "Rien", 'order_hist': "Historique", 'processing': "...", 'expired': "Expiré", 'low_bal': "Solde bas", 'success': "Succès", 'data_here': "Données:", 'file_cap': "Fichier", 'stock_out': "Rupture", 'ask_amount': "Combien?", 'invalid_amount': "Nombres", 'pay_instruct': "Envoyez {amount} à `{num}`. TrxID?", 'req_sent': "Envoyé", 'deposit_received': "+{amount}", 'deposit_rejected': "Rejeté", 'refer_msg': "Lien: `{link}`", 'coupon_ask': "Code:", 'coupon_success': "+{amount}", 'coupon_invalid': "Invalide"},
    'ru': {'welcome': "Привет {name}!", 'shop': "🛍️ Магазин", 'profile': "👤 Профиль", 'add_money': "💸 Пополнить", 'orders': "📦 Заказы", 'coupon': "🎁 Купон", 'refer': "🗣️ Реф", 'support': "📞 Поддержка", 'lang_btn': "🌐 Язык", 'shop_empty': "Пусто", 'shop_title': "Товары", 'buy_btn': "Купить", 'stock': "Наличие", 'unlimited': "Безлим", 'profile_title': "Профиль", 'balance': "Баланс", 'no_orders': "Нет", 'order_hist': "История", 'processing': "...", 'expired': "Истек", 'low_bal': "Мало средств", 'success': "Успешно", 'data_here': "Данные:", 'file_cap': "Файл", 'stock_out': "Нет", 'ask_amount': "Сумма?", 'invalid_amount': "Цифры", 'pay_instruct': "{amount} на `{num}`. TrxID?", 'req_sent': "Отправлено", 'deposit_received': "+{amount}", 'deposit_rejected': "Отказ", 'refer_msg': "Ссылка: `{link}`", 'coupon_ask': "Код:", 'coupon_success': "+{amount}", 'coupon_invalid': "Ошибка"},
    'pt': {'welcome': "Olá {name}!", 'shop': "🛍️ Loja", 'profile': "👤 Perfil", 'add_money': "💸 Adicionar", 'orders': "📦 Pedidos", 'coupon': "🎁 Cupom", 'refer': "🗣️ Referir", 'support': "📞 Suporte", 'lang_btn': "🌐 Idioma", 'shop_empty': "Vazio", 'shop_title': "Produtos", 'buy_btn': "Comprar", 'stock': "Estoque", 'unlimited': "Ilimitado", 'profile_title': "Perfil", 'balance': "Saldo", 'no_orders': "Nada", 'order_hist': "Histórico", 'processing': "...", 'expired': "Expirado", 'low_bal': "Saldo baixo", 'success': "Sucesso", 'data_here': "Dados:", 'file_cap': "Arquivo", 'stock_out': "Sem estoque", 'ask_amount': "Quanto?", 'invalid_amount': "Números", 'pay_instruct': "Envie {amount} para `{num}`. TrxID?", 'req_sent': "Enviado", 'deposit_received': "+{amount}", 'deposit_rejected': "Rejeitado", 'refer_msg': "Link: `{link}`", 'coupon_ask': "Código:", 'coupon_success': "+{amount}", 'coupon_invalid': "Inválido"},
    'id': {'welcome': "Halo {name}!", 'shop': "🛍️ Toko", 'profile': "👤 Profil", 'add_money': "💸 Tambah", 'orders': "📦 Pesanan", 'coupon': "🎁 Kupon", 'refer': "🗣️ Referral", 'support': "📞 Dukungan", 'lang_btn': "🌐 Bahasa", 'shop_empty': "Kosong", 'shop_title': "Produk", 'buy_btn': "Beli", 'stock': "Stok", 'unlimited': "Tanpa Batas", 'profile_title': "Profil", 'balance': "Saldo", 'no_orders': "Kosong", 'order_hist': "Riwayat", 'processing': "...", 'expired': "Kadaluarsa", 'low_bal': "Saldo Rendah", 'success': "Sukses", 'data_here': "Data:", 'file_cap': "File", 'stock_out': "Habis", 'ask_amount': "Berapa?", 'invalid_amount': "Angka", 'pay_instruct': "Kirim {amount} ke `{num}`. TrxID?", 'req_sent': "Terkirim", 'deposit_received': "+{amount}", 'deposit_rejected': "Ditolak", 'refer_msg': "Link: `{link}`", 'coupon_ask': "Kode:", 'coupon_success': "+{amount}", 'coupon_invalid': "Salah"},
    'zh': {'welcome': "您好 {name}!", 'shop': "🛍️ 商店", 'profile': "👤 个人资料", 'add_money': "💸 充值", 'orders': "📦 订单", 'coupon': "🎁 优惠券", 'refer': "🗣️ 推荐", 'support': "📞 支持", 'lang_btn': "🌐 语言", 'shop_empty': "空的", 'shop_title': "产品", 'buy_btn': "购买", 'stock': "库存", 'unlimited': "无限", 'profile_title': "轮廓", 'balance': "余额", 'no_orders': "无订单", 'order_hist': "历史", 'processing': "...", 'expired': "过期", 'low_bal': "余额不足", 'success': "成功", 'data_here': "数据:", 'file_cap': "文件", 'stock_out': "缺货", 'ask_amount': "多少？", 'invalid_amount': "数字", 'pay_instruct': "发送 {amount} 至 `{num}`. TrxID?", 'req_sent': "已发送", 'deposit_received': "+{amount}", 'deposit_rejected': "拒绝", 'refer_msg': "链接: `{link}`", 'coupon_ask': "代码:", 'coupon_success': "+{amount}", 'coupon_invalid': "无效"}
}

# --- ডাটাবেস সেটআপ ---
def get_db_connection():
    conn = sqlite3.connect('shop.db', check_same_thread=False)
    return conn

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, username TEXT, language TEXT DEFAULT 'en')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, data TEXT, price INTEGER, is_file INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_name TEXT, price INTEGER, data TEXT, date TEXT, is_file INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS coupons (code TEXT PRIMARY KEY, amount INTEGER, uses INTEGER)''')
    
    try: cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
    except: pass
    try: cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE products ADD COLUMN is_file INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE orders ADD COLUMN is_file INTEGER DEFAULT 0")
    except: pass
    conn.commit()

# --- হেল্পার ফাংশন ---
def get_lang_code(user_id):
    with db_lock, get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
        res = cursor.fetchone()
        return res[0] if res else 'en'

def get_str(lang, key, **kwargs):
    ld = LANG_DICT.get(lang, LANG_DICT['en'])
    text = ld.get(key, LANG_DICT['en'].get(key, key))
    try:
        return text.format(**kwargs)
    except:
        return text

# ==========================================
#              হ্যান্ডলার
# ==========================================

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        username = message.from_user.username
        
        with db_lock, get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                cursor.execute("INSERT INTO users (user_id, balance, username, language) VALUES (?, 0, ?, 'en')", (user_id, username))
                conn.commit()
                
                parts = message.text.split()
                if len(parts) > 1:
                    try:
                        referrer_id = int(parts[1])
                        if referrer_id != user_id:
                            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (REFER_BONUS, referrer_id))
                            conn.commit()
                            try: bot.send_message(referrer_id, f"🎉 Refer Bonus: +{REFER_BONUS}tk")
                            except: pass
                    except: pass
                
                send_lang_selector(message.chat.id)
                return
            else:
                lang = user_data[0]
                if username:
                    cursor.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
                    conn.commit()

        if user_id == ADMIN_ID:
            bot.send_message(user_id, "👑 **স্বাগতম বস!**\nএডমিন প্যানেল খুলতে /admin লিখুন |", parse_mode="Markdown")

        show_main_menu(user_id, lang, first_name)

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

def show_main_menu(user_id, lang, name):
    txt = get_str(lang, 'welcome', name=name)
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
    bot.send_message(user_id, txt, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        user_id = call.from_user.id
        
        if call.data.startswith("set_lang_"):
            new_lang = call.data.split("_")[2]
            with db_lock, get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET language=? WHERE user_id=?", (new_lang, user_id))
                conn.commit()
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_main_menu(user_id, new_lang, call.from_user.first_name)
            return

        lang = get_lang_code(user_id)

        if call.data == "lang_select":
            send_lang_selector(call.message.chat.id)

        elif call.data == "refer_link":
            link = f"https://t.me/{bot.get_me().username}?start={user_id}"
            bot.send_message(user_id, get_str(lang, 'refer_msg', link=link, amount=REFER_BONUS), parse_mode="Markdown")
            
        elif call.data == "redeem_btn":
            msg = bot.send_message(user_id, get_str(lang, 'coupon_ask'))
            bot.register_next_step_handler(msg, redeem_process, lang)

        # --- ADMIN PANEL ---
        elif call.data == "panel_add":
            if user_id != ADMIN_ID: return
            msg = "➕ Rule:\n`/addprod Name|Price|Data`\n`/bulk Name|Price`\n`/addfile Name|Price`"
            bot.send_message(user_id, msg, parse_mode="Markdown")

        elif call.data == "panel_coupon":
            if user_id != ADMIN_ID: return
            msg = "🎟️ Coupon Rule:\n`/coupon CODE AMOUNT USES`"
            bot.send_message(user_id, msg, parse_mode="Markdown")

        elif call.data == "panel_stock":
            if user_id != ADMIN_ID: return
            with db_lock, get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, COUNT(id), MAX(is_file) FROM products GROUP BY name")
                stocks = cursor.fetchall()
            msg = "📦 Stock:\n" + "\n".join([f"- {i[0]}: {'Unlimited' if i[2] else i[1]}" for i in stocks]) if stocks else "Empty"
            bot.send_message(user_id, msg)
        
        elif call.data == "panel_orders":
            if user_id != ADMIN_ID: return
            with db_lock, get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT item_name, price, user_id FROM orders ORDER BY id DESC LIMIT 10")
                orders = cursor.fetchall()
            msg = "🛒 Sales:\n" + "\n".join([f"- {o[0]} ({o[1]}tk)" for o in orders])
            bot.send_message(user_id, msg)
        
        elif call.data == "panel_cast":
             bot.send_message(user_id, "Rule: `/cast msg`", parse_mode="Markdown")

        elif call.data == "deposit_request":
            msg = bot.send_message(user_id, get_str(lang, 'ask_amount'), parse_mode="Markdown")
            bot.register_next_step_handler(msg, receive_amount_step, lang)

        elif call.data == "shop":
            with db_lock, get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, price, COUNT(id), MAX(is_file) FROM products GROUP BY name, price")
                groups = cursor.fetchall()
                
                if not groups:
                    bot.send_message(user_id, get_str(lang, 'shop_empty'))
                    return

                bot.send_message(user_id, get_str(lang, 'shop_title'), parse_mode="Markdown")
                for group in groups:
                    name, price, stock, is_file = group
                    stk_lbl = get_str(lang, 'unlimited') if is_file == 1 else f"{stock}"
                    
                    cursor.execute("SELECT id FROM products WHERE name=? AND price=? LIMIT 1", (name, price))
                    oid = cursor.fetchone()[0]
                    
                    btn_txt = f"{get_str(lang, 'buy_btn')} ({price}tk)"
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton(btn_txt, callback_data=f"buy_{oid}"))
                    
                    stk_txt = get_str(lang, 'stock')
                    bot.send_message(user_id, f"✨ **{name}**\n📦 {stk_txt}: {stk_lbl} | 💰 {price}tk", reply_markup=markup, parse_mode="Markdown")

        elif call.data == "profile":
            with db_lock, get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                bal = cursor.fetchone()[0]
            
            p_ti = get_str(lang, 'profile_title')
            b_ti = get_str(lang, 'balance')
            bot.send_message(user_id, f"{p_ti}\n🆔 ID: `{user_id}`\n💰 {b_ti}: {bal}tk", parse_mode="Markdown")

        elif call.data == "my_orders":
            with db_lock, get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT item_name, price, data, date, is_file FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 5", (user_id,))
                orders = cursor.fetchall()
            
            if not orders:
                bot.send_message(user_id, get_str(lang, 'no_orders'))
                return
            bot.send_message(user_id, get_str(lang, 'order_hist'), parse_mode="Markdown")
            for o in orders:
                if o[4] == 1:
                    try: bot.send_document(user_id, o[2], caption=f"🛒 {o[0]} ({o[1]}tk)\n📅 {o[3]}")
                    except: bot.send_message(user_id, "File Error")
                else:
                    bot.send_message(user_id, f"🛒 {o[0]} ({o[1]}tk)\n📅 {o[3]}\n📝: `{o[2]}`", parse_mode="Markdown")
            
        elif call.data == "support":
             bot.send_message(user_id, f"📞 {ADMIN_USERNAME}")
             
        elif call.data.startswith("buy_"):
            bot.answer_callback_query(call.id, get_str(lang, 'processing'))
            
            try:
                clicked_id = int(call.data.split("_")[1])
                
                with db_lock, get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name, price FROM products WHERE id=?", (clicked_id,))
                    original = cursor.fetchone()
                    if not original:
                        bot.send_message(user_id, get_str(lang, 'expired'))
                        return
                    name, price = original
                    
                    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                    if cursor.fetchone()[0] < price:
                        bot.send_message(user_id, get_str(lang, 'low_bal'))
                        return
                    
                    cursor.execute("SELECT id, data, is_file FROM products WHERE name=? AND price=? LIMIT 1", (name, price))
                    final_item = cursor.fetchone()
                    
                    if final_item:
                        final_id, content, is_file = final_item
                        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, user_id))
                        if is_file == 0: cursor.execute("DELETE FROM products WHERE id=?", (final_id,))
                        
                        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        cursor.execute("INSERT INTO orders (user_id, item_name, price, data, date, is_file) VALUES (?, ?, ?, ?, ?, ?)", (user_id, name, price, content, today, is_file))
                        conn.commit()
                        
                        bot.send_message(user_id, f"{get_str(lang, 'success')}\n📦 {name}\n💰 -{price}tk")
                        
                        if is_file == 1:
                            try: bot.send_document(user_id, content, caption=get_str(lang, 'file_cap'))
                            except: pass
                        else:
                            bot.send_message(user_id, f"{get_str(lang, 'data_here')}\n`{content}`", parse_mode="Markdown")
                        
                        u_name = call.from_user.username
                        bot.send_message(ADMIN_ID, f"🔔 **Sold:** {name} to @{u_name} ({price}tk)")
                    else:
                        bot.send_message(user_id, get_str(lang, 'stock_out'))

            except Exception as e:
                bot.send_message(user_id, f"Error: {e}")

        elif call.data.startswith("apr_"):
            if user_id != ADMIN_ID: return
            parts = call.data.split("_")
            tid, am = int(parts[1]), int(parts[2])
            
            with db_lock, get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (am, tid))
                conn.commit()
            
            bot.edit_message_text(f"✅ Approved: {am}tk for {tid}", chat_id=ADMIN_ID, message_id=call.message.message_id)
            
            u_lang = get_lang_code(tid)
            try: bot.send_message(tid, get_str(u_lang, 'deposit_received', amount=am))
            except: pass
            
        elif call.data.startswith("rej_"):
            if user_id != ADMIN_ID: return
            tid = int(call.data.split("_")[1])
            bot.edit_message_text(f"❌ Rejected for {tid}", chat_id=ADMIN_ID, message_id=call.message.message_id)
            
            u_lang = get_lang_code(tid)
            try: bot.send_message(tid, get_str(u_lang, 'deposit_rejected'))
            except: pass

    except Exception as e:
        print(f"Callback Error: {e}")

def receive_amount_step(message, lang):
    try:
        amount = int(message.text)
        msg_text = get_str(lang, 'pay_instruct', amount=amount, num=PAYMENT_NUM, method=PAYMENT_METHOD)
        msg = bot.send_message(message.chat.id, msg_text, parse_mode="Markdown")
        bot.register_next_step_handler(msg, receive_trx_step, amount, lang)
    except:
        bot.send_message(message.chat.id, get_str(lang, 'invalid_amount'))

def receive_trx_step(message, amount, lang):
    trx = message.text
    uid = message.from_user.id
    u_tag = f"@{message.from_user.username}" if message.from_user.username else f"ID:{uid}"
    
    admin_msg = f"🔔 **Deposit Req:**\n👤 {u_tag}\n💰 Amt: {amount}\n🧾 Trx: `{trx}`"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Approve", callback_data=f"apr_{uid}_{amount}"), InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}"))
    
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode="Markdown")
    bot.reply_to(message, get_str(lang, 'req_sent'))

def redeem_process(message, lang):
    code = message.text.strip()
    uid = message.from_user.id
    with db_lock, get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT amount, uses FROM coupons WHERE code=?", (code,))
        res = cursor.fetchone()
        if res:
            amt, uses = res
            if uses > 0:
                cursor.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
                if uses == 1: cursor.execute("DELETE FROM coupons WHERE code=?", (code,))
                else: cursor.execute("UPDATE coupons SET uses=uses-1 WHERE code=?", (code,))
                conn.commit()
                bot.reply_to(message, get_str(lang, 'coupon_success', amount=amt))
            else: bot.reply_to(message, get_str(lang, 'coupon_invalid'))
        else: bot.reply_to(message, get_str(lang, 'coupon_invalid'))

@bot.message_handler(commands=['admin', 'panel'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("📦 Stock", callback_data="panel_stock"), InlineKeyboardButton("🛒 Sales", callback_data="panel_orders"))
    markup.add(InlineKeyboardButton("📢 Cast", callback_data="panel_cast"), InlineKeyboardButton("➕ Add Prod", callback_data="panel_add"))
    markup.add(InlineKeyboardButton("🎟️ Coupon", callback_data="panel_coupon"))
    bot.reply_to(message, "🛡️ Admin Panel", reply_markup=markup)

@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
    if message.from_user.id == ADMIN_ID and message.caption and message.caption.startswith('/addfile'):
        try:
            name, price = message.caption.replace('/addfile ', '').split('|')
            with db_lock, get_db_connection() as conn:
                conn.cursor().execute("INSERT INTO products (name, price, data, is_file) VALUES (?, ?, ?, 1)", (name.strip(), int(price), message.document.file_id))
                conn.commit()
            bot.reply_to(message, "✅ File Added")
        except: pass

@bot.message_handler(commands=['bulk'])
def bulk_add(message):
    if message.from_user.id == ADMIN_ID:
        try:
            lines = message.text.replace('/bulk ', '').split('\n')
            name, price = lines[0].split('|')
            with db_lock, get_db_connection() as conn:
                for d in lines[1:]: 
                    if d.strip(): conn.cursor().execute("INSERT INTO products (name, price, data, is_file) VALUES (?, ?, ?, 0)", (name, int(price), d.strip()))
                conn.commit()
            bot.reply_to(message, "✅ Bulk Added")
        except: pass

@bot.message_handler(commands=['addprod'])
def add_prod(m):
    if m.from_user.id == ADMIN_ID:
        try:
            n, p, d = m.text.split(' ', 1)[1].split('|')
            with db_lock, get_db_connection() as conn:
                conn.cursor().execute("INSERT INTO products (name, price, data, is_file) VALUES (?, ?, ?, 0)", (n.strip(), int(p), d.strip()))
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
                with db_lock, get_db_connection() as conn:
                    res = conn.cursor().execute("SELECT user_id FROM users WHERE username=?", (target.replace('@',''),)).fetchone()
                    if res: uid = res[0]
            if uid:
                with db_lock, get_db_connection() as conn:
                    conn.cursor().execute("UPDATE users SET balance=balance+? WHERE user_id=?", (am, uid))
                    conn.commit()
                bot.reply_to(m, f"✅ Added {am}tk to {uid}")
                try: bot.send_message(uid, f"🎉 Balance Added: +{am}tk")
                except: pass
        except: bot.reply_to(m, "Error")

@bot.message_handler(commands=['coupon'])
def create_coupon(message):
    if message.from_user.id == ADMIN_ID:
        try:
            c, a, u = message.text.split()[1:]
            with db_lock, get_db_connection() as conn:
                conn.cursor().execute("INSERT OR REPLACE INTO coupons (code, amount, uses) VALUES (?, ?, ?)", (c, int(a), int(u)))
                conn.commit()
            bot.reply_to(message, "✅ Coupon Added")
        except: pass

@bot.message_handler(commands=['cast'])
def broadcast(message):
    if message.from_user.id == ADMIN_ID:
        msg = message.text.replace('/cast ', '')
        with db_lock, get_db_connection() as conn:
            users = conn.cursor().execute("SELECT user_id FROM users").fetchall()
        for u in users:
            try: bot.send_message(u[0], msg)
            except: pass
        bot.reply_to(message, "✅ Done")

print("Bot Running...")
keep_alive()  #hhhh
bot.polling()
