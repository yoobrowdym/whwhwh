#!/usr/bin/env python3
"""
ربات بازی "کی کِی کجا"
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
            'time_limit': 60
        }
        return game_id
    
    def join_game(self, game_id, user_id, username):
        """اضافه شدن به بازی گروهی"""
        if game_id in self.games:
            game = self.games[game_id]
            if game['status'] == 'waiting' and user_id not in game['players']:
                if len(game['players']) < 10:
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
    
    def cancel_game(self, game_id, user_id):
        """کنسل کردن بازی (فقط توسط سازنده)"""
        if game_id in self.games:
            if self.games[game_id]['creator'] == user_id:
                del self.games[game_id]
                return True
        return False
    
    def stop_game(self, game_id, user_id):
        """توقف بازی در حال انجام (فقط توسط سازنده)"""
        if game_id in self.games:
            game = self.games[game_id]
            if game['creator'] == user_id:
                # پاک کردن وضعیت کاربران
                for pid in game['players']:
                    if pid in self.user_states:
                        del self.user_states[pid]
                del self.games[game_id]
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
    """شروع بازی در گروه یا پیوی"""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        keyboard = [
            [InlineKeyboardButton("❓ راهنمای بازی", callback_data="private_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🙋‍♂️ سلام {user.first_name}!\n"
            f"🎲 **به بازی «کی کِی کجا» خوش اومدی!**\n\n"
            f"برای بازی کردن، من رو به یک گروه اضافه کن\n"
            f"و دوباره توی گروه دستور /start رو بزن.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    active_game = None
    for game_id, game in game_manager.games.items():
        if game['chat_id'] == chat.id:
            active_game = game_id
            break
    
    if active_game and game_manager.games[active_game]['status'] == 'playing':
        await update.message.reply_text("🎮 یه بازی در این گروه در حال انجامه!\nبرای کنسل کردن از دستور /stop استفاده کن.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🎮 شروع بازی جدید", callback_data=f"new_group_game_{chat.id}")],
        [InlineKeyboardButton("❓ راهنما", callback_data="group_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🙋‍♂️ سلام {user.first_name}!
🎲 **به بازی «کی کِی کجا» خوش اومدی**

برای شروع بازی جدید، روی دکمه زیر کلیک کن.
"""
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def stop_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور توقف بازی"""
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == "private":
        await update.message.reply_text("❌ این دستور فقط در گروه قابل استفاده است!")
        return
    
    # پیدا کردن بازی فعال در گروه
    active_game = None
    for game_id, game in game_manager.games.items():
        if game['chat_id'] == chat.id:
            active_game = game_id
            break
    
    if not active_game:
        await update.message.reply_text("❌ هیچ بازی فعالی در این گروه وجود ندارد!")
        return
    
    game = game_manager.games[active_game]
    
    if user.id != game['creator']:
        await update.message.reply_text("❌ فقط سازنده بازی می‌تواند آن را متوقف کند!")
        return
    
    if game_manager.stop_game(active_game, user.id):
        await update.message.reply_text(
            "🛑 **بازی با موفقیت متوقف شد!**\n\n"
            "می‌توانید با /start یک بازی جدید شروع کنید.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ خطا در توقف بازی!")

async def private_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای بازی در پیوی"""
    query = update.callback_query
    await query.answer()
    
    help_text = """
📚 **راهنمای بازی «کی کِی کجا»**

**🎮 چطوری بازی کنیم؟**
1️⃣ **بات رو به گروه اضافه کن**
2️⃣ تو گروه بنویس `/start`
3️⃣ روی **"شروع بازی جدید"** کلیک کن
4️⃣ بقیه اعضا روی **"➕ Join"** کلیک کنن
5️⃣ **سازنده بازی** زمان هر سوال رو انتخاب کنه
6️⃣ **سازنده بازی** دکمه **"▶️ شروع"** رو بزنه
7️⃣ همه در **پیوی ربات** به سوالات جواب بدن
8️⃣ نتیجه نهایی **تو گروه** نمایش داده میشه

**🛑 برای کنسل کردن بازی:**
• قبل از شروع: از دکمه "❌ کنسل کردن بازی"
• در حین بازی: دستور `/stop@whowhwhbot` در گروه

**⚠️ نکات مهم:**
• فقط سازنده بازی می‌تونه بازی رو شروع یا کنسل کنه
• هر سوال بین 30 تا 120 ثانیه وقت دارید
• اگه کسی جواب نده، جواب پیش‌فرض گذاشته میشه
• بازی با 3 تا 10 نفر لذت‌بخش‌تره

😂 بریم که ببینیم چی میشه!
    """
    
    await query.edit_message_text(help_text, parse_mode='Markdown')

async def group_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای بازی در گروه"""
    query = update.callback_query
    await query.answer()
    
    help_text = """
📚 **راهنمای بازی «کی کِی کجا» در گروه**

