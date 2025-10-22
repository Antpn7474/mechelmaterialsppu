import os
import json
import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

BOT_TOKEN = "7578917097:AAE-FwH8lj6JXTyzaTD-hC-OIWeyqaHtFxo" # Лучше в переменной среды!
ADMIN_IDS = [1618247541]
DATA_FILE = "suggestions.json"

SUGGESTION = 1

LIST_SUGGESTIONS, VIEW_SUGGESTION, COMMENT_INPUT = range(3, 6)

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_user_menu():
    keyboard = [
        [KeyboardButton("Подать предложение по улучшению")],
        [KeyboardButton("Посмотреть историю предложений")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_menu():
    keyboard = [
        [KeyboardButton("Просмотреть все предложения")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        await update.message.reply_text(
            "Привет, администратор! Выбери действие из меню.",
            reply_markup=get_admin_menu(),
        )
    else:
        await update.message.reply_text(
            'Привет! Данный бот создан для работников ООО "Мечел-Материалы", где каждый работник может написать свое предложение по улучшению процессов и условий работы! За каждое действенное предложение есть возможность получить вознаграждение! Отправьте свою идею, и мы обязательно её рассмотрим.',
            reply_markup=get_user_menu(),
        )

async def handle_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    if text == "Посмотреть историю предложений":
        data = load_data()
        user_suggestions = [s for s in data if s["user_id"] == user.id]

        if not user_suggestions:
            menu = get_admin_menu() if is_admin(user.id) else get_user_menu()
            await update.message.reply_text("У вас нет поданных предложений.", reply_markup=menu)
            return

        for s in user_suggestions:
            msg = (
                f"ID: {s['id']}\n"
                f"Дата: {s['date'][:19]}\n"
                f"Текст: {s['text']}\n"
                f"Статус: {s['status']}\n"
                f"Комментарий: {s['comment'] if s['comment'] else 'нет'}"
            )
            await update.message.reply_text(msg)
        
        menu = get_admin_menu() if is_admin(user.id) else get_user_menu()
        await update.message.reply_text("История предложений показана выше.", reply_markup=menu)
    else:
        await update.message.reply_text("Пожалуйста, используйте меню.")

async def start_suggestion_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        await update.message.reply_text(
            "Администраторы не могут подавать предложения. Ваша функция - просмотр и реакция на предложения других пользователей.",
            reply_markup=get_admin_menu()
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Пожалуйста, опишите вашу идею по пунктам: 1. Отдел/место применения: где это будет действовать. 2. Подробное описание: что именно, как работает сейчас, что предлагаете изменить. 3. Выгода/эффект: экономия времени/денег, повышение безопасности, качество, удобство. 4.Примерный план внедрения: простые шаги, ресурсы. 5.Вложения: фото, схемы, расчёты.Чтобы отменить /cancel.",
        reply_markup=ReplyKeyboardRemove()
    )
    return SUGGESTION

async def handle_new_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if not text:
        await update.message.reply_text("Пустое предложение не может быть сохранено. Пожалуйста, введите текст или /cancel.")
        return SUGGESTION

    data = load_data()
    suggestion_id = max([s["id"] for s in data], default=0) + 1
    new_suggestion = {
        "id": suggestion_id,
        "user_id": user.id,
        "user_name": user.full_name,
        "text": text,
        "date": datetime.datetime.now().isoformat(),
        "status": "Новый",
        "comment": "",
    }
    data.append(new_suggestion)
    data.sort(key=lambda x: x["date"], reverse=True)
    save_data(data)

    menu = get_admin_menu() if is_admin(user.id) else get_user_menu()
    await update.message.reply_text(
        f"Спасибо! Ваше предложение зарегистровано под №{suggestion_id}. Ответ будет в этом боте, а также вы сможете наблюдать статус вашего обращения!",
        reply_markup=menu
    )
    return ConversationHandler.END

async def send_suggestions_list_message(update_or_query_or_message, context):
    data = load_data()
    if not data:
        text = "Пока нет предложений."
        reply_markup = None
    else:
        text = "Выберите предложение для просмотра:"
        keyboard = []
        for s in data:
            btn_text = f"ID {s['id']}: {s['text'][:25]}{'...' if len(s['text']) > 25 else ''}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_{s['id']}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(update_or_query_or_message, Update):
        await update_or_query_or_message.message.reply_text(text, reply_markup=reply_markup)
    elif hasattr(update_or_query_or_message, 'edit_message_text'):
        await update_or_query_or_message.edit_message_text(text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update_or_query_or_message.effective_chat.id, text=text, reply_markup=reply_markup)

async def send_detailed_suggestion_message(update_or_query, context, suggestion_id):
    data = load_data()
    suggestion = next((s for s in data if s["id"] == suggestion_id), None)

    if not suggestion:
        text = "Предложение не найдено."
        reply_markup = None
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(text)
        elif hasattr(update_or_query, 'reply_text'):
            await update_or_query.reply_text(text)
        else:
            await update_or_query.message.reply_text(text)
        return

    text = (
        f"ID: {suggestion['id']}\n"
        f"Пользователь: {suggestion['user_name']} (id: {suggestion['user_id']})\n"
        f"Дата: {suggestion['date'][:19]}\n"
        f"Текст: {suggestion['text']}\n"
        f"Статус: {suggestion['status']}\n"
        f"Комментарий: {suggestion['comment'] if suggestion['comment'] else 'нет'}\n\n"
        "Выберите действие:"
    )
    keyboard = [
        [
            InlineKeyboardButton("Принято к рассмотрению", callback_data=f"status_{suggestion_id}_Принято к рассмотрению"),
            InlineKeyboardButton("Удовлетворено", callback_data=f"status_{suggestion_id}_Удовлетворено"),
            InlineKeyboardButton("Отказано", callback_data=f"status_{suggestion_id}_Отказано"),
        ],
        [InlineKeyboardButton("Добавить комментарий", callback_data=f"comment_{suggestion_id}")],
        [InlineKeyboardButton("Назад", callback_data="back_to_list")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(text, reply_markup=reply_markup)
    elif hasattr(update_or_query, 'reply_text'):
        await update_or_query.reply_text(text, reply_markup=reply_markup)
    else:
        await update_or_query.message.reply_text(text, reply_markup=reply_markup)

async def start_admin_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для этого действия.")
        return ConversationHandler.END

    await send_suggestions_list_message(update, context)
    return LIST_SUGGESTIONS

async def handle_list_suggestions_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.edit_message_text("У вас нет прав для этого действия.")
        return ConversationHandler.END

    data_payload = query.data
    if data_payload.startswith("view_"):
        suggestion_id = int(data_payload.split("_")[1])
        await send_detailed_suggestion_message(query, context, suggestion_id)
        context.user_data["current_suggestion_id"] = suggestion_id
        return VIEW_SUGGESTION
    
    return LIST_SUGGESTIONS

async def handle_view_suggestion_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.edit_message_text("У вас нет прав для этого действия.")
        return ConversationHandler.END

    data_payload = query.data
    data = load_data()

    if data_payload.startswith("status_"):
        parts = data_payload.split("_", 2)
        suggestion_id = int(parts[1])
        new_status = parts[2]
        
        suggestion = next((s for s in data if s["id"] == suggestion_id), None)
        if suggestion:
            suggestion["status"] = new_status
            save_data(data)
            try:
                await context.bot.send_message(
                    chat_id=suggestion["user_id"],
                    text=f"Статус вашего предложения №{suggestion_id} обновлён на: {new_status}",
                )
            except Exception as e:
                print(f"Ошибка при уведомлении пользователя: {e}")
            
            await send_detailed_suggestion_message(query, context, suggestion_id)
            return VIEW_SUGGESTION
        else:
            await query.edit_message_text("Предложение не найдено.")
            await send_suggestions_list_message(query, context)
            return LIST_SUGGESTIONS

    elif data_payload.startswith("comment_"):
        suggestion_id = int(data_payload.split("_")[1])
        context.user_data["comment_for"] = suggestion_id
        await query.edit_message_text(
            f"Пожалуйста, отправьте комментарий к предложению №{suggestion_id}.\n"
            "Для отмены введите /cancel, для завершения ввода комментария введите /done."
        )
        return COMMENT_INPUT

    elif data_payload == "back_to_list":
        await send_suggestions_list_message(query, context)
        context.user_data.pop("current_suggestion_id", None)
        return LIST_SUGGESTIONS
    
    return VIEW_SUGGESTION

async def comment_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("У вас нет прав оставлять комментарии.")
        return ConversationHandler.END

    suggestion_id = context.user_data.get("comment_for")
    if suggestion_id is None:
        await update.message.reply_text("Ошибка: не найдено предложение для комментария.")
        return ConversationHandler.END

    comment_text = update.message.text.strip()

    if comment_text.startswith('/done'):
        await update.message.reply_text("Ввод комментария завершён.")
        context.user_data.pop("comment_for", None)
        await send_detailed_suggestion_message(update.message, context, suggestion_id)
        return VIEW_SUGGESTION
    elif comment_text.startswith('/cancel'):
        await update.message.reply_text("Ввод комментария отменён.")
        context.user_data.pop("comment_for", None)
        await send_detailed_suggestion_message(update.message, context, suggestion_id)
        return VIEW_SUGGESTION
    else:
        data = load_data()
        suggestion = next((s for s in data if s["id"] == suggestion_id), None)

        if not suggestion:
            await update.message.reply_text("Предложение не найдено.")
            context.user_data.pop("comment_for", None)
            return ConversationHandler.END

        if suggestion["comment"]:
            suggestion["comment"] += "\n" + comment_text
        else:
            suggestion["comment"] = comment_text
        save_data(data)

        try:
            await context.bot.send_message(
                chat_id=suggestion["user_id"],
                text=f"К вашему предложению №{suggestion_id} добавлен комментарий:\n{comment_text}",
            )
        except Exception as e:
            print(f"Ошибка при уведомлении пользователя: {e}")

        await update.message.reply_text(
            "Комментарий добавлен. Если хотите добавить ещё, напишите текст, "
            "или введите /done для завершения, /cancel для отмены."
        )
        return COMMENT_INPUT

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    menu = get_admin_menu() if is_admin(user_id) else get_user_menu()
    await update.message.reply_text("Действие отменено.", reply_markup=menu)
    
    context.user_data.pop("comment_for", None)
    context.user_data.pop("current_suggestion_id", None)

    return ConversationHandler.END

async def admin_comment_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    suggestion_id = context.user_data.pop("comment_for", None)
    await update.message.reply_text("Ввод комментария завершён.")
    if suggestion_id:
        await send_detailed_suggestion_message(update.message, context, suggestion_id)
        return VIEW_SUGGESTION
    else:
        user_id = update.effective_user.id
        menu = get_admin_menu() if is_admin(user_id) else get_user_menu()
        await update.message.reply_text("Произошла ошибка, возвращаемся в главное меню.", reply_markup=menu)
        return ConversationHandler.END

async def admin_comment_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    suggestion_id = context.user_data.pop("comment_for", None)
    await update.message.reply_text("Ввод комментария отменён.")
    if suggestion_id:
        await send_detailed_suggestion_message(update.message, context, suggestion_id)
        return VIEW_SUGGESTION
    else:
        user_id = update.effective_user.id
        menu = get_admin_menu() if is_admin(user_id) else get_user_menu()
        await update.message.reply_text("Произошла ошибка, возвращаемся в главное меню.", reply_markup=menu)
        return ConversationHandler.END

def main():
    if not BOT_TOKEN:
        print("ОШИБКА: BOT_TOKEN не установлен!")
        print("Пожалуйста, установите переменную окружения BOT_TOKEN в Secrets.")
        return
    
    if not ADMIN_IDS:
        print("ВНИМАНИЕ: ADMIN_IDS не установлен!")
        print("Пожалуйста, установите переменную окружения ADMIN_IDS в Secrets.")
        print("Формат: 1234567890,9876543210 (ID администраторов через запятую)")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^Посмотреть историю предложений$"), handle_user_menu))

    suggestion_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Подать предложение по улучшению$"), start_suggestion_flow)],
        states={
            SUGGESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_suggestion)],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )
    app.add_handler(suggestion_conv)

    admin_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Просмотреть все предложения$"), start_admin_suggestions)
        ],
        states={
            LIST_SUGGESTIONS: [
                CallbackQueryHandler(handle_list_suggestions_callbacks, pattern="^view_\\d+$")
            ],
            VIEW_SUGGESTION: [
                CallbackQueryHandler(handle_view_suggestion_callbacks, pattern="^(status_\\d+_.+|comment_\\d+|back_to_list)$")
            ],
            COMMENT_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, comment_text_handler),
                CommandHandler("cancel", admin_comment_cancel_handler),
                CommandHandler("done", admin_comment_done_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_handler),
            CommandHandler("start", cancel_handler)
        ],
    )
    app.add_handler(admin_conv)

    print("Бот запущен и готов к работе!")
    app.run_polling()

if __name__ == "__main__":
    main()
