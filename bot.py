import os, logging, random, html, json
from threading import Thread
from flask import Flask
import pyarabic.araby as araby
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

# --- الإعدادات ---
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = 7271805464 
CHANNEL_ID = "@eliteseceret" # استبدله بمعرف قناتك
SHEET_ID = "1RTCF6wWNrmtIWkLXYUPgVvB3HU12W8vfMLh0bxMtETg"

logging.basicConfig(level=logging.INFO)

# --- ربط Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ.get('GOOGLE_SHEETS_JSON'))
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
gc = gspread.authorize(creds)
db = gc.open_by_key(SHEET_ID)
users_sheet = db.worksheet("users") 
ban_sheet = db.worksheet("ban")

# --- وظائف الحماية والبيانات ---
def is_banned(user_id):
    return ban_sheet.find(str(user_id)) is not None

def add_user(user_id):
    if not users_sheet.find(str(user_id)):
        users_sheet.append_row([str(user_id)])

async def check_sub(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except: return True 

# --- سيرفر التشغيل الدائم ---
flask_app = Flask('')
@flask_app.route('/')
def home(): return "Bot Online"
def keep_alive(): Thread(target=lambda: flask_app.run(host='0.0.0.0', port=8080)).start()

# --- لوحة التحكم (الأزرار) ---
def admin_kb():
    keyboard = [
        [InlineKeyboardButton("📊 عدد الأعضاء", callback_data='st_count'), InlineKeyboardButton("📢 إذاعة للكل", callback_data='st_bc')],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data='st_ban'), InlineKeyboardButton("🔓 فك حظر", callback_data='st_unban')],
        [InlineKeyboardButton("❌ إغلاق اللوحة", callback_data='st_close')]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- محرك الزخرفة ---
def get_styles(text):
    tash = ['َ', 'ُ', 'ِ', 'ْ', 'ّ', 'ً', 'ٌ', 'ٍ']
    def dec(t, d=0.5): return "".join([c + random.choice(tash) if c != ' ' and random.random() < d else c for c in t])
    return {
        's1': f"۞ {dec(text, 0.4)} ۞", 's2': dec(text, 0.9), 's3': f"﴿ {text} ﴾",
        's4': f"★彡 {text} 彡★", 's5': f"{text.replace('', 'ـ')[1:-1]}", 
        's6': f"✨ {dec(text, 0.7)} ✨", 's7': f"👑 ⚜️ {text} ⚜️ 👑", 's8': f"⟦ {text} ⟧"
    }

# --- المعالجات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    add_user(uid)
    if not await check_sub(uid, context):
        return await update.message.reply_text(f"⚠️ يجب الاشتراك بالقناة أولاً:\n{CHANNEL_ID}", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("إضغط هنا للاشتراك", url=f"https://t.me/{CHANNEL_ID[1:]}")]]))
    await update.message.reply_text("<b>أهلاً بك في بوت زخرفة حبر الأمة 🖋️</b>\nأرسل النص الآن.", parse_mode=ParseMode.HTML)

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("🛠 **لوحة تحكم المدير:**", reply_markup=admin_kb())

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = update.effective_user.id
    await q.answer()

    if q.data.startswith('st_'): # أوامر الأدمن
        if uid != ADMIN_ID: return
        if q.data == 'st_count':
            count = len(users_sheet.col_values(1))
            await q.edit_message_text(f"📊 إجمالي عدد المشتركين: {count}", reply_markup=admin_kb())
        elif q.data == 'st_bc':
            await q.edit_message_text("📝 أرسل رسالة الإذاعة الآن:")
            context.user_data['state'] = 'bc'
        elif q.data == 'st_ban':
            await q.edit_message_text("🆔 أرسل الـ ID المراد حظره:")
            context.user_data['state'] = 'ban'
        elif q.data == 'st_close':
            await q.delete_message()
    
    elif q.data.startswith('s'): # أوامر الزخرفة
        styles = get_styles(context.user_data.get('txt', "حبر الأمة"))
        await q.edit_message_text(f"<code>{styles.get(q.data)}</code>", parse_mode=ParseMode.HTML)

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    
    state = context.user_data.get('state')
    if uid == ADMIN_ID and state:
        if state == 'bc':
            for u in users_sheet.col_values(1):
                try: await context.bot.send_message(u, update.message.text)
                except: pass
            await update.message.reply_text("✅ تمت الإذاعة.")
        elif state == 'ban':
            ban_sheet.append_row([update.message.text])
            await update.message.reply_text("🚫 تم الحظر.")
        context.user_data['state'] = None
        return

    # عرض أزرار الزخرفة
    context.user_data['txt'] = araby.strip_tashkeel(update.message.text)
    kb = [
        [InlineKeyboardButton("زخرفة إسلامية", callback_data='s1'), InlineKeyboardButton("تشكيل", callback_data='s2')],
        [InlineKeyboardButton("مصحف", callback_data='s3'), InlineKeyboardButton("نجوم", callback_data='s4')],
        [InlineKeyboardButton("كشيدة", callback_data='s5'), InlineKeyboardButton("فخمة", callback_data='s6')]
    ]
    await update.message.reply_text("اختر النمط:", reply_markup=InlineKeyboardMarkup(kb))

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('admin', admin_cmd))
    app.add_handler(CallbackQueryHandler(query_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), msg_handler))

    app.run_polling()

