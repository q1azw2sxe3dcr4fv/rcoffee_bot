import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database connection
def get_db_connection():
    conn = sqlite3.connect('coffedb.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Напитки", callback_data='drinks')],
        [InlineKeyboardButton("Десерты", callback_data='desserts')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f'Привет, {user.first_name}! Добро пожаловать в наше кафе. Что бы вы хотели посмотреть?',
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'drinks':
        await show_drink_categories(update, context)
    elif data == 'desserts':
        await show_dessert_categories(update, context)
    elif data == 'back_to_categories':
        await show_drink_categories(update, context)
    elif data == 'back_to_main_menu':
        await show_main_menu(update, context)
    elif data.startswith('category_'):
        category = data.split('_', 1)[1]
        await show_drinks_in_category(update, context, category)
    elif data.startswith('dessert_category_'):
        category = data.split('_', 2)[2]
        await show_desserts_in_category(update, context, category)
    elif data.startswith('dessert_'):
        dessert_id = data.split('_', 1)[1]
        await show_dessert_details(update, context, dessert_id)
    elif data == 'americano_options':
        await show_americano_options(update, context)
    elif data == 'all_americano_details':
        await show_all_americano_details(update, context)
    elif data.startswith('all_drink_details_'):
        drink_base = data.split('_', 3)[3]
        await show_all_drink_details(update, context, drink_base)
    elif data.startswith('drink_'):
        drink_id = data.split('_', 1)[1]
        await show_drink_details(update, context, drink_id)
    elif data.startswith('back_to_'):
        if data == 'back_to_coffee_classic':
            await show_drinks_in_category(update, context, 'coffee_classic')
        elif data == 'back_to_coffee_signature':
            await show_drinks_in_category(update, context, 'coffee_signature')
        elif data == 'back_to_desserts':
            await show_dessert_categories(update, context)
        else:
            category = data.split('_', 2)[2]
            await show_drinks_in_category(update, context, category)
    else:
        await query.edit_message_text(text=f"Неизвестная команда: {data}")

async def show_drink_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show drink categories."""
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM drinks")
        categories = cursor.fetchall()
        conn.close()
        
        # Create a dictionary to map database categories to display names
        category_names = {
            'coffee_classic': 'Классический кофе',
            'coffee_signature': 'Авторский кофе',
            'tea_regular': 'Чай',
            'tea_fruit': 'Фруктовый чай',
            'smoothie': 'Смузи',
            'lemonade': 'Лимонады',
            'coffee_milkshake': 'Кофейные милкшейки',
            'matcha': 'Матча'
        }
        
        keyboard = []
        for category in categories:
            cat = category['category']
            display_name = category_names.get(cat, cat)
            keyboard.append([InlineKeyboardButton(display_name, callback_data=f"category_{cat}")])
        
        # Добавляем кнопку "Назад" для возврата в главное меню
        keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_main_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="Выберите категорию напитков:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in show_drink_categories: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_drinks_in_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str) -> None:
    """Show drinks in the selected category."""
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем все напитки в категории
        cursor.execute("SELECT id, name, volume FROM drinks WHERE category = ?", (category,))
        drinks = cursor.fetchall()
        
        # Группируем напитки по базовому имени
        drink_groups = {}
        
        # Особая обработка для категории "Авторский кофе"
        if category == 'coffee_signature':
            for drink in drinks:
                drink_id = drink['id']
                # Для Латте разделяем по типу (малина-фиалка, груша-карамель)
                if drink_id.startswith('latte_'):
                    # Получаем полный базовый ID (например, latte_raspberry_violet или latte_pear_caramel)
                    parts = drink_id.split('_')
                    if len(parts) >= 3:
                        base_id = f"{parts[0]}_{parts[1]}_{parts[2]}"  # например, latte_raspberry_violet
                        if base_id not in drink_groups:
                            drink_groups[base_id] = []
                        drink_groups[base_id].append(drink)
                else:
                    # Для остальных напитков используем стандартную логику
                    if '_' in drink_id:
                        base_id = drink_id.split('_')[0]
                        if base_id not in drink_groups:
                            drink_groups[base_id] = []
                        drink_groups[base_id].append(drink)
                    else:
                        if drink_id not in drink_groups:
                            drink_groups[drink_id] = []
                        drink_groups[drink_id].append(drink)
        # Особая обработка для категории "Матча"
        elif category == 'matcha':
            for drink in drinks:
                drink_id = drink['id']
                # Используем полный ID как базовый для каждого напитка матчи
                if drink_id not in drink_groups:
                    drink_groups[drink_id] = []
                drink_groups[drink_id].append(drink)
        else:
            # Стандартная логика группировки для других категорий
            for drink in drinks:
                drink_id = drink['id']
                if '_' in drink_id:
                    base_id = drink_id.split('_')[0]
                    if base_id not in drink_groups:
                        drink_groups[base_id] = []
                    drink_groups[base_id].append(drink)
                else:
                    if drink_id not in drink_groups:
                        drink_groups[drink_id] = []
                    drink_groups[drink_id].append(drink)
        
        # Создаем словарь для отображения категорий
        category_names = {
            'coffee_classic': 'Классический кофе',
            'coffee_signature': 'Авторский кофе',
            'tea_regular': 'Чай',
            'tea_fruit': 'Фруктовый чай',
            'smoothie': 'Смузи',
            'lemonade': 'Лимонады',
            'coffee_milkshake': 'Кофейные милкшейки',
            'matcha': 'Матча'
        }
        
        keyboard = []
        
        # Для категории "Авторский кофе" используем особую логику отображения
        if category == 'coffee_signature':
            # Создаем кнопки для каждой группы напитков
            for base_id, variants in drink_groups.items():
                # Определяем отображаемое имя в зависимости от типа напитка
                if base_id.startswith('latte_raspberry_violet'):
                    display_name = "Латте малина-фиалка"
                elif base_id.startswith('latte_pear_caramel'):
                    display_name = "Латте груша-карамель"
                else:
                    # Используем полное название напитка
                    display_name = variants[0]['name']
                
                if len(variants) > 1:
                    # Если есть несколько вариантов, показываем одну кнопку для всех вариантов
                    keyboard.append([InlineKeyboardButton(display_name, callback_data=f"all_drink_details_{base_id}")])
                else:
                    # Если только один вариант, показываем кнопку для этого варианта
                    keyboard.append([InlineKeyboardButton(display_name, callback_data=f"drink_{variants[0]['id']}")])
        # Особая логика для категории "Матча"
        elif category == 'matcha':
            # Создаем отдельную кнопку для каждого напитка матчи
            for base_id, variants in drink_groups.items():
                # Используем полное название напитка
                display_name = variants[0]['name']
                keyboard.append([InlineKeyboardButton(display_name, callback_data=f"drink_{variants[0]['id']}")])
        else:
            # Стандартная логика для других категорий
            # Получаем базовые названия напитков для отображения
            cursor.execute("""
                SELECT DISTINCT SUBSTR(id, 1, INSTR(id || '_', '_') - 1) as base_id, 
                       MIN(name) as display_name
                FROM drinks 
                WHERE category = ?
                GROUP BY base_id
            """, (category,))
            base_drinks = cursor.fetchall()
            
            # Создаем кнопки для каждого базового напитка
            for base_drink in base_drinks:
                base_id = base_drink['base_id']
                display_name = base_drink['display_name']  # Используем полное название без объема
                
                # Проверяем, есть ли варианты для этого напитка
                variants = [d for d in drinks if d['id'] == base_id or d['id'].startswith(f"{base_id}_")]
                
                if len(variants) > 1:
                    # Если есть несколько вариантов, показываем одну кнопку для всех вариантов
                    keyboard.append([InlineKeyboardButton(display_name, callback_data=f"all_drink_details_{base_id}")])
                else:
                    # Если только один вариант, показываем кнопку для этого варианта
                    keyboard.append([InlineKeyboardButton(display_name, callback_data=f"drink_{variants[0]['id']}")])
        
        conn.close()
        
        keyboard.append([InlineKeyboardButton("Назад к категориям", callback_data='back_to_categories')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f'Напитки в категории "{category_names.get(category, category)}":',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in show_drinks_in_category: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_americano_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show different volume options for Americano."""
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, volume, category FROM drinks WHERE id LIKE 'americano_%'")
        americano_variants = cursor.fetchall()
        conn.close()
        
        if not americano_variants:
            await query.edit_message_text(text="Варианты Американо не найдены.")
            return
            
        # Получаем категорию для правильной навигации
        category = americano_variants[0]['category']
        
        keyboard = []
        for variant in americano_variants:
            keyboard.append([InlineKeyboardButton(variant['name'], callback_data=f"drink_{variant['id']}")])
        
        keyboard.append([InlineKeyboardButton("Назад", callback_data=f"back_to_{category}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="Выберите объем Американо:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in show_americano_options: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_all_americano_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show details of all Americano variants in sequence."""
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drinks WHERE id LIKE 'americano_%' ORDER BY volume")
        americano_variants = cursor.fetchall()
        conn.close()
        
        if not americano_variants:
            await query.edit_message_text(text="Варианты Американо не найдены.")
            return
        
        # Получаем категорию для правильной навигации
        category = americano_variants[0]['category']
        
        # Send each Americano variant as a separate message
        for i, variant in enumerate(americano_variants):
            # Format the details
            details = f"<b>{variant['name']}</b>\n\n"
            
            if variant['volume']:
                details += f"<b>Объем:</b> {variant['volume']}\n\n"
            
            if variant['ingredients']:
                details += f"<b>Состав:</b> {variant['ingredients']}\n\n"
            
            if variant['preparation']:
                details += f"<b>Приготовление:</b> {variant['preparation']}\n\n"
            
            # For the first message, edit the existing message
            if i == 0:
                await query.edit_message_text(
                    text=details,
                    parse_mode='HTML'
                )
            # For subsequent messages, send new messages
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=details,
                    parse_mode='HTML'
                )
        
        # Send a final message with a back button
        keyboard = [[InlineKeyboardButton("Назад", callback_data=f"back_to_{category}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Выше представлены все варианты Американо.",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in show_all_americano_details: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_drink_details(update: Update, context: ContextTypes.DEFAULT_TYPE, drink_id: str) -> None:
    """Show details of the selected drink."""
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drinks WHERE id = ?", (drink_id,))
        drink = cursor.fetchone()
        conn.close()
        
        if not drink:
            await query.edit_message_text(text="Напиток не найден.")
            return
        
        # Get the category name for the back button
        category = drink['category']
        
        # Format the details
        details = f"<b>{drink['name']}</b>\n\n"
        
        if drink['volume']:
            details += f"<b>Объем:</b> {drink['volume']}\n\n"
        
        if drink['ingredients']:
            details += f"<b>Состав:</b> {drink['ingredients']}\n\n"
        
        if drink['preparation']:
            details += f"<b>Приготовление:</b> {drink['preparation']}\n\n"
        
        # Удалено отображение описания
        # if drink['description']:
        #     details += f"<b>Описание:</b> {drink['description']}\n\n"
        
        # Create a back button
        # Special case for Americano variants
        if drink_id.startswith('americano_'):
            keyboard = [[InlineKeyboardButton("Назад к вариантам Американо", callback_data="americano_options")]]
        else:
            keyboard = [[InlineKeyboardButton("Назад", callback_data=f"back_to_{category}")]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=details,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in show_drink_details: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_all_drink_details(update: Update, context: ContextTypes.DEFAULT_TYPE, drink_base: str) -> None:
    """Show details of all variants of a drink in sequence."""
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drinks WHERE id = ? OR id LIKE ? ORDER BY volume", 
                      (drink_base, f"{drink_base}_%"))
        drink_variants = cursor.fetchall()
        conn.close()
        
        if not drink_variants:
            await query.edit_message_text(text="Варианты напитка не найдены.")
            return
        
        # Получаем базовое название напитка (без объема)
        base_name = drink_variants[0]['name'].split(' ')[0]
        
        # Получаем категорию напитка для правильной навигации
        category = drink_variants[0]['category']
        
        # Отправляем каждый вариант напитка как отдельное сообщение
        for i, variant in enumerate(drink_variants):
            # Форматируем детали
            details = f"<b>{variant['name']}</b>\n\n"
            
            if variant['volume']:
                details += f"<b>Объем:</b> {variant['volume']}\n\n"
            
            if variant['ingredients']:
                details += f"<b>Состав:</b> {variant['ingredients']}\n\n"
            
            if variant['preparation']:
                details += f"<b>Приготовление:</b> {variant['preparation']}\n\n"
            
            # Для первого сообщения редактируем существующее сообщение
            if i == 0:
                await query.edit_message_text(
                    text=details,
                    parse_mode='HTML'
                )
            # Для последующих сообщений отправляем новые
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=details,
                    parse_mode='HTML'
                )
        
        # Отправляем финальное сообщение с кнопкой "Назад"
        keyboard = [[InlineKeyboardButton("Назад", callback_data=f"back_to_{category}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Выше представлены все варианты {base_name}.",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in show_all_drink_details: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for drinks by name."""
    query_text = update.message.text.lower()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, volume FROM drinks WHERE LOWER(name) LIKE ?", (f"%{query_text}%",))
        drinks = cursor.fetchall()
        conn.close()
        
        if not drinks:
            await update.message.reply_text("Напитки не найдены. Попробуйте другой запрос.")
            return
        
        # Группируем напитки по базовому имени
        drink_groups = {}
        for drink in drinks:
            drink_id = drink['id']
            # Проверяем, является ли это вариантом с объемом (имеет '_' в id)
            if '_' in drink_id:
                base_id = drink_id.split('_')[0]
                if base_id not in drink_groups:
                    drink_groups[base_id] = []
                drink_groups[base_id].append(drink)
            else:
                # Это базовый напиток без вариантов
                if drink_id not in drink_groups:
                    drink_groups[drink_id] = []
                drink_groups[drink_id].append(drink)
        
        keyboard = []
        
        # Создаем кнопки для каждого найденного напитка/группы напитков
        for base_id, variants in drink_groups.items():
            if len(variants) > 1:
                # Если есть несколько вариантов, показываем одну кнопку для всех вариантов
                display_name = variants[0]['name']  # Используем полное название без объема
                keyboard.append([InlineKeyboardButton(display_name, callback_data=f"all_drink_details_{base_id}")])
            else:
                # Если только один вариант, показываем кнопку для этого варианта
                display_name = variants[0]['name']  # Используем полное название без объема
                keyboard.append([InlineKeyboardButton(display_name, callback_data=f"drink_{variants[0]['id']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=f'Результаты поиска для "{query_text}":',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in search: {e}")
        await update.message.reply_text(text=f"Произошла ошибка при поиске: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Используйте /start для начала работы с ботом.\n"
                                   "Вы также можете искать напитки, просто отправив их название.")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main menu with drinks and desserts options."""
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("Напитки", callback_data='drinks')],
        [InlineKeyboardButton("Десерты", callback_data='desserts')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text='Добро пожаловать в наше кафе. Что бы вы хотели посмотреть?',
        reply_markup=reply_markup
    )

async def show_dessert_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show dessert categories."""
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM desserts")
        categories = cursor.fetchall()
        conn.close()
        
        # Create a dictionary to map database categories to display names
        category_names = {
            'macarons': 'Макаруны',
            'shu': 'Шу',
            'tiramisu': 'Тирамису',
            'medovik': 'Медовик',
            'brownie': 'Брауни-картошка',
            'tart': 'Тарт цветок',
            'profiteroles': 'Белый с шоколадной стружкой'
            # Add more dessert categories as they are added
        }
        
        keyboard = []
        for category in categories:
            cat = category['category']
            display_name = category_names.get(cat, cat)
            keyboard.append([InlineKeyboardButton(display_name, callback_data=f"dessert_category_{cat}")])
        
        # Add a back button to return to the main menu
        keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_main_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="Выберите категорию десертов:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in show_dessert_categories: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_desserts_in_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str) -> None:
    """Show desserts in the selected category."""
    query = update.callback_query
    
    try:
        # Специальная обработка для категории "macarons"
        if category == 'macarons':
            # Сразу показываем информацию о макарунах
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM desserts WHERE id = 'macaron'")
            macaron = cursor.fetchone()
            conn.close()
            
            if not macaron:
                await query.edit_message_text(text="Информация о макарунах не найдена.")
                return
            
            # Format the details
            details = f"<b>{macaron['name']}</b>\n\n"
            
            if macaron['description']:
                details += f"{macaron['description']}\n\n"
            
            if macaron['ingredients']:
                details += f"<b>Состав:</b> {macaron['ingredients']}\n\n"
            
            if macaron['preparation']:
                details += f"<b>Вкусы:</b>\n{macaron['preparation']}\n\n"
            
            if macaron['shelf_life']:
                details += f"<b>Срок хранения:</b> {macaron['shelf_life']}\n\n"
            
            if macaron['storage_info']:
                details += f"<b>Хранение:</b> {macaron['storage_info']}\n\n"
            
            # Удалено отображение описания
            # if macaron['description']:
            #     details += f"<b>Описание:</b> {macaron['description']}\n\n"
            
            # Сначала отправляем фото с информацией без кнопок
            with open('macaron_image.jpg', 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=photo,
                    caption=details,
                    parse_mode='HTML'
                )
            
            # Затем отправляем отдельное сообщение с кнопкой "Назад"
            keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Нажмите кнопку ниже, чтобы вернуться к категориям десертов:",
                reply_markup=reply_markup
            )
            
            # Удаляем старое сообщение
            await query.message.delete()
            return
        
        # Специальная обработка для категории "shu"
        elif category == 'shu':
            # Сразу показываем информацию о шу
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM desserts WHERE id = 'shu'")
            shu = cursor.fetchone()
            conn.close()
            
            if not shu:
                await query.edit_message_text(text="Информация о шу не найдена.")
                return
            
            # Format the details
            details = f"<b>{shu['name']}</b>\n\n"
            
            if shu['description']:
                details += f"{shu['description']}\n\n"
            
            if shu['ingredients']:
                details += f"<b>Состав:</b>\n{shu['ingredients']}\n\n"
            
            if shu['preparation']:
                details += f"<b>Начинки:</b>\n{shu['preparation']}\n\n"
            
            if shu['shelf_life']:
                details += f"<b>Срок хранения:</b> {shu['shelf_life']}\n\n"
            
            if shu['storage_info']:
                details += f"<b>Хранение:</b> {shu['storage_info']}"
            
            # Затем отправляем отдельное сообщение с кнопкой "Назад"
            keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем фотографии в группе с описанием
            from telegram import InputMediaPhoto
            
            # Открываем файлы для чтения в бинарном режиме
            with open('shu_1.jpg', 'rb') as photo1_file, open('shu_2.jpg', 'rb') as photo2_file:
                # Создаем список медиа-объектов
                media_group = [
                    InputMediaPhoto(photo1_file, caption=details, parse_mode='HTML'),
                    InputMediaPhoto(photo2_file)
                ]
                
                # Отправляем группу медиа
                await context.bot.send_media_group(
                    chat_id=query.message.chat_id,
                    media=media_group
                )
            
            # Отправляем сообщение с кнопкой
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Нажмите кнопку ниже, чтобы вернуться к категориям десертов:",
                reply_markup=reply_markup
            )
            
            # Удаляем старое сообщение
            await query.message.delete()
            return
        
        # Специальная обработка для категории "tiramisu"
        elif category == 'tiramisu':
            # Сразу показываем информацию о тирамису
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM desserts WHERE id = 'tiramisu'")
            tiramisu = cursor.fetchone()
            conn.close()
            
            if not tiramisu:
                await query.edit_message_text(text="Информация о тирамису не найдена.")
                return
            
            # Format the details
            details = f"<b>{tiramisu['name']}</b>\n\n"
            
            if tiramisu['preparation']:
                details += f"{tiramisu['preparation']}\n\n"
            
            if tiramisu['ingredients']:
                details += f"<b>Состав:</b>\n{tiramisu['ingredients']}\n\n"
            
            # Затем отправляем отдельное сообщение с кнопкой "Назад"
            keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем фото с описанием
            try:
                with open('tiramisu.jpg', 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=details,
                        parse_mode='HTML'
                    )
                
                # Отправляем сообщение с кнопкой
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Нажмите кнопку ниже, чтобы вернуться к категориям десертов:",
                    reply_markup=reply_markup
                )
                
                # Удаляем старое сообщение
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error sending tiramisu image: {e}")
                # Если не удалось отправить изображение, просто показываем текст
                await query.edit_message_text(
                    text=f"{details}\n\n(Не удалось загрузить изображение)",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            return
        
        # Специальная обработка для категории "medovik"
        elif category == 'medovik':
            # Сразу показываем информацию о медовике
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM desserts WHERE id = 'medovik'")
            medovik = cursor.fetchone()
            conn.close()
            
            if not medovik:
                await query.edit_message_text(text="Информация о медовике не найдена.")
                return
            
            # Format the details
            details = f"<b>{medovik['name']}</b>\n\n"
            
            if medovik['preparation']:
                details += f"{medovik['preparation']}\n\n"
            
            if medovik['ingredients']:
                details += f"<b>Состав:</b>\n{medovik['ingredients']}\n\n"
            
            # Затем отправляем отдельное сообщение с кнопкой "Назад"
            keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем фото с описанием
            try:
                with open('medovik.jpg', 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=details,
                        parse_mode='HTML'
                    )
                
                # Отправляем сообщение с кнопкой
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Нажмите кнопку ниже, чтобы вернуться к категориям десертов:",
                    reply_markup=reply_markup
                )
                
                # Удаляем старое сообщение
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error sending medovik image: {e}")
                # Если не удалось отправить изображение, просто показываем текст
                await query.edit_message_text(
                    text=f"{details}\n\n(Не удалось загрузить изображение)",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            return
        
        # Специальная обработка для категории "brownie"
        elif category == 'brownie':
            # Сразу показываем информацию о брауни-картошке
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM desserts WHERE id = 'brownie'")
            brownie = cursor.fetchone()
            conn.close()
            
            if not brownie:
                await query.edit_message_text(text="Информация о брауни-картошке не найдена.")
                return
            
            # Format the details
            details = f"<b>{brownie['name']}</b>\n\n"
            
            if brownie['preparation']:
                details += f"{brownie['preparation']}\n\n"
            
            if brownie['ingredients']:
                details += f"<b>Состав:</b>\n{brownie['ingredients']}\n\n"
            
            if brownie['shelf_life']:
                details += f"<b>{brownie['shelf_life']}</b>\n"
            
            if brownie['storage_info']:
                details += f"{brownie['storage_info']}"
            
            # Затем отправляем отдельное сообщение с кнопкой "Назад"
            keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем фото с описанием
            try:
                with open('brauni_potaps.jpg', 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=details,
                        parse_mode='HTML'
                    )
                
                # Отправляем сообщение с кнопкой
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Нажмите кнопку ниже, чтобы вернуться к категориям десертов:",
                    reply_markup=reply_markup
                )
                
                # Удаляем старое сообщение
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error sending brownie image: {e}")
                # Если не удалось отправить изображение, просто показываем текст
                await query.edit_message_text(
                    text=f"{details}\n\n(Не удалось загрузить изображение)",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            return
        
        # Специальная обработка для категории "tart"
        elif category == 'tart':
            # Сразу показываем информацию о тарт цветке
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM desserts WHERE id = 'tart'")
            tart = cursor.fetchone()
            conn.close()
            
            if not tart:
                await query.edit_message_text(text="Информация о тарт цветке не найдена.")
                return
            
            # Format the details
            details = f"<b>{tart['name']}</b>\n\n"
            
            if tart['preparation']:
                details += f"{tart['preparation']}\n\n"
            
            if tart['ingredients']:
                details += f"<b>Состав:</b>\n{tart['ingredients']}\n\n"
            
            if tart['shelf_life']:
                details += f"<b>{tart['shelf_life']}</b>\n"
            
            if tart['storage_info']:
                details += f"{tart['storage_info']}"
            
            # Затем отправляем отдельное сообщение с кнопкой "Назад"
            keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем фото с описанием
            try:
                with open('tart.jpg', 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=details,
                        parse_mode='HTML'
                    )
                
                # Отправляем сообщение с кнопкой
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Нажмите кнопку ниже, чтобы вернуться к категориям десертов:",
                    reply_markup=reply_markup
                )
                
                # Удаляем старое сообщение
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error sending tart image: {e}")
                # Если не удалось отправить изображение, просто показываем текст
                await query.edit_message_text(
                    text=f"{details}\n\n(Не удалось загрузить изображение)",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            return
        
        # Специальная обработка для категории "profiteroles"
        elif category == 'profiteroles':
            # Сразу показываем информацию о профитролях
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM desserts WHERE id = 'profiteroles'")
            profiteroles = cursor.fetchone()
            conn.close()
            
            if not profiteroles:
                await query.edit_message_text(text="Информация о десерте 'Белый с шоколадной стружкой' не найдена.")
                return
            
            # Format the details
            details = f"<b>{profiteroles['name']}</b>\n\n"
            
            if profiteroles['ingredients']:
                details += f"{profiteroles['ingredients']}\n\n"
            
            if profiteroles['shelf_life']:
                details += f"{profiteroles['shelf_life']}\n\n"
            
            if profiteroles['storage_info']:
                details += f"{profiteroles['storage_info']}"
            
            # Затем отправляем отдельное сообщение с кнопкой "Назад"
            keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем фотографии в группе с описанием
            try:
                from telegram import InputMediaPhoto
                
                # Открываем файлы для чтения в бинарном режиме
                with open('whitebro.jpg', 'rb') as photo1_file, open('nenatural.jpg', 'rb') as photo2_file:
                    # Создаем список медиа-объектов
                    media_group = [
                        InputMediaPhoto(photo1_file, caption=details, parse_mode='HTML'),
                        InputMediaPhoto(photo2_file)
                    ]
                    
                    # Отправляем группу медиа
                    await context.bot.send_media_group(
                        chat_id=query.message.chat_id,
                        media=media_group
                    )
                
                # Отправляем сообщение с кнопкой
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Нажмите кнопку ниже, чтобы вернуться к категориям десертов:",
                    reply_markup=reply_markup
                )
                
                # Удаляем старое сообщение
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error sending profiteroles images: {e}")
                # Если не удалось отправить изображения, просто показываем текст
                await query.edit_message_text(
                    text=f"{details}\n\n(Не удалось загрузить изображения)",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all desserts in the category
        cursor.execute("SELECT id, name FROM desserts WHERE category = ?", (category,))
        desserts = cursor.fetchall()
        conn.close()
        
        # Create a dictionary to map database categories to display names
        category_names = {
            'macarons': 'Макаруны',
            'shu': 'Шу',
            'tiramisu': 'Тирамису',
            'medovik': 'Медовик',
            'brownie': 'Брауни-картошка',
            'tart': 'Тарт цветок',
            'profiteroles': 'Белый с шоколадной стружкой'
            # Add more dessert categories as they are added
        }
        
        keyboard = []
        for dessert in desserts:
            keyboard.append([InlineKeyboardButton(dessert['name'], callback_data=f"dessert_{dessert['id']}")])
        
        keyboard.append([InlineKeyboardButton("Назад к категориям десертов", callback_data='back_to_desserts')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f'Десерты в категории "{category_names.get(category, category)}":',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in show_desserts_in_category: {e}")
        try:
            await query.edit_message_text(text=f"Произошла ошибка: {e}")
        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Произошла ошибка при отображении десертов: {e}"
            )

async def show_dessert_details(update: Update, context: ContextTypes.DEFAULT_TYPE, dessert_id: str) -> None:
    """Show details of the selected dessert."""
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM desserts WHERE id = ?", (dessert_id,))
        dessert = cursor.fetchone()
        conn.close()
        
        if not dessert:
            await query.edit_message_text(text="Десерт не найден.")
            return
        
        # Get the category name for the back button
        category = dessert['category']
        
        # Format the details
        details = f"<b>{dessert['name']}</b>\n\n"
        
        if dessert['description']:
            details += f"{dessert['description']}\n\n"
        
        if dessert['ingredients']:
            details += f"<b>Состав:</b> {dessert['ingredients']}\n\n"
        
        if dessert['preparation']:
            details += f"<b>Вкусы:</b>\n{dessert['preparation']}\n\n"
        
        if dessert['shelf_life']:
            details += f"<b>Срок хранения:</b> {dessert['shelf_life']}\n\n"
        
        if dessert['storage_info']:
            details += f"<b>Хранение:</b> {dessert['storage_info']}\n\n"
        
        # Create a back button
        # Для макарунов используем 'back_to_desserts' вместо 'dessert_category_{category}'
        if dessert_id == 'macaron':
            keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
        else:
            keyboard = [[InlineKeyboardButton("Назад", callback_data=f"dessert_category_{category}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Special case for macaron - always use the macaron_image.jpg
        if dessert_id == 'macaron':
            try:
                # Отправляем фото с текстом и кнопкой в одном сообщении
                with open('macaron_image.jpg', 'rb') as photo:
                    # Создаем новое сообщение с фото и кнопкой
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=details,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                # Удаляем старое сообщение
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error sending macaron image: {e}")
                # Если не удалось отправить изображение, просто показываем текст
                await query.edit_message_text(
                    text=f"{details}\n\n(Не удалось загрузить изображение)",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        # Check if there's an image path and if it's not the macaron image
        elif dessert['image_path'] and dessert['image_path'] != 'macaron_image.jpg':
            # Send image with caption
            await query.message.reply_photo(
                photo=open(dessert['image_path'], 'rb'),
                caption=details,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            # Delete the original message
            await query.message.delete()
        else:
            # If no image or image doesn't exist, just send text
            await query.edit_message_text(
                text=details,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            # If the image is the one from the user's message, send it separately
            if dessert_id == 'macaron':
                # Use the photo from the user's message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Фото макарунов:",
                    parse_mode='HTML'
                )
    except Exception as e:
        logger.error(f"Error in show_dessert_details: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("7977642468:AAGhiLC1uEsscPjD9lcRwshJpQe5OYRcirQ").build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))
    
    # Add message handler for search
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot")
    application.run_polling()

if __name__ == '__main__':
    main()
