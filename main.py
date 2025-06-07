import json
import os
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, CallbackQueryHandler
)

ANSWER_DB = 'answers.json'
RESULTS_DB = 'results.json'
FILES_DB = 'files.json'
ADMIN_ID = 5802051984  # Admin Telegram ID

pending_tests = {}  # Temporarily store test code and answers by admin

def get_score_emoji(score):
    if score == 100:
        return "\U0001F3C6 A+ (Zo‘r!)"
    elif score >= 90:
        return "\U0001F389 A (A’lo)"
    elif score >= 80:
        return "\u2705 B (Yaxshi)"
    elif score >= 70:
        return "\U0001F7E1 C (Qoniqarli)"
    elif score >= 60:
        return "\U0001F7E0 D (O‘rtacha)"
    else:
        return "\u274C F (Yomon)"

def save_result(user_id, code, correct_count, total):
    if os.path.exists(RESULTS_DB):
        with open(RESULTS_DB, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    percent = round(correct_count / total * 100)
    record = {
        "code": code,
        "score": percent,
        "correct": correct_count,
        "total": total,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    user_id = str(user_id)
    data.setdefault(user_id, []).append(record)

    with open(RESULTS_DB, 'w') as f:
        json.dump(data, f, indent=2)

def check_answer(update: Update, context: CallbackContext):
    message = update.message.text.strip()
    try:
        code, user_answers_raw = message.split(maxsplit=1)
    except:
        update.message.reply_text("❗ Format: TEST123 A B 42 Paris")
        return

    code = code.upper()
    user_answers_list = user_answers_raw.strip().split()

    if not os.path.exists(ANSWER_DB):
        update.message.reply_text("📂 Hozircha testlar yo‘q.")
        return

    with open(ANSWER_DB, 'r') as f:
        data = json.load(f)

    if code not in data:
        update.message.reply_text("❌ Noto‘g‘ri test kodi.")
        return

    correct_answers = data[code]["answers"]
    if isinstance(correct_answers, str):
        correct_answers = correct_answers.strip().split()  # eski formatni qo‘llab-quvvatlash

    if len(user_answers_list) != len(correct_answers):
        update.message.reply_text(f"⚠️ Javoblar soni noto‘g‘ri. {len(correct_answers)} ta javob bo‘lishi kerak.")
        return

    correct_count = 0
    total = len(correct_answers)

    for user_ans, correct_ans in zip(user_answers_list, correct_answers):
        if correct_ans.upper() in ["A", "B", "C", "D"]:
            # Variantli — faqat harfni solishtirish
            if user_ans.upper() == correct_ans.upper():
                correct_count += 1
        else:
            # Ochiq — raqamli yoki matnli, case-insensitive
            if user_ans.strip().lower() == correct_ans.strip().lower():
                correct_count += 1

    percent = round(correct_count / total * 100)
    emoji = get_score_emoji(percent)

    save_result(update.effective_user.id, code, correct_count, total)

    try:
        context.bot.send_message(
            chat_id=update.effective_user.id,
            text=(f"📨 Test natijangiz:\n"
                  f"📘 Test: {code}\n"
                  f"✅ To‘g‘ri: {correct_count}/{total}\n"
                  f"📊 Ball: {percent}%\n"
                  f"📈 Baho: {emoji}")
        )
        update.message.reply_text("📬 Natijangiz tayyor")
    except:
        update.message.reply_text("⚠️ Botni /start bilan boshlang, keyin DM jo‘natiladi.")


def myresults(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)

    if not os.path.exists(RESULTS_DB):
        update.message.reply_text("⛔ Siz hali test ishlamagansiz.")
        return

    with open(RESULTS_DB, 'r') as f:
        data = json.load(f)

    if user_id not in data:
        update.message.reply_text("📭 Sizda natijalar yo‘q.")
        return

    results = data[user_id][-5:]
    text = "📌 So‘nggi natijalar:\n\n"
    for r in results:
        emoji = get_score_emoji(r['score'])
        text += f"🧾 {r['code']} — {r['score']}% {emoji}\n📅 {r['date']}\n\n"

    update.message.reply_text(text)

def topusers(update: Update, context: CallbackContext):
    if not os.path.exists(RESULTS_DB):
        update.message.reply_text("⛔ Hech kim test ishlamagan.")
        return

    with open(RESULTS_DB, 'r') as f:
        data = json.load(f)

    scores = []
    for uid, results in data.items():
        for r in results:
            scores.append((uid, r['score'], r['code'], r['date']))

    scores.sort(key=lambda x: x[1], reverse=True)
    top = scores[:5]

    text = "🏅 Eng yuqori natijalar:\n\n"
    for i, (uid, score, code, date) in enumerate(top, 1):
        emoji = get_score_emoji(score)
        text += f"{i}. 👤 {uid} — {score}% {emoji} ({code})\n📅 {date}\n"

    update.message.reply_text(text)

def tests(update: Update, context: CallbackContext):
    if not os.path.exists(FILES_DB):
        update.message.reply_text("📂 Hozircha testlar mavjud emas.")
        return

    with open(FILES_DB, 'r') as f:
        data = json.load(f)

    keyboard = [
        [InlineKeyboardButton(code, callback_data=f"SEND_{code}")] for code in data
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("📚 Testlar ro‘yxati:", reply_markup=reply_markup)

def send_file_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data_code = query.data

    if not data_code.startswith("SEND_"):
        return

    code = data_code.replace("SEND_", "")

    if not os.path.exists(FILES_DB):
        query.message.reply_text("📂 Fayllar bazasi topilmadi.")
        return

    with open(FILES_DB, 'r') as f:
        data = json.load(f)

    if code in data:
        file_id = data[code]
        context.bot.send_document(chat_id=query.message.chat.id, document=file_id)
        context.bot.send_message(chat_id=query.message.chat.id, text=f"📘 Test kodi: `{code}`\n✏️ Javoblaringizni quyidagicha yuboring:\n`{code} ABCD...`", parse_mode='Markdown')
    else:
        query.message.reply_text("❌ Fayl topilmadi.")

def addanswers(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("⛔ Sizda ruxsat yo‘q.")
        return

    try:
        code = context.args[0].upper()
        answers = [a.strip().upper() for a in context.args[1:]]
        if not answers:
            raise Exception
    except:
        update.message.reply_text("❗ Format: /addanswers TEST123 A B 42 Paris")
        return

    if os.path.exists(ANSWER_DB):
        with open(ANSWER_DB, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    data[code] = {"answers": answers}
    with open(ANSWER_DB, 'w') as f:
        json.dump(data, f, indent=2)

    pending_tests[update.effective_user.id] = code
    update.message.reply_text("✅ Javoblar saqlandi. Endi test faylini yuboring.")


def addfile(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID or not update.message.document:
        return

    code = pending_tests.get(update.message.from_user.id)
    if not code:
        update.message.reply_text("❗ Avval /addanswers TEST123 ABCD yuboring.")
        return

    file_id = update.message.document.file_id

    if os.path.exists(FILES_DB):
        with open(FILES_DB, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    data[code] = file_id
    with open(FILES_DB, 'w') as f:
        json.dump(data, f, indent=2)

    update.message.reply_text(f"📎 Fayl saqlandi: {code}")
    del pending_tests[update.message.from_user.id]

def set_commands(updater: Updater):
    commands = [
        BotCommand("start", "Botni boshlash"),
        BotCommand("addanswers", "Test javoblarini qo‘shish (admin)"),
        BotCommand("tests", "Testlar ro‘yxatini ko‘rish"),
        BotCommand("myresults", "Mening natijalarim"),
        BotCommand("topusers", "Eng yaxshi foydalanuvchilar")
    ]
    updater.bot.set_my_commands(commands)

def main():
    updater = Updater("8196241808:AAG-o8blSV4-yCS6pPcPOWadZs-n7G_Lvmk", use_context=True)
    dp = updater.dispatcher

    set_commands(updater)

    dp.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("👋 Botga xush kelibsiz!")))
    dp.add_handler(CommandHandler("addanswers", addanswers))
    dp.add_handler(CommandHandler("tests", tests))
    dp.add_handler(CommandHandler("myresults", myresults))
    dp.add_handler(CommandHandler("topusers", topusers))
    dp.add_handler(MessageHandler(Filters.document, addfile))

    dp.add_handler(CallbackQueryHandler(send_file_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, check_answer))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
