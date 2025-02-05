import os

# токен бота от BotFather
BOT_TOKEN = os.getenv('BOT_TOKEN')

# API-ключ для OpenWeatherMap (получить на https://openweathermap.org/api)
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# API-ключ для USDA FoodData Central (получить на https://fdc.nal.usda.gov/)
USDA_API_KEY = os.getenv('USDA_API_KEY')

DB_NAME = os.getenv('DB_NAME', '/app/bot_database.db')
