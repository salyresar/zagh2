import os, logging, random, html, json
from threading import Thread
from flask import Flask
import pyarabic.araby as araby
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

# --- الإعدادات الأساسية ---
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = 7271805464 
CHANNELS = ["@eliteseceret", "@worddecor"] 
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

# --- وظائف التحقق ---
def is_banned(user_id):
    try: return ban_sheet.find(str(user_id)) is not None
    except: return False

def add_user(user_id):
    try:
        if not users_sheet.find(str(user_id)):
            users_sheet.append_row([str(user_id)])
            return True 
    except: pass
    return False

async def check_sub(user_id, context):
    for channel in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False, channel
        except Exception as e:
            logging.error(f"Error checking {channel}: {e}")
            continue
    return True, None

# --- محرك الزخرفة (13 نمط) ---
def get_all_styles(text):
    text_clean = araby.strip_tashkeel(text)
    tash = ['َ', 'ُ', 'ِ', 'ْ', 'ّ', 'ً', 'ٌ', 'ٍ']
    def d(t, p=0.4): return "".join([c + random.choice(tash) if c != ' ' and random.random() < p else c for c in t])
    return {
        's1': f"۞ {d(text_clean, 0.3)} ۞", 's2': f"﴿ {text_clean} ﴾",
        's3': f"★彡 {text_clean} 彡★", 's4': f"{text_clean.replace('', 'ـ')[1:-1]}",
        's5': f"✨ {d(text_clean, 0.6)} ✨", 's6': f"👑 {text_clean} 👑",
        's7': f"⟦ {text_clean} ⟧", 's8': f"『 {text_clean} 』",
        's9': f"╰ {text_clean} ╮", 's10': f"⚡️ {d(text_clean, 0.8)} ⚡️",
        's11': f"【{text_clean}】", 's12': f"💎 ⁞ {text_clean} ⁞ 💎",
        's13': f"{d(text_clean, 0.9)}"
    }

# --- لوحة التحكم المطورة ---
def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 إحصائيات", callback_data='adm_stats'), InlineKeyboardButton("📢 إذاعة", callback_data='adm_bc')],
        [InlineKeyboardButton("📋 قائمة IDs", callback_data='adm_list'), InlineKeyboardButton("🔍 فحص عضو", callback_data='adm_check')],
        [InlineKeyboardButton("🚫 حظر", callback_data='adm_ban'), InlineKeyboardButton("🔓 فك حظر", callback_data='adm_unban')],
        [InlineKeyboardButton("❌ إغلاق", callback_data='adm_close')]
    ])

# --- سيرفر Flask ---
flask_app = Flask('')
@flask_app.route('/')
def home(): return "Bot Online"
def keep_alive(): Thread(target=lambda: flask_app.run(host='0.0.0.0', port=8080)).start()

