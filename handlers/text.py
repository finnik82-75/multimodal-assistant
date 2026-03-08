"""
Text Message Handler.
Handles regular text messages from users using pyTelegramBotAPI.
"""

from telebot import types
from bot import bot
from services.router import route_text_request
from utils.logging import logger
from utils.helpers import user_sessions
from config import BotMode


@bot.message_handler(commands=['mode'])
async def cmd_mode(message: types.Message):
    """Handle /mode command - change bot mode."""
    user_id = message.from_user.id
    
    # Parse command arguments
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        # Show current mode and available modes
        current_mode = user_sessions.get_mode(user_id)
        
        mode_info = f"""🔧 **Текущий режим:** `{current_mode}`

**Доступные режимы:**

• `text` — консультант ЗМГ: диалог, выявление потребностей, запись к менеджеру
• `rag` — ответы только по документам из data/ с указанием источника
• `voice` — голосовые ответы
• `vision` — анализ изображений

**Использование:** /mode <режим>, например: /mode text или /mode rag"""
        
        await bot.send_message(message.chat.id, mode_info)
        return
    
    # Set new mode
    new_mode = args[1].lower()
    valid_modes = [BotMode.TEXT, BotMode.VOICE, BotMode.VISION, BotMode.RAG]
    
    if new_mode not in valid_modes:
        await bot.send_message(
            message.chat.id,
            f"❌ Неизвестный режим: `{new_mode}`\n\n"
            f"Доступные режимы: {', '.join(valid_modes)}"
        )
        return
    
    user_sessions.set_mode(user_id, new_mode)
    logger.info(f"User {user_id} switched to mode: {new_mode}")
    
    mode_descriptions = {
        BotMode.TEXT: "📝 Текстовый режим — диалог как с консультантом ЗМГ, выявление потребностей и запись на консультацию",
        BotMode.VOICE: "🎤 Голосовой режим — ответы голосом",
        BotMode.VISION: "📸 Режим Vision — анализ изображений",
        BotMode.RAG: "📚 Режим RAG — ответы строго по документам из базы знаний с указанием источника"
    }
    
    await bot.send_message(
        message.chat.id,
        f"✅ Режим изменен!\n\n{mode_descriptions[new_mode]}"
    )


@bot.message_handler(commands=['image'])
async def cmd_image(message: types.Message):
    """Handle /image command - generate image with specific parameters."""
    user_id = message.from_user.id
    
    # Parse command arguments
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        help_text = """🎨 **Генерация изображений**

**Автоматическая генерация:**
Просто напишите "Нарисуй...", "Создай изображение..." и ИИ автоматически создаст картинку.

**Примеры:**
• Нарисуй кота в космосе
• Создай изображение футуристического города
• Сгенерируй картинку заката на море

**Прямая команда:**
/image <описание>

Бот использует DALL-E 3 для создания изображений высокого качества."""
        
        await bot.send_message(message.chat.id, help_text)
        return
    
    prompt = args[1]
    
    logger.info(f"Direct image generation request from user {user_id}")
    
    # Show typing indicator
    await bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Generate image directly
        from services.router import route_image_generation_request
        from utils.helpers import cleanup_file
        
        response = await route_image_generation_request(
            user_id=user_id,
            prompt=prompt,
            original_text=prompt
        )
        
        # Send text response
        await bot.send_message(message.chat.id, response["text"])
        
        # Send image if generated successfully
        if response.get('has_image') and response.get('image_path'):
            await bot.send_chat_action(message.chat.id, 'upload_photo')
            
            image_path = response['image_path']
            try:
                with open(image_path, 'rb') as photo:
                    caption = response.get('revised_prompt', '')
                    if len(caption) > 1024:
                        caption = caption[:1021] + "..."
                    
                    await bot.send_photo(
                        message.chat.id,
                        photo,
                        caption=caption if caption else None
                    )
            finally:
                cleanup_file(image_path)
    
    except Exception as e:
        logger.error(f"Error in /image command: {e}", exc_info=True)
        await bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при генерации изображения.\n"
            "Попробуйте еще раз или перефразируйте запрос."
        )


@bot.message_handler(func=lambda message: message.content_type == 'text' and not message.text.startswith('/'))
async def handle_text_message(message: types.Message):
    """Handle regular text messages."""
    user_id = message.from_user.id
    text = message.text
    
    logger.info(f"Text message from user {user_id}: {text[:50]}...")
    
    # Show typing indicator
    await bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Route request
        response = await route_text_request(user_id, text)
        
        # Check if response contains an image
        if response.get('has_image') and response.get('image_path'):
            # Send text response first
            await bot.send_message(message.chat.id, response["text"])
            
            # Then send the generated image
            from utils.helpers import cleanup_file
            image_path = response['image_path']
            
            try:
                # Show uploading photo action
                await bot.send_chat_action(message.chat.id, 'upload_photo')
                
                # Send image
                with open(image_path, 'rb') as photo:
                    caption = response.get('revised_prompt', '')
                    if len(caption) > 1024:
                        caption = caption[:1021] + "..."
                    
                    await bot.send_photo(
                        message.chat.id, 
                        photo,
                        caption=caption if caption else None
                    )
                
                logger.info(f"Image sent to user {user_id}")
                
            finally:
                # Cleanup generated image file
                cleanup_file(image_path)
            
            return
        
        # Check mode for voice response
        mode = user_sessions.get_mode(user_id)
        
        if mode == BotMode.VOICE:
            # Generate voice response
            from services.tts import generate_voice_response
            from utils.helpers import cleanup_file
            
            voice_path = await generate_voice_response(
                response["text"],
                voice=user_sessions.get_voice(user_id)
            )
            
            try:
                # Send text first
                await bot.send_message(message.chat.id, response["text"])
                
                # Then send voice
                with open(voice_path, 'rb') as audio:
                    await bot.send_voice(message.chat.id, audio)
                
            finally:
                # Cleanup
                cleanup_file(voice_path)
        else:
            # Send text response
            await bot.send_message(message.chat.id, response["text"])
    
    except Exception as e:
        logger.error(f"Error handling text message: {e}", exc_info=True)
        await bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при обработке сообщения.\n"
            "Попробуйте еще раз или используйте /reset для сброса."
        )
