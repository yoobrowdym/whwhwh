#!/usr/bin/env python3
"""
ربات بازی داستانساز خنده‌دار - نسخه گروهی
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
TOKEN = "8041384292:AAFgB5WqXN3iCMqMIst_jSqqVlCk8o_24l8"  # جایگزین کن با توکن واقعی
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
    
    def create_group_game(self, chat_id, creator_id, creator_name):
        """ساخت بازی جدید در گروه"""
        game_id = f"group_{chat_id}_{int(datetime.now().timestamp())}"
        self.games[game_id] = {
            'chat_id': chat_id,
            'creator': creator_id,
            'players': [creator_id],
            'usernames': [creator_name],
            'answers': {},
            'status': 'waiting',
            'current_question': 0,
            'message_id': None,
            'time_limit': 60  # زمان پیش‌فرض ۶۰ ثانیه
        }
        return game_id
    
    def join_game(self, game_id, user_id, username):
        """اضافه شدن به بازی گروهی"""
        if game_id in self.games:
            game = self.games[game_id]
            if game['status'] == 'waiting' and user_id not in game['players']:
                if len(game['players']) < 10:  # حداکثر ۱۰ نفر
                    game['players'].append(user_id)
                    game['usernames'].append(username)
                    return True
        return False
    
    def set_time_limit(self, game_id, seconds):
        """تنظیم زمان هر سوال"""
        if game_id in self.games:
            self.games[game_id]['time_limit'] = seconds
            return True
        return False

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
    """شروع بازی در گروه"""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text(
            "🎮 **به ربات بازی داستانساز خوش اومدی!**\n\n"
            "برای بازی کردن، لطفاً من رو به یک گروه اضافه کن\n"
            "و دوباره دستور /start رو بزن.",
            parse_mode='Markdown'
        )
        return
    
    # بررسی اینکه آیا بازی قبلاً شروع شده
    active_game = None
    for game_id, game in game_manager.games.items():
        if game['chat_id'] == chat.id:
            active_game = game_id
            break
    
    if active_game and game_manager.games[active_game]['status'] == 'playing':
        await update.message.reply_text("🎮 یه بازی در این گروه در حال انجامه!")
        return
    
    # نمایش منوی شروع بازی
    keyboard = [
        [InlineKeyboardButton("🎮 شروع بازی جدید", callback_data=f"new_group_game_{chat.id}")],
        [InlineKeyboardButton("❓ راهنما", callback_data="group_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🙋‍♂️ سلام {user.first_name}!
🎲 **به بازی داستانساز خنده‌دار در گروه خوش اومدی**

🎯 **چطوری بازی کنیم؟**
۱. روی دکمه "شروع بازی جدید" کلیک کن
۲. بقیه اعضا با دکمه "➕ Join" به بازی اضافه میشن
۳. تو (به عنوان سازنده) زمان هر سوال رو انتخاب کن
۴. دکمه "▶️ شروع بازی" رو بزن
۵. همه در پیوی به سوالات جواب میدن
۶. نتیجه نهایی همینجا تو گروه نمایش داده میشه!

👥 **تعداد بازیکنان:** ۳ تا ۱۰ نفر
⏱ **زمان هر سوال:** قابل انتخاب (۳۰، ۶۰ یا ۱۲۰ ثانیه)

📌 برای شروع، دکمه زیر رو بزن:
"""
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def group_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای بازی در گروه"""
    query = update.callback_query
    await query.answer()
    
    help_text = """
📚 **راهنمای بازی در گروه**

**🎮 مراحل بازی:**
1️⃣ **بات رو به گروه اضافه کن**
2️⃣ تو گروه بنویس `/start`
3️⃣ روی **"شروع بازی جدید"** کلیک کن
4️⃣ بقیه اعضا روی **"➕ Join"** کلیک کنن
5️⃣ **سازنده بازی** زمان هر سوال رو انتخاب کنه
6️⃣ **سازنده بازی** دکمه **"▶️ شروع"** رو بزنه
7️⃣ همه در **پیوی ربات** به سوالات جواب بدن
8️⃣ نتیجه نهایی **تو گروه** نمایش داده میشه

**⚠️ نکات مهم:**
• فقط سازنده بازی می‌تونه بازی رو شروع کنه
• هر سوال بین ۳۰ تا ۱۲۰ ثانیه وقت دارید
• اگه کسی جواب نده، جواب پیش‌فرض گذاشته میشه
• بازی با ۳ تا ۱۰ نفر لذت‌بخش‌تره

