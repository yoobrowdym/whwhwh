#!/usr/bin/env python3
"""
ربات بازی داستانساز خنده‌دار
ساخته شده با عشق برای دوستان 😄
"""
import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= تنظیمات =================
TOKEN = os.environ.get("8041384292:AAFgB5WqXN3iCMqMIst_jSqqVlCk8o_24l8")  # جایگزین کن با توکن واقعی
QUESTIONS = [
    "چه کسی؟",
    "با چه کسی؟",
    "چه زمانی؟",
    "کجا؟",
    "چه کار می‌کردند؟"
]
DEFAULT_ANSWERS = [
    "یک آدم عجیب",
    "با جیش عمو",
    "تو یه شب مهتابی",
    "تو دستشویی فرودگاه",
    "داشتند لواشک می‌خوردند"
]

# ================= ذخیره اطلاعات =================
class GameManager:
    def __init__(self):
        self.games = {}
        self.user_states = {}
    
    def create_room(self, chat_id, creator_id, creator_name):
        room_id = f"{chat_id}_{int(datetime.now().timestamp())}"
        self.games[room_id] = {
            'chat_id': chat_id,
            'creator': creator_id,
            'players': [creator_id],
            'usernames': [creator_name],
            'answers': {},
            'status': 'waiting',
            'current_question': 0,
            'message_id': None
        }
        return room_id
    
    def join_room(self, room_id, user_id, username):
        if room_id in self.games:
            if user_id not in self.games[room_id]['players']:
                self.games[room_id]['players'].append(user_id)
                self.games[room_id]['usernames'].append(username)
                return True
        return False
    
    def get_room_by_code(self, code):
        for room_id in self.games:
            if room_id.endswith(code):
                return room_id
        return None

game_manager = GameManager()

