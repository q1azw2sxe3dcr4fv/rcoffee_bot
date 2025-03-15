import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect('coffedb.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

CATEGORY_NAMES = {
    'coffee_classic': 'Классический кофе',
    'coffee_signature': 'Авторский кофе',
    'tea_regular': 'Чай',
    'tea_fruit': 'Фруктовый чай',
    'smoothie': 'Смузи',
    'lemonade': 'Лимонады',
    'coffee_milkshake': 'Кофейные милкшейки',
    'matcha': 'Матча',
    'macarons': 'Макаруны',
    'shu': 'Шу',
    'tiramisu': 'Тирамису',
    'medovik': 'Медовик',
    'brownie': 'Брауни-картошка',
    'tart': 'Тарт цветок',
    'profiteroles': 'Белый с шоколадной стружкой'
}

DESSERT_IMAGES = {
    'macarons': ['macaron_image.jpg'],
    'shu': ['shu_1.jpg', 'shu_2.jpg'],
    'tiramisu': ['tiramisu.jpg'],
    'medovik': ['medovik.jpg'],
    'brownie': ['brauni_potaps.jpg'],
    'tart': ['tart.jpg'],
    'profiteroles': ['whitebro.jpg', 'nenatural.jpg']
}

DESSERT_IDS = {
    'macarons': 'macaron',
    'shu': 'shu',
    'tiramisu': 'tiramisu',
    'medovik': 'medovik',
    'brownie': 'brownie',
    'tart': 'tart',
    'profiteroles': 'profiteroles'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Напитки", callback_data='drinks')],
        [InlineKeyboardButton("Десерты", callback_data='desserts')]
    ]
    await update.message.reply_text(
        f'Привет, {user.first_name}! Добро пожаловать в наше кафе. Что бы вы хотели посмотреть?',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Напитки", callback_data='drinks')],
        [InlineKeyboardButton("Десерты", callback_data='desserts')]
    ]
    await query.edit_message_text(
        text='Добро пожаловать в наше кафе. Что бы вы хотели посмотреть?',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    elif data == 'americano_options':
        await show_americano_options(update, context)
    elif data == 'all_americano_details':
        await show_all_americano_details(update, context)
    elif data == 'back_to_desserts':
        await show_dessert_categories(update, context)
    elif data.startswith('category_'):
        category = data.split('_', 1)[1]
        await show_drinks_in_category(update, context, category)
    elif data.startswith('dessert_category_'):
        category = data.split('_', 2)[2]
        await show_desserts_in_category(update, context, category)
    elif data.startswith('dessert_'):
        dessert_id = data.split('_', 1)[1]
        await show_dessert_details(update, context, dessert_id)
    elif data.startswith('all_drink_details_'):
        drink_base = data.split('_', 3)[3]
        await show_all_drink_details(update, context, drink_base)
    elif data.startswith('drink_'):
        drink_id = data.split('_', 1)[1]
        await show_drink_details(update, context, drink_id)
    elif data.startswith('back_to_'):
        category = data.split('_', 2)[2]
        await show_drinks_in_category(update, context, category)
    else:
        await query.edit_message_text(text=f"Неизвестная команда: {data}")

async def show_drink_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM drinks")
        categories = cursor.fetchall()
        conn.close()
        
        keyboard = []
        for category in categories:
            cat = category['category']
            display_name = CATEGORY_NAMES.get(cat, cat)
            keyboard.append([InlineKeyboardButton(display_name, callback_data=f"category_{cat}")])
        
        keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_main_menu')])
        
        await query.edit_message_text(
            text="Выберите категорию напитков:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in show_drink_categories: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_drinks_in_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str) -> None:
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, volume FROM drinks WHERE category = ?", (category,))
        drinks = cursor.fetchall()
        
        drink_groups = {}
        
        if category == 'coffee_signature':
            for drink in drinks:
                drink_id = drink['id']
                if drink_id.startswith('latte_'):
                    parts = drink_id.split('_')
                    if len(parts) >= 3:
                        base_id = f"{parts[0]}_{parts[1]}_{parts[2]}"
                        if base_id not in drink_groups:
                            drink_groups[base_id] = []
                        drink_groups[base_id].append(drink)
                else:
                    if '_' in drink_id:
                        base_id = drink_id.split('_')[0]
                        if base_id not in drink_groups:
                            drink_groups[base_id] = []
                        drink_groups[base_id].append(drink)
                    else:
                        if drink_id not in drink_groups:
                            drink_groups[drink_id] = []
                        drink_groups[drink_id].append(drink)
        elif category == 'matcha':
            for drink in drinks:
                drink_id = drink['id']
                if drink_id not in drink_groups:
                    drink_groups[drink_id] = []
                drink_groups[drink_id].append(drink)
        else:
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
        
        keyboard = []
        
        if category == 'coffee_signature':
            for base_id, variants in drink_groups.items():
                if base_id.startswith('latte_raspberry_violet'):
                    display_name = "Латте малина-фиалка"
                elif base_id.startswith('latte_pear_caramel'):
                    display_name = "Латте груша-карамель"
                else:
                    display_name = variants[0]['name']
                
                if len(variants) > 1:
                    keyboard.append([InlineKeyboardButton(display_name, callback_data=f"all_drink_details_{base_id}")])
                else:
                    keyboard.append([InlineKeyboardButton(display_name, callback_data=f"drink_{variants[0]['id']}")])
        elif category == 'matcha':
            for base_id, variants in drink_groups.items():
                display_name = variants[0]['name']
                keyboard.append([InlineKeyboardButton(display_name, callback_data=f"drink_{variants[0]['id']}")])
        else:
            cursor.execute("""
                SELECT DISTINCT SUBSTR(id, 1, INSTR(id || '_', '_') - 1) as base_id, 
                       MIN(name) as display_name
                FROM drinks 
                WHERE category = ?
                GROUP BY base_id
            """, (category,))
            base_drinks = cursor.fetchall()
            
            for base_drink in base_drinks:
                base_id = base_drink['base_id']
                display_name = base_drink['display_name']
                
                variants = [d for d in drinks if d['id'] == base_id or d['id'].startswith(f"{base_id}_")]
                
                if len(variants) > 1:
                    keyboard.append([InlineKeyboardButton(display_name, callback_data=f"all_drink_details_{base_id}")])
                else:
                    keyboard.append([InlineKeyboardButton(display_name, callback_data=f"drink_{variants[0]['id']}")])
        
        conn.close()
        
        keyboard.append([InlineKeyboardButton("Назад к категориям", callback_data='back_to_categories')])
        
        await query.edit_message_text(
            text=f'Напитки в категории "{CATEGORY_NAMES.get(category, category)}":',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in show_drinks_in_category: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_americano_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            
        category = americano_variants[0]['category']
        
        keyboard = []
        for variant in americano_variants:
            keyboard.append([InlineKeyboardButton(variant['name'], callback_data=f"drink_{variant['id']}")])
        
        keyboard.append([InlineKeyboardButton("Назад", callback_data=f"back_to_{category}")])
        
        await query.edit_message_text(
            text="Выберите объем Американо:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in show_americano_options: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_drink_details(update: Update, context: ContextTypes.DEFAULT_TYPE, drink_id: str) -> None:
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
        
        category = drink['category']
        
        details = f"<b>{drink['name']}</b>\n\n"
        
        if drink['volume']:
            details += f"<b>Объем:</b> {drink['volume']}\n\n"
        
        if drink['ingredients']:
            details += f"<b>Состав:</b> {drink['ingredients']}\n\n"
        
        if drink['preparation']:
            details += f"<b>Приготовление:</b> {drink['preparation']}\n\n"
        
        if drink_id.startswith('americano_'):
            keyboard = [[InlineKeyboardButton("Назад к вариантам Американо", callback_data="americano_options")]]
        else:
            keyboard = [[InlineKeyboardButton("Назад", callback_data=f"back_to_{category}")]]
        
        await query.edit_message_text(
            text=details,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in show_drink_details: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_all_americano_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        
        category = americano_variants[0]['category']
        
        for i, variant in enumerate(americano_variants):
            details = f"<b>{variant['name']}</b>\n\n"
            
            if variant['volume']:
                details += f"<b>Объем:</b> {variant['volume']}\n\n"
            
            if variant['ingredients']:
                details += f"<b>Состав:</b> {variant['ingredients']}\n\n"
            
            if variant['preparation']:
                details += f"<b>Приготовление:</b> {variant['preparation']}\n\n"
            
            if i == 0:
                await query.edit_message_text(text=details, parse_mode='HTML')
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=details,
                    parse_mode='HTML'
                )
        
        keyboard = [[InlineKeyboardButton("Назад", callback_data=f"back_to_{category}")]]
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Выше представлены все варианты Американо.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in show_all_americano_details: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def show_all_drink_details(update: Update, context: ContextTypes.DEFAULT_TYPE, drink_base: str) -> None:
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
        
        base_name = drink_variants[0]['name'].split(' ')[0]
        category = drink_variants[0]['category']
        
        for i, variant in enumerate(drink_variants):
            details = f"<b>{variant['name']}</b>\n\n"
            
            if variant['volume']:
                details += f"<b>Объем:</b> {variant['volume']}\n\n"
            
            if variant['ingredients']:
                details += f"<b>Состав:</b> {variant['ingredients']}\n\n"
            
            if variant['preparation']:
                details += f"<b>Приготовление:</b> {variant['preparation']}\n\n"
            
            if i == 0:
                await query.edit_message_text(text=details, parse_mode='HTML')
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=details,
                    parse_mode='HTML'
                )
        
        keyboard = [[InlineKeyboardButton("Назад", callback_data=f"back_to_{category}")]]
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Выше представлены все варианты {base_name}.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in show_all_drink_details: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        
        drink_groups = {}
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
        
        keyboard = []
        
        for base_id, variants in drink_groups.items():
            if len(variants) > 1:
                display_name = variants[0]['name']
                keyboard.append([InlineKeyboardButton(display_name, callback_data=f"all_drink_details_{base_id}")])
            else:
                display_name = variants[0]['name']
                keyboard.append([InlineKeyboardButton(display_name, callback_data=f"drink_{variants[0]['id']}")])
        
        await update.message.reply_text(
            text=f'Результаты поиска для "{query_text}":',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in search: {e}")
        await update.message.reply_text(text=f"Произошла ошибка при поиске: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Используйте /start для начала работы с ботом.\n"
                                   "Вы также можете искать напитки, просто отправив их название.")

async def show_dessert_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM desserts")
        categories = cursor.fetchall()
        conn.close()
        
        keyboard = []
        for category in categories:
            cat = category['category']
            display_name = CATEGORY_NAMES.get(cat, cat)
            keyboard.append([InlineKeyboardButton(display_name, callback_data=f"dessert_category_{cat}")])
        
        keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_main_menu')])
        
        await query.edit_message_text(
            text="Выберите категорию десертов:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in show_dessert_categories: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

async def handle_special_dessert(update, context, dessert_id, image_files):
    query = update.callback_query
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM desserts WHERE id = ?", (DESSERT_IDS[dessert_id],))
        dessert = cursor.fetchone()
        conn.close()
        
        if not dessert:
            await query.edit_message_text(text=f"Информация о десерте не найдена.")
            return
        
        details = f"<b>{dessert['name']}</b>\n\n"
        
        if dessert['description']:
            details += f"{dessert['description']}\n\n"
        
        if dessert['ingredients']:
            details += f"<b>Состав:</b> {dessert['ingredients']}\n\n"
        
        if dessert['preparation']:
            field_name = "Вкусы:" if dessert_id == "macarons" else "Начинки:" if dessert_id == "shu" else ""
            details += f"<b>{field_name}</b>\n{dessert['preparation']}\n\n"
        
        if dessert['shelf_life']:
            details += f"<b>Срок хранения:</b> {dessert['shelf_life']}\n\n"
        
        if dessert['storage_info']:
            details += f"<b>Хранение:</b> {dessert['storage_info']}"
        
        keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if len(details) > 1024:
            if len(image_files) > 1:
                with open(image_files[0], 'rb') as photo1_file, open(image_files[1], 'rb') as photo2_file:
                    media_group = [
                        InputMediaPhoto(photo1_file),
                        InputMediaPhoto(photo2_file)
                    ]
                    await context.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
            else:
                with open(image_files[0], 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo
                    )
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=details,
                parse_mode='HTML'
            )
        else:
            if len(image_files) > 1:
                with open(image_files[0], 'rb') as photo1_file, open(image_files[1], 'rb') as photo2_file:
                    media_group = [
                        InputMediaPhoto(photo1_file, caption=details, parse_mode='HTML'),
                        InputMediaPhoto(photo2_file)
                    ]
                    await context.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
            else:
                with open(image_files[0], 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=details,
                        parse_mode='HTML'
                    )
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Нажмите кнопку ниже, чтобы вернуться к категориям десертов:",
            reply_markup=reply_markup
        )
        
        await query.message.delete()
    except Exception as e:
        logger.error(f"Error in handle_special_dessert: {e}")
        await query.edit_message_text(
            text=f"Произошла ошибка: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]])
        )

async def show_desserts_in_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str) -> None:
    query = update.callback_query
    
    try:
        if category in DESSERT_IMAGES:
            await handle_special_dessert(update, context, category, DESSERT_IMAGES[category])
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM desserts WHERE category = ?", (category,))
        desserts = cursor.fetchall()
        conn.close()
        
        keyboard = []
        for dessert in desserts:
            keyboard.append([InlineKeyboardButton(dessert['name'], callback_data=f"dessert_{dessert['id']}")])
        
        keyboard.append([InlineKeyboardButton("Назад к категориям десертов", callback_data='back_to_desserts')])
        
        await query.edit_message_text(
            text=f'Десерты в категории "{CATEGORY_NAMES.get(category, category)}":',
            reply_markup=InlineKeyboardMarkup(keyboard)
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
        
        category = dessert['category']
        
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
        
        if dessert_id == 'macaron':
            keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_desserts')]]
        else:
            keyboard = [[InlineKeyboardButton("Назад", callback_data=f"dessert_category_{category}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Проверяем длину текста для подписи к фото
        if len(details) > 1024:
            # Если текст слишком длинный, отправляем его отдельно
            if dessert_id == 'macaron':
                try:
                    with open('macaron_image.jpg', 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=photo
                        )
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=details,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                    await query.message.delete()
                except Exception as e:
                    logger.error(f"Error sending macaron image: {e}")
                    await query.edit_message_text(
                        text=f"{details}\n\n(Не удалось загрузить изображение)",
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            elif dessert['image_path'] and dessert['image_path'] != 'macaron_image.jpg':
                await query.message.reply_photo(
                    photo=open(dessert['image_path'], 'rb'),
                    caption="Фото десерта"
                )
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=details,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                await query.message.delete()
            else:
                await query.edit_message_text(
                    text=details,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            # Если текст не слишком длинный, отправляем его вместе с фото
            if dessert_id == 'macaron':
                try:
                    with open('macaron_image.jpg', 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=photo,
                            caption=details,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                    await query.message.delete()
                except Exception as e:
                    logger.error(f"Error sending macaron image: {e}")
                    await query.edit_message_text(
                        text=f"{details}\n\n(Не удалось загрузить изображение)",
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            elif dessert['image_path'] and dessert['image_path'] != 'macaron_image.jpg':
                await query.message.reply_photo(
                    photo=open(dessert['image_path'], 'rb'),
                    caption=details,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                await query.message.delete()
            else:
                await query.edit_message_text(
                    text=details,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                
                if dessert_id == 'macaron':
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text="Фото макарунов:",
                        parse_mode='HTML'
                    )
    except Exception as e:
        logger.error(f"Error in show_dessert_details: {e}")
        await query.edit_message_text(text=f"Произошла ошибка: {e}")

def main() -> None:
    application = Application.builder().token("7977642468:AAGhiLC1uEsscPjD9lcRwshJpQe5OYRcirQ").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    logger.info("Starting bot")
    application.run_polling()

if __name__ == '__main__':
    main()