😂 بریم که ببینیم چی میشه!
    """
    
    await query.edit_message_text(help_text, parse_mode='Markdown')

async def new_group_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع بازی جدید در گروه"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    chat_id = int(query.data.split("_")[-1])
    
    # بررسی وجود بازی قبلی
    for game_id, game in game_manager.games.items():
        if game['chat_id'] == chat_id and game['status'] == 'waiting':
            await query.edit_message_text("⚠️ یه بازی در حال انتظار قبلاً ساخته شده!")
            return
    
    # ساخت بازی جدید
    game_id = game_manager.create_group_game(chat_id, user.id, user.first_name)
    
    # نمایش وضعیت بازی
    await show_game_status(query, game_id, context)

async def show_game_status(query, game_id: str, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت فعلی بازی"""
    game = game_manager.games[game_id]
    players_list = "\n".join([f"• {name}" for name in game['usernames']])
    
    keyboard = [
        [InlineKeyboardButton("➕ Join", callback_data=f"join_game_{game_id}")],
        [InlineKeyboardButton("⏱ انتخاب زمان", callback_data=f"select_time_{game_id}")],
        [InlineKeyboardButton("▶️ شروع بازی", callback_data=f"start_group_game_{game_id}")]
    ]
    
    if game['creator'] != query.from_user.id:
        keyboard = [[InlineKeyboardButton("➕ Join", callback_data=f"join_game_{game_id}")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status_text = f"""
🏠 **بازی در گروه**
🎮 وضعیت: در انتظار بازیکنان

👥 **بازیکنان ({len(game['players'])}/۱۰):**
{players_list}

⏱ **زمان هر سوال:** {game['time_limit']} ثانیه

👑 **سازنده:** {game['usernames'][0]}

📌 حداقل ۳ نفر برای شروع لازمه.
    """
    
    await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')

async def join_group_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیوستن به بازی گروهی"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    game_id = query.data.replace("join_game_", "")
    
    if game_id not in game_manager.games:
        await query.answer("❌ بازی پیدا نشد!", show_alert=True)
        return
    
    game = game_manager.games[game_id]
    
    if game['status'] != 'waiting':
        await query.answer("❌ بازی قبلاً شروع شده!", show_alert=True)
        return
    
    if user.id in game['players']:
        await query.answer("✅ قبلاً به بازی پیوستی!", show_alert=True)
        return
    
    if game_manager.join_game(game_id, user.id, user.first_name):
        await query.answer("✅ به بازی پیوستی!", show_alert=True)
        await show_game_status(query, game_id, context)
    else:
        await query.answer("❌ خطا در پیوستن!", show_alert=True)

async def select_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب زمان برای سوالات"""
    query = update.callback_query
    await query.answer()
    
    game_id = query.data.replace("select_time_", "")
    
    if game_id not in game_manager.games:
        await query.answer("❌ بازی پیدا نشد!", show_alert=True)
        return
    
    game = game_manager.games[game_id]
    
    if query.from_user.id != game['creator']:
        await query.answer("❌ فقط سازنده می‌تونه زمان رو انتخاب کنه!", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton("⏱ ۳۰ ثانیه", callback_data=f"set_time_{game_id}_30")],
        [InlineKeyboardButton("⏱ ۶۰ ثانیه", callback_data=f"set_time_{game_id}_60")],
        [InlineKeyboardButton("⏱ ۱۲۰ ثانیه", callback_data=f"set_time_{game_id}_120")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⏰ **زمان پاسخ به هر سوال رو انتخاب کن:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def set_time_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم زمان بازی"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    game_id = f"{parts[2]}_{parts[3]}" if len(parts) > 4 else f"{parts[2]}_{parts[3]}"
    seconds = int(parts[-1])
    
    if game_id not in game_manager.games:
        await query.answer("❌ بازی پیدا نشد!", show_alert=True)
        return
    
    game_manager.set_time_limit(game_id, seconds)
    await show_game_status(query, game_id, context)

async def start_group_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع بازی گروهی"""
    query = update.callback_query
    await query.answer()
    
    game_id = query.data.replace("start_group_game_", "")
    
    if game_id not in game_manager.games:
        await query.answer("❌ بازی پیدا نشد!", show_alert=True)
        return
    
    game = game_manager.games[game_id]
    
    if query.from_user.id != game['creator']:
        await query.answer("❌ فقط سازنده بازی می‌تونه شروع کنه!", show_alert=True)
        return
    
    if len(game['players']) < 3:
        await query.answer(f"🚫 حداقل ۳ نفر لازمه! (الان {len(game['players'])} نفر)", show_alert=True)
        return
    
    game['status'] = 'playing'
    
    await query.edit_message_text(
        f"🎮 **بازی شروع شد!**\n\n"
        f"👥 {len(game['players'])} نفر تو بازی هستن.\n"
        f"⏱ هر سوال {game['time_limit']} ثانیه وقت دارید.\n\n"
        f"📝 به پیوی ربات برید و به سوالات جواب بدید!",
        parse_mode='Markdown'
    )
    
    # شروع پرسش سوالات
    await ask_question_group(game_id, 0, context)

async def ask_question_group(game_id: str, q_index: int, context: ContextTypes.DEFAULT_TYPE):
    """پرسش سوال در بازی گروهی"""
    game = game_manager.games[game_id]
    question = QUESTIONS[q_index]
    time_limit = game['time_limit']
    
    # پرسش از هر بازیکن
    for player_id in game['players']:
        game_manager.user_states[player_id] = {
            'game_id': game_id,
            'question': q_index,
            'answered': False
        }
        
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"📝 **سوال {q_index + 1} از {len(QUESTIONS)}**\n\n"
                     f"❓ {question}\n\n"
                     f"💡 جوابت رو همینجا بنویس...\n"
                     f"⏱ وقت داری تا {time_limit} ثانیه",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"خطا در ارسال به کاربر {player_id}: {e}")
    
    # تنظیم تایمر
    context.job_queue.run_once(
        timeout_handler_group,
        time_limit,
        data={'game_id': game_id, 'q_index': q_index},
        name=f"timeout_{game_id}_{q_index}"
    )

async def handle_answer_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت جواب در بازی گروهی"""
    user_id = update.effective_user.id
    answer_text = update.message.text.strip()
    
    if user_id not in game_manager.user_states:
        await update.message.reply_text("❌ الان نوبت تو نیست یا بازی تموم شده!")
        return
    
    state = game_manager.user_states[user_id]
    game_id = state['game_id']
    
    if game_id not in game_manager.games:
        await update.message.reply_text("❌ بازی پیدا نشد!")
        return
    
    game = game_manager.games[game_id]
    
    if str(user_id) not in game['answers']:
        game['answers'][str(user_id)] = {}
    
    game['answers'][str(user_id)][QUESTIONS[state['question']]] = answer_text
    state['answered'] = True
    
    await update.message.reply_text("✅ جوابت ذخیره شد! منتظر بقیه...")
    
    # چک کردن جواب همه
    all_answered = True
    for pid in game['players']:
        if pid in game_manager.user_states:
            if not game_manager.user_states[pid]['answered']:
                all_answered = False
                break
    
    if all_answered:
        next_q = state['question'] + 1
        if next_q < len(QUESTIONS):
            game['current_question'] = next_q
            await ask_question_group(game_id, next_q, context)
        else:
            await finalize_game_group(game_id, context)

async def timeout_handler_group(context: ContextTypes.DEFAULT_TYPE):
    """مدیریت اتمام زمان در بازی گروهی"""
    job = context.job
    game_id = job.data['game_id']
    q_index = job.data['q_index']
    
    if game_id not in game_manager.games:
        return
    
    game = game_manager.games[game_id]
    
    for player_id in game['players']:
        if str(player_id) not in game['answers']:
            game['answers'][str(player_id)] = {}
        
        if QUESTIONS[q_index] not in game['answers'][str(player_id)]:
            game['answers'][str(player_id)][QUESTIONS[q_index]] = DEFAULT_ANSWERS[q_index]
    
    next_q = q_index + 1
    if next_q < len(QUESTIONS):
        game['current_question'] = next_q
        await ask_question_group(game_id, next_q, context)
    else:
        await finalize_game_group(game_id, context)

async def finalize_game_group(game_id: str, context: ContextTypes.DEFAULT_TYPE):
    """پایان بازی و نمایش نتایج در گروه"""
    game = game_manager.games[game_id]
    players = game['players']
    usernames = game['usernames']
    answers = game['answers']
    
    n = len(players)
    stories = []
    
    for i in range(n):
        story_parts = []
        for q_index, question in enumerate(QUESTIONS):
            player_index = (i + q_index) % n
            player_id = str(players[player_index])
            answer = answers.get(player_id, {}).get(question, DEFAULT_ANSWERS[q_index])
            story_parts.append(answer)
        
        story = " ".join(story_parts)
        stories.append(f"📖 **داستان {i+1}:** {story}")
    
    result_text = "🎉 **نتیجه نهایی بازی!** 🎉\n\n"
    result_text += "\n\n".join(stories)
    result_text += f"\n\n👥 **بازیکنان:** {', '.join(usernames)}"
    result_text += f"\n\n😂 اینم شد داستان‌هاتون!"
    
    await context.bot.send_message(
        chat_id=game['chat_id'],
        text=result_text,
        parse_mode='Markdown'
    )
    
    # پاک کردن بازی
    if game_id in game_manager.games:
        del game_manager.games[game_id]
    
    for pid in players:
        if pid in game_manager.user_states:
            del game_manager.user_states[pid]

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
          نسخه گروهی
          در حال راه‌اندازی...
    ====================================
    """)
    
    app = Application.builder().token(TOKEN).build()
    
    # دستورات
    app.add_handler(CommandHandler("start", start))
    
    # کالبک‌ها
    app.add_handler(CallbackQueryHandler(new_group_game, pattern="^new_group_game_"))
    app.add_handler(CallbackQueryHandler(group_help_callback, pattern="^group_help$"))
    app.add_handler(CallbackQueryHandler(join_group_game, pattern="^join_game_"))
    app.add_handler(CallbackQueryHandler(select_time_callback, pattern="^select_time_"))
    app.add_handler(CallbackQueryHandler(set_time_limit, pattern="^set_time_"))
    app.add_handler(CallbackQueryHandler(start_group_game, pattern="^start_group_game_"))
    
    # هندلر پیام‌ها
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer_group))
    
    # هندلر خطا
    app.add_error_handler(error_handler)
    
    print("🤖 ربات آماده است!")
    print("📱 ربات رو به گروه اضافه کن و /start رو بزن")
    print("⏸ برای متوقف کردن: Ctrl+C")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