# ================= لاگ کردن =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================= دستورات =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع کار با ربات"""
    user = update.effective_user
    
    if context.args:
        # پیوستن به اتاق از طریق لینک
        join_code = context.args[0].replace("join_", "")
        room_id = game_manager.get_room_by_code(join_code)
        
        if room_id:
            if game_manager.join_room(room_id, user.id, user.first_name):
                await update.message.reply_text(
                    f"✅ به اتاق پیوستی!\n"
                    f"کد اتاق: `{join_code}`\n"
                    f"منتظر شروع بازی باش...",
                    parse_mode='Markdown'
                )
                return
        else:
            await update.message.reply_text("❌ اتاق پیدا نشد یا بازی شروع شده!")
            return
    
    # نمایش منوی اصلی
    keyboard = [
        [InlineKeyboardButton("🎮 ساخت اتاق جدید", callback_data="new_room")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
    🙋‍♂️ سلام {user.first_name}!
    🎲 **به بازی داستانساز خنده‌دار خوش اومدی**
    
    🎯 **قوانین ساده:**
    ۱. یه اتاق می‌سازی
    ۲. لینک رو به دوستات می‌فرستی
    ۳. هرکس به ۵ سوال جواب می‌ده
    ۴. ربات داستان‌های خنده‌دار می‌سازه!
    
    👥 **تعداد بازیکنان:** ۳ تا ۱۰ نفر
    ⏱ **زمان هر سوال:** ۲ دقیقه
    
    📌 برای شروع، دکمه زیر رو بزن:
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def new_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ساخت اتاق جدید"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    chat_id = query.message.chat_id
    
    room_id = game_manager.create_room(chat_id, user.id, user.first_name)
    room_code = room_id[-6:]
    
    # ذخیره ID پیام برای آپدیت بعدی
    game_manager.games[room_id]['message_id'] = query.message.message_id
    
    # ساخت دکمه‌ها
    join_url = f"https://t.me/{context.bot.username}?start=join_{room_code}"
    keyboard = [
        [InlineKeyboardButton("🔗 لینک پیوستن", url=join_url)],
        [InlineKeyboardButton("▶️ شروع بازی", callback_data=f"start_{room_id}")],
        [InlineKeyboardButton("🚪 بستن اتاق", callback_data=f"close_{room_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # متن اتاق
    room_text = f"""
    🏠 **اتاق بازی ساخته شد!**
    
    🔑 کد اتاق: `{room_code}`
    
    👥 بازیکنان (۱/{10}):
    • {user.first_name}
    
    📢 لینک بالا رو برای دوستات بفرست تا بیان تو بازی!
    
    ⚠️ حداقل ۳ نفر برای شروع لازمه.
    """
    
    await query.edit_message_text(room_text, reply_markup=reply_markup, parse_mode='Markdown')

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع بازی"""
    query = update.callback_query
    await query.answer()
    
    room_id = query.data.replace("start_", "")
    
    if room_id not in game_manager.games:
        await query.answer("❌ اتاق پیدا نشد!", show_alert=True)
        return
    
    room = game_manager.games[room_id]
    
    # چک کردن تعداد بازیکنان
    if len(room['players']) < 3:
        await query.answer("🚫 حداقل ۳ نفر لازمه!", show_alert=True)
        return
    
    room['status'] = 'playing'
    
    # اطلاع در گروه
    await query.edit_message_text(
        f"🎮 **بازی شروع شد!**\n\n"
        f"به {len(room['players'])} نفر پیام خصوصی فرستاده میشه...\n"
        f"به ۵ سوال جواب بدید! ⏱",
        parse_mode='Markdown'
    )
    
    # شروع پرسش سوالات
    await ask_question(room_id, 0, context)

async def ask_question(room_id: str, q_index: int, context: ContextTypes.DEFAULT_TYPE):
    """پرسش یک سوال به همه بازیکنان"""
    room = game_manager.games[room_id]
    question = QUESTIONS[q_index]
    
    # پرسش از هر بازیکن
    for player_id in room['players']:
        # ذخیره وضعیت کاربر
        game_manager.user_states[player_id] = {
            'room_id': room_id,
            'question': q_index,
            'answered': False
        }
        
        # ارسال سوال به کاربر
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"📝 **سوال {q_index + 1} از ۵**\n\n"
                     f"❓ {question}\n\n"
                     f"💡 جوابت رو همینجا بنویس...\n"
                     f"⏱ وقت داری تا ۲ دقیقه دیگه",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"خطا در ارسال به کاربر {player_id}: {e}")
    
    # تنظیم تایمر
    context.job_queue.run_once(
        timeout_handler,
        120,  # ۲ دقیقه
        data={'room_id': room_id, 'q_index': q_index},
        name=f"timeout_{room_id}_{q_index}"
    )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت جواب از کاربر"""
    user_id = update.effective_user.id
    answer_text = update.message.text.strip()
    
    if user_id not in game_manager.user_states:
        await update.message.reply_text("❌ الان نوبت تو نیست یا بازی تموم شده!")
        return
    
    state = game_manager.user_states[user_id]
    room_id = state['room_id']
    
    if room_id not in game_manager.games:
        await update.message.reply_text("❌ اتاق بازی پیدا نشد!")
        return
    
    room = game_manager.games[room_id]
    
    # ذخیره جواب
    if str(user_id) not in room['answers']:
        room['answers'][str(user_id)] = {}
    
    room['answers'][str(user_id)][QUESTIONS[state['question']]] = answer_text
    state['answered'] = True
    
    await update.message.reply_text("✅ جوابت ذخیره شد! منتظر بقیه...")
    
    # چک کن همه جواب دادن؟
    all_answered = True
    for pid in room['players']:
        if pid in game_manager.user_states:
            if not game_manager.user_states[pid]['answered']:
                all_answered = False
                break
    
    if all_answered:
        # همه جواب دادن، برو سوال بعدی
        next_q = state['question'] + 1
        if next_q < len(QUESTIONS):
            room['current_question'] = next_q
            await ask_question(room_id, next_q, context)
        else:
            # همه سوالات تموم شد
            await finalize_game(room_id, context)

async def timeout_handler(context: ContextTypes.DEFAULT_TYPE):
    """وقت تمام شدن زمان سوال"""
    job = context.job
    room_id = job.data['room_id']
    q_index = job.data['q_index']
    
    if room_id not in game_manager.games:
        return
    
    room = game_manager.games[room_id]
    
    # برای کسایی که جواب ندادن، جواب پیش‌فرض بذار
    for player_id in room['players']:
        if str(player_id) not in room['answers']:
            room['answers'][str(player_id)] = {}
        
        if QUESTIONS[q_index] not in room['answers'][str(player_id)]:
            room['answers'][str(player_id)][QUESTIONS[q_index]] = DEFAULT_ANSWERS[q_index]
    
    # برو سوال بعدی
    next_q = q_index + 1
    if next_q < len(QUESTIONS):
        room['current_question'] = next_q
        await ask_question(room_id, next_q, context)
    else:
        await finalize_game(room_id, context)

async def finalize_game(room_id: str, context: ContextTypes.DEFAULT_TYPE):
    """پردازش نهایی و ساخت داستان‌ها"""
    room = game_manager.games[room_id]
    players = room['players']
    usernames = room['usernames']
    answers = room['answers']
    
    n = len(players)  # تعداد بازیکنان
    stories = []
    
    # ساخت داستان‌ها
    for i in range(n):
        story_parts = []
        for q_index, question in enumerate(QUESTIONS):
            player_index = (i + q_index) % n
            player_id = str(players[player_index])
            answer = answers.get(player_id, {}).get(question, DEFAULT_ANSWERS[q_index])
            story_parts.append(answer)
        
        story = " ".join(story_parts)
        stories.append(f"**داستان {i+1}:** {story}")
    
    # نمایش نتایج
    result_text = "🎉 **نتیجه نهایی بازی!** 🎉\n\n"
    result_text += "\n\n".join(stories)
    result_text += f"\n\n👥 **بازیکنان:** {', '.join(usernames)}"
    result_text += f"\n\n😂 حتماً screenshots بگیرین!"
    
    # ارسال به گروه
    await context.bot.send_message(
        chat_id=room['chat_id'],
        text=result_text,
        parse_mode='Markdown'
    )
    
    # پاک کردن اتاق
    if room_id in game_manager.games:
        del game_manager.games[room_id]
    
    # پاک کردن وضعیت کاربران
    for pid in players:
        if pid in game_manager.user_states:
            del game_manager.user_states[pid]

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور راهنما"""
    help_text = """
    📚 **راهنمای کامل بازی**
    
    **🎮 چگونه بازی کنیم؟**
    ۱. دستور /start رو بزن
    ۲. دکمه "ساخت اتاق جدید" رو بزن
    ۳. لینک رو برای دوستات بفرست
    ۴. وقتی حداقل ۳ نفر شدن، "شروع بازی" رو بزن
    ۵. به سوالات در پیام خصوصی جواب بده
    ۶. منتظر داستان‌های خنده‌دار باش!
    
    **⚠️ نکات مهم:**
    • ربات باید بتونه بهت پیام خصوصی بده
    • هر سوال ۲ دقیقه وقت داری
    • اگه جواب ندی، جواب پیش‌فرض گذاشته میشه
    • بازی با ۳ تا ۱۰ نفر بهتره
    
    **🔧 پشتیبانی:**
    اگه مشکل داشتی، پیام بده به سازنده!
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت خطا"""
    logger.error(f"خطا: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ یه مشکلی پیش اومد! دوباره امتحان کن")

# ================= اجرای ربات =================
def main():
    """تابع اصلی اجرای ربات"""
    print("""
    ====================================
       ربات بازی داستانساز خنده‌دار
          در حال راه‌اندازی...
    ====================================
    """)
    
    # ساخت اپلیکیشن
    app = Application.builder().token(TOKEN).build()
    
    # اضافه کردن دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # اضافه کردن callback ها
    app.add_handler(CallbackQueryHandler(new_room, pattern="^new_room$"))
    app.add_handler(CallbackQueryHandler(start_game, pattern="^start_"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    
    # هندلر پیام‌های متنی
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    
    # هندلر خطا
    app.add_error_handler(error_handler)
    
    # شروع ربات
    print("🤖 ربات آماده است!")
    print("📱 به تلگرام برو و /start رو بزن")
    print("⏸ برای متوقف کردن: Ctrl+C")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