**🎮 مراحل بازی:**
1️⃣ روی **"شروع بازی جدید"** کلیک کن
2️⃣ بقیه اعضا روی **"➕ Join"** کلیک کنن
3️⃣ **سازنده بازی** زمان هر سوال رو انتخاب کنه
4️⃣ **سازنده بازی** دکمه **"▶️ شروع"** رو بزنه
5️⃣ همه در **پیوی ربات** به سوالات جواب بدن
6️⃣ نتیجه نهایی **تو گروه** نمایش داده میشه

**🛑 برای کنسل کردن بازی:**
• قبل از شروع: از دکمه "❌ کنسل کردن بازی"
• در حین بازی: دستور `/stop@whowhwhbot` در گروه

**⚠️ نکات مهم:**
• فقط سازنده بازی می‌تونه بازی رو شروع یا کنسل کنه
• هر سوال بین 30 تا 120 ثانیه وقت دارید
• اگه کسی جواب نده، جواب پیش‌فرض گذاشته میشه
• بازی با 3 تا 10 نفر لذت‌بخش‌تره

😂 بریم که ببینیم چی میشه!
    """
    
    await query.edit_message_text(help_text, parse_mode='Markdown')

async def new_group_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع بازی جدید در گروه"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    chat_id = int(query.data.split("_")[-1])
    
    for game_id, game in game_manager.games.items():
        if game['chat_id'] == chat_id and game['status'] == 'waiting':
            await query.edit_message_text("⚠️ یه بازی در حال انتظار قبلاً ساخته شده!")
            return
    
    game_id = game_manager.create_group_game(chat_id, user.id, user.first_name)
    await show_game_status(query, game_id, context)

async def show_game_status(query, game_id: str, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت فعلی بازی"""
    game = game_manager.games[game_id]
    players_list = "\n".join([f"• {name}" for name in game['usernames']])
    
    time_30_text = "⏱ 30 ثانیه"
    time_60_text = "✅ ⏱ 60 ثانیه"
    time_120_text = "⏱ 120 ثانیه"
    
    if game['time_limit'] == 30:
        time_30_text = "✅ ⏱ 30 ثانیه"
        time_60_text = "⏱ 60 ثانیه"
        time_120_text = "⏱ 120 ثانیه"
    elif game['time_limit'] == 120:
        time_30_text = "⏱ 30 ثانیه"
        time_60_text = "⏱ 60 ثانیه"
        time_120_text = "✅ ⏱ 120 ثانیه"
    
    keyboard = [
        [InlineKeyboardButton("➕ Join", callback_data=f"join_game_{game_id}")],
        [
            InlineKeyboardButton(time_30_text, callback_data=f"set_time_{game_id}_30"),
            InlineKeyboardButton(time_60_text, callback_data=f"set_time_{game_id}_60"),
            InlineKeyboardButton(time_120_text, callback_data=f"set_time_{game_id}_120")
        ],
        [InlineKeyboardButton("▶️ شروع بازی", callback_data=f"start_group_game_{game_id}")],
        [InlineKeyboardButton("❌ کنسل کردن بازی", callback_data=f"cancel_game_{game_id}")]
    ]
    
    if game['creator'] != query.from_user.id:
        keyboard = [[InlineKeyboardButton("➕ Join", callback_data=f"join_game_{game_id}")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status_text = f"""
🏠 **بازی «کی کِی کجا» در گروه**
🎮 وضعیت: در انتظار بازیکنان

👥 **بازیکنان ({len(game['players'])}/10):**
{players_list}

⏱ **زمان هر سوال:** {game['time_limit']} ثانیه

👑 **سازنده:** {game['usernames'][0]}

📌 حداقل 3 نفر برای شروع لازمه.
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
    
    # چک کردن اینکه کاربر بات رو استارت کرده یا نه
    try:
        await context.bot.send_chat_action(chat_id=user.id, action="typing")
    except Exception:
        await query.answer("❌ ابتدا ربات رو استارت کن!\n\n/start رو توی پیوی ربات بزن.", show_alert=True)
        return
    
    if game_manager.join_game(game_id, user.id, user.first_name):
        await query.answer("✅ به بازی پیوستی!", show_alert=True)
        await show_game_status(query, game_id, context)
    else:
        await query.answer("❌ خطا در پیوستن!", show_alert=True)

async def set_time_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم زمان بازی"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    
    # استخراج صحیح game_id
    # فرمت: set_time_{game_id}_{seconds}
    seconds = int(parts[-1])
    game_part = "_".join(parts[3:-1])  # همه چیز بین set_time_ و آخرین بخش
    
    # پیدا کردن game_id کامل
    game_id = None
    for gid in game_manager.games:
        if gid.endswith(game_part) or game_part in gid:
            game_id = gid
            break
    
    if not game_id or game_id not in game_manager.games:
        await query.answer("❌ بازی پیدا نشد!", show_alert=True)
        return
    
    game = game_manager.games[game_id]
    
    if query.from_user.id != game['creator']:
        await query.answer("❌ فقط سازنده می‌تونه زمان رو انتخاب کنه!", show_alert=True)
        return
    
    game_manager.set_time_limit(game_id, seconds)
    await show_game_status(query, game_id, context)

async def cancel_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کنسل کردن بازی"""
    query = update.callback_query
    await query.answer()
    
    game_id = query.data.replace("cancel_game_", "")
    
    if game_id not in game_manager.games:
        await query.answer("❌ بازی پیدا نشد!", show_alert=True)
        return
    
    game = game_manager.games[game_id]
    
    if query.from_user.id != game['creator']:
        await query.answer("❌ فقط سازنده می‌تونه بازی رو کنسل کنه!", show_alert=True)
        return
    
    if game_manager.cancel_game(game_id, query.from_user.id):
        await query.edit_message_text(
            "❌ **بازی با موفقیت کنسل شد!**\n\n"
            "می‌تونی دوباره با /start یه بازی جدید شروع کنی.",
            parse_mode='Markdown'
        )
    else:
        await query.answer("❌ خطا در کنسل کردن!", show_alert=True)

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
        await query.answer(f"⚠️ ظرفیت به حد مجاز نرسیده! حداقل 3 نفر لازم است. (الان {len(game['players'])} نفر)", show_alert=True)
        return
    
    game['status'] = 'playing'
    
    await query.edit_message_text(
        f"🎮 **بازی «کی کِی کجا» شروع شد!**\n\n"
        f"👥 {len(game['players'])} نفر تو بازی هستن.\n"
        f"⏱ هر سوال {game['time_limit']} ثانیه وقت دارید.\n\n"
        f"📝 به پیوی ربات برید و به سوالات جواب بدید!\n\n"
        f"🛑 برای کنسل کردن بازی از دستور /stop استفاده کنید.",
        parse_mode='Markdown'
    )
    
    await ask_question_group(game_id, 0, context)

async def ask_question_group(game_id: str, q_index: int, context: ContextTypes.DEFAULT_TYPE):
    """پرسش سوال در بازی گروهی"""
    game = game_manager.games[game_id]
    question = QUESTIONS[q_index]
    time_limit = game['time_limit']
    
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
    
    context.job_queue.run_once(
        timeout_handler_group,
        time_limit,
        data={'game_id': game_id, 'q_index': q_index},
        name=f"timeout_{game_id}_{q_index}"
    )

async def handle_answer_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت جواب در بازی گروهی - بدون پیام خطای نوبتی"""
    user_id = update.effective_user.id
    answer_text = update.message.text.strip()
    
    if user_id not in game_manager.user_states:
        # بدون پیام خطا - فقط سکوت
        return
    
    state = game_manager.user_states[user_id]
    game_id = state['game_id']
    
    if game_id not in game_manager.games:
        return
    
    game = game_manager.games[game_id]
    
    if str(user_id) not in game['answers']:
        game['answers'][str(user_id)] = {}
    
    game['answers'][str(user_id)][QUESTIONS[state['question']]] = answer_text
    state['answered'] = True
    
    await update.message.reply_text("✅ جوابت ذخیره شد! منتظر بقیه...")
    
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
    
    result_text = "🎉 **نتیجه نهایی بازی «کی کِی کجا»!** 🎉\n\n"
    result_text += "\n\n".join(stories)
    result_text += f"\n\n👥 **بازیکنان:** {', '.join(usernames)}"
    result_text += f"\n\n😂 اینم شد داستان‌هاتون!"
    
    await context.bot.send_message(
        chat_id=game['chat_id'],
        text=result_text,
        parse_mode='Markdown'
    )
    
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
       ربات بازی "کی کِی کجا"
          نسخه گروهی
          در حال راه‌اندازی...
    ====================================
    """)
    
    app = Application.builder().token(TOKEN).build()
    
    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop_game_command))
    
    # کالبک‌ها
    app.add_handler(CallbackQueryHandler(new_group_game, pattern="^new_group_game_"))
    app.add_handler(CallbackQueryHandler(private_help_callback, pattern="^private_help$"))
    app.add_handler(CallbackQueryHandler(group_help_callback, pattern="^group_help$"))
    app.add_handler(CallbackQueryHandler(join_group_game, pattern="^join_game_"))
    app.add_handler(CallbackQueryHandler(set_time_limit, pattern="^set_time_"))
    app.add_handler(CallbackQueryHandler(start_group_game, pattern="^start_group_game_"))
    app.add_handler(CallbackQueryHandler(cancel_game_callback, pattern="^cancel_game_"))
    
    # هندلر پیام‌ها
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer_group))
    
    # هندلر خطا
    app.add_error_handler(error_handler)
    
    print("🤖 ربات آماده است!")
    print("📱 ربات رو به گروه اضافه کن و /start رو بزن")
    print("🛑 برای توقف بازی در گروه: /stop")
    print("⏸ برای متوقف کردن کل ربات: Ctrl+C")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
