"""
Start and Help Command Handlers.
Handles /start and /help commands using pyTelegramBotAPI.
"""

from telebot import types
from bot import bot
from utils.logging import logger
from utils.helpers import user_sessions
from config import BotMode, DEFAULT_MODE


@bot.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """Handle /start command."""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    logger.info(f"User {user_id} started the bot")
    
    # Initialize user session
    user_sessions.set_mode(user_id, DEFAULT_MODE)
    
    welcome_text = f"""👋 Здравствуйте, {user_name}!

Я — консультант **Забайкальской медиа группы**. Помогаю с выбором рекламных форматов (радио, портал ZAB.RU, ЗабТВ, соцсети) и записью на консультацию с менеджером.

🔤 **Текстовый режим** — диалог: уточняю ваши задачи и направляю к менеджеру
📚 **Режим RAG** — ответы строго по документам компании с указанием источника
🎤 **Голос** — можно общаться голосовыми сообщениями
📸 **Изображения** — анализ фото при необходимости

**Команды:** /help | /mode | /reset | /stats

Напишите, что хотите продвинуть и на каких площадках — подберём формат и запишем на консультацию."""
    
    await bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    """Handle /help command."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested help")
    
    help_text = """📖 **Консультант Забайкальской медиа группы**

**🔤 Текстовый режим (по умолчанию)**
Диалог как с консультантом: уточняю цели, формат (радио, ZAB.RU, ЗабТВ, соцсети) и географию. Цены и тарифы не обсуждаю — направляю к менеджеру для записи на консультацию.

**📚 Режим RAG (база знаний)**
/mode rag — ответы только на основе документов из data/documents/, с указанием источника. Если в базе нет ответа — предложу записаться к менеджеру.

**🎤 Голосовой режим**
Отправьте голосовое — распознаю, отвечу текстом и голосом.

**📸 Режим Vision**
Отправьте фото (при необходимости) — анализ изображения.

**⚙️ Команды:**
/mode text | rag | voice | vision — смена режима
/reset — очистить историю
/stats — статистика базы знаний (RAG)
/voice <имя> — выбор голоса (alloy, echo, nova и др.)

**💡 Примеры:**
• «Хочу рекламировать кафе в Чите»
• «Какие у вас форматы на радио?»
• В RAG: вопросы по загруженным документам компании"""
    
    await bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=['reset'])
async def cmd_reset(message: types.Message):
    """Handle /reset command - clear conversation history."""
    user_id = message.from_user.id
    
    user_sessions.clear_history(user_id)
    logger.info(f"User {user_id} cleared conversation history")
    
    await bot.send_message(
        message.chat.id,
        "✅ История диалога очищена!\n\n"
        "Начнем с чистого листа. Чем могу помочь?"
    )


@bot.message_handler(commands=['stats'])
async def cmd_stats(message: types.Message):
    """Handle /stats command - show knowledge base statistics."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested stats")
    
    try:
        from rag.query import get_knowledge_base_stats
        
        stats = get_knowledge_base_stats()
        
        if "error" in stats:
            await bot.send_message(
                message.chat.id,
                f"⚠️ Ошибка получения статистики:\n{stats['error']}"
            )
            return
        
        total_docs = stats.get("total_documents", 0)
        persist_dir = stats.get("persist_directory", "N/A")
        
        stats_text = f"""📊 **Статистика базы знаний**

📄 Документов в индексе: {total_docs}
💾 Директория: {persist_dir}

{"✅ База знаний готова к использованию!" if total_docs > 0 else "⚠️ База знаний пуста. Добавьте документы в data/documents/"}

Используйте /mode rag для работы с базой знаний."""
        
        await bot.send_message(message.chat.id, stats_text)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await bot.send_message(
            message.chat.id,
            "⚠️ Ошибка получения статистики базы знаний."
        )
