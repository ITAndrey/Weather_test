import os
import logging
import psycopg2
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки подключения к PostgreSQL
DB_HOST = 'db'
DB_NAME = 'weather_test'
DB_USER = 'admin'
DB_PASSWORD = '89562876'
DB_PORT = '5432'

# Создание соединения с БД
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

# Функция для получения погоды из OpenWeather
async def get_weather(city_name: str) -> dict:
    api_key = '8d9b2728bd31be415ec496cb18419ca7'  # Замените на ваш API ключ
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        logger.info(f"Weather data for {city_name}: {response.json()}")
        return response.json()
    else:
        logger.warning(f"Failed to get weather data for {city_name}, status code: {response.status_code}")
        return None

# Создание клавиатуры
def create_keyboard():
    keyboard = [
        [InlineKeyboardButton("Узнать погоду", callback_data='weather')],
        [InlineKeyboardButton("История запросов", callback_data='history')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Добро пожаловать! Выберите действие:', reply_markup=create_keyboard())

# Обработка сообщения с городом
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    city_name = update.message.text.strip()
    weather_data = await get_weather(city_name)

    if weather_data:
        temperature = int(weather_data['main']['temp'])
        pressure = int(weather_data['main']['pressure'])
        wind_speed = int(weather_data['wind']['speed'])

        await update.message.reply_text(f"Температура: {temperature}°C\n"
                                        f"Атмосферное давление: {pressure} мм рт. ст.\n"
                                        f"Скорость ветра: {wind_speed} м/с",
                                        reply_markup=create_keyboard())

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Сохраняем город в базе данных, если он еще не существует
            cursor.execute("INSERT INTO weather_app_city (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id;", (city_name,))
            city_id = cursor.fetchone()  # Получаем id вставленного города

            if city_id is None:
                # Если город уже существует, получаем его id
                cursor.execute("SELECT id FROM weather_app_city WHERE name = %s;", (city_name,))
                city_id = cursor.fetchone()[0]  # Получаем id существующего города

            # Сохраняем запрос в таблице weather_app_weatherrequest
            cursor.execute(
                "INSERT INTO weather_app_weatherrequest (timestamp, request_type, city_id) "
                "VALUES (%s, %s, %s);",
                (datetime.now(), 'telegram', city_id)
            )
            connection.commit()
            logger.info(f"Weather request saved for city ID: {city_id}")  # Логируем успешное сохранение запроса

        except Exception as e:
            logger.error(f"Ошибка при добавлении в базу данных: {e}")
            await update.message.reply_text("Произошла ошибка при сохранении запроса в базе данных.", reply_markup=create_keyboard())
        
        finally:
            cursor.close()
            connection.close()

    else:
        await update.message.reply_text("Город не найден. Пожалуйста, попробуйте снова.", reply_markup=create_keyboard())


# Показ истории запросов
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()  # Подтверждение нажатия кнопки
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT wr.id, c.name, wr.timestamp "
                       "FROM weather_app_weatherrequest wr "
                       "JOIN weather_app_city c ON wr.city_id = c.id "
                       "ORDER BY wr.timestamp DESC;")
        requests = cursor.fetchall()
        cursor.close()
        connection.close()

        if requests:
            history_text = "История запросов:\n"
            for request in requests:
                history_text += f"{request[0]}: Город - {request[1]}, Время - {request[2]}\n"
            await update.callback_query.message.reply_text(history_text + "\nЧтобы удалить запрос, введите команду /delete <номер запроса>.", reply_markup=create_keyboard())
        else:
            await update.callback_query.message.reply_text("История запросов пуста.", reply_markup=create_keyboard())
    except Exception as e:
        logger.error(f"Ошибка при получении истории запросов: {e}")
        await update.callback_query.message.reply_text("Произошла ошибка при получении истории запросов.", reply_markup=create_keyboard())

# Обработка нажатия кнопки "Узнать погоду"
async def weather_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()  # Подтверждение нажатия кнопки
    await update.callback_query.message.reply_text("Введите название города:", reply_markup=create_keyboard())

# Удаление записи из истории
async def delete_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        request_id = context.args[0]
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM weather_app_weatherrequest WHERE id = %s;", (request_id,))
        connection.commit()
        cursor.close()
        connection.close()
        await update.message.reply_text(f"Запрос с ID {request_id} был удалён.", reply_markup=create_keyboard())
    else:
        await update.message.reply_text("Пожалуйста, укажите номер запроса для удаления.", reply_markup=create_keyboard())

# Основная функция
def main() -> None:
    app = ApplicationBuilder().token('7434664290:AAGPwE_txaYq8XLTNmS5IRQCAd1nmNfefnQ').build()  # Замените на ваш токен

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(weather_callback, pattern='weather'))
    app.add_handler(CallbackQueryHandler(show_history, pattern='history'))
    app.add_handler(CommandHandler('delete', delete_request))  # Добавляем обработчик для команды удаления

    app.run_polling()

if __name__ == '__main__':
    main()