# --- المعالجات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    if is_banned(uid): return
    if add_user(uid):
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🆕 **انضمام عضو جديد:**\n\n👤: {user.full_name}\n🆔: <code>{uid}</code>\n🔗: @{user.username}", parse_mode=ParseMode.HTML)
    
    is_sub, channel = await check_sub(uid, context)
    if not is_sub:
        kb = [[InlineKeyboardButton("اشتراك ✅", url=f"https://t.me/{channel[1:]}")]]
        return await update.message.reply_text(f"⚠️ يجب الاشتراك في {channel} أولاً.", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("🖋 **مرحباً بك في حبر الأمة.**\nأرسل النص الآن للزخرفة.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    await query.answer()

    if query.data.startswith('adm_'):
        if uid != ADMIN_ID: return
        all_ids = users_sheet.col_values(1)
        
        if query.data == 'adm_stats':
            total = len(all_ids)
            last_id = all_ids[-1] if total > 0 else "N/A"
            msg = (f"📊 **إحصائيات البوت الحالية:**\n\n"
                   f"👥 إجمالي الأعضاء: `{total}`\n"
                   f"🟢 الأعضاء النشطين: `{total}`\n"
                   f"🆔 آخر ID انضم: `{last_id}`\n"
                   f"📡 حالة السيرفر: `Live` ✅")
            await query.edit_message_text(msg, reply_markup=admin_kb(), parse_mode=ParseMode.HTML)
        
        elif query.data == 'adm_list':
            list_msg = "📋 **آخر 15 معرف (ID) مسجل:**\n\n" + "\n".join([f"`{i}`" for i in all_ids[-15:]])
            await query.edit_message_text(list_msg, reply_markup=admin_kb(), parse_mode=ParseMode.HTML)

        elif query.data == 'adm_check':
            await query.edit_message_text("🔍 أرسل الـ ID المراد فحصه:")
            context.user_data['step'] = 'check'

        elif query.data == 'adm_bc':
            await query.edit_message_text("📝 أرسل رسالة الإذاعة:")
            context.user_data['step'] = 'bc'

        elif query.data == 'adm_ban':
            await query.edit_message_text("🚫 أرسل الـ ID للحظر:")
            context.user_data['step'] = 'ban'

        elif query.data == 'adm_unban':
            await query.edit_message_text("🔓 أرسل الـ ID لفك الحظر:")
            context.user_data['step'] = 'unban'

        elif query.data == 'adm_close': await query.delete_message()
    
    elif query.data.startswith('s'):
        txt = context.user_data.get('last_txt', "حبر الأمة")
        styles = get_all_styles(txt)
        await query.edit_message_text(f"✅ النتيجة:\n\n<code>{styles.get(query.data)}</code>", parse_mode=ParseMode.HTML)

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    step = context.user_data.get('step')

    if uid == ADMIN_ID and step:
        target = update.message.text
        if step == 'bc':
            users = users_sheet.col_values(1)
            for u in users:
                try: await context.bot.send_message(u, target)
                except: pass
            await update.message.reply_text(f"✅ تم الإرسال لـ {len(users)} مستخدم.")
        elif step == 'check':
            found = users_sheet.find(target)
            banned = ban_sheet.find(target)
            res = f"🔍 **تقرير العضو:** `{target}`\n\n"
            res += "✅ موجود في القاعدة" if found else "❌ غير موجود"
            res += "\n🚫 حالة الحظر: محظور" if banned else "\n🟢 حالة الحظر: غير محظور"
            await update.message.reply_text(res, parse_mode=ParseMode.HTML)
        elif step == 'ban':
            if not ban_sheet.find(target): ban_sheet.append_row([target])
            await update.message.reply_text(f"🚫 تم حظر {target}")
        elif step == 'unban':
            try:
                cell = ban_sheet.find(target)
                ban_sheet.delete_rows(cell.row)
                await update.message.reply_text(f"🔓 فك حظر {target}")
            except: await update.message.reply_text("المستخدم ليس محظوراً.")
        context.user_data['step'] = None
        return

    is_sub, ch = await check_sub(uid, context)
    if not is_sub: return await update.message.reply_text(f"⚠️ اشترك في {ch}")

    context.user_data['last_txt'] = update.message.text
    kb = [
        [InlineKeyboardButton("۞ إسلامية", callback_data='s1'), InlineKeyboardButton("﴿ قرآنية ﴾", callback_data='s2')],
        [InlineKeyboardButton("★ نجوم", callback_data='s3'), InlineKeyboardButton("ـ كشيدة ـ", callback_data='s4')],
        [InlineKeyboardButton("✨ بريق", callback_data='s5'), InlineKeyboardButton("👑 ملكي", callback_data='s6')],
        [InlineKeyboardButton("⟦ أقواس ⟧", callback_data='s7'), InlineKeyboardButton("『 فخامة 』", callback_data='s8')],
        [InlineKeyboardButton("╰ مائل ╮", callback_data='s9'), InlineKeyboardButton("⚡️ رعد", callback_data='s10')],
        [InlineKeyboardButton("【 عريض 】", callback_data='s11'), InlineKeyboardButton("💎 جوهرة", callback_data='s12')],
        [InlineKeyboardButton("✍️ تشكيل مكثف", callback_data='s13')]
    ]
    await update.message.reply_text("⚙️ **اختر نمط الزخرفة:**", reply_markup=InlineKeyboardMarkup(kb))

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('admin', lambda u, c: u.message.reply_text("🛠 لوحة التحكم:", reply_markup=admin_kb()) if u.effective_user.id == ADMIN_ID else None))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.run_polling()
