# Telegram Bot for Weight Management and Calorie Tracking

This Telegram bot allows you to set a goal for weight change and track the consumption and expenditure of calories and water.

## Main Bot Commands:

- **/set_profile** — Set or update profile data. It asks for weight, height, age, gender, activity level, and city.
- **/log_water** — Log water intake. Allows you to enter the amount of water (in ml) consumed.
- **/log_food** — Log food. Asks for the product and its weight. Displays the consumed calories. Product input is available in both English and Russian. If the product data is not available, it offers to manually enter the calorie count for the product.
- **/log_workout** — Log workout. You need to select the type of workout, intensity, and duration. It shows the calories burned and water consumption.
- **/check_progress** — Check the progress of water and calorie consumption, calories burned, and how much remains to reach the goal.
- **/show_charts** — Graphs of water and calorie consumption, as well as calories burned during workouts over the past 7 days.
- **/recommend** — Nutrition and workout recommendations based on the current calorie balance, time of day, and temperature in the selected city.
- **/help** — List of available commands.

## Project Structure:

```
├── Dockerfile  
├── config.py  
├── db.py  
├── handlers.py  
├── main.py  
├── nutrition_api.py  
├── requirements.txt  
└── weather_api.py
```

### Dockerfile  
A file with a set of instructions specifying how to create a Docker image to run the application. Based on python:3.11-slim, it installs dependencies from `requirements.txt`, copies all the code to `/app`, and runs the bot via `python main.py`.

### config.py  
Settings and secrets (or reading from environment variables).

### db.py  
File for working with a local SQLite database: creates tables (profile, water, food, workouts) and provides functions for writing/reading data.

### handlers.py  
File containing the main bot handlers and FSM logic:  
Profile setup, water logging, food logging, workouts logging, progress check, chart generation, recommendations.  
Uses the local database via functions from `db.py`.  
Integrated with external APIs:  
- Weather (OpenWeatherMap) to account for hot weather in calculations and advice.  
- Calorie information (USDA), including automatic translation of product names from Russian to English (via googletrans) for accurate search.  
Main commands:  
/help, /start, /log_water, /log_food, /log_workout, /check_progress, /show_charts, /recommend.  
User interaction via inline buttons.  
FSM states (ProfileStates, FoodLogStates, WaterLogStates, WorkoutStates) organize step-by-step data input.  
Recommendations are based on calorie balance, time of day, workout intensity, and local temperature.  
Charts are generated with matplotlib for the last 7 days (water, calories, calories burned) and displayed to the user as images.

### main.py  
The entry point for the bot:  
- Initializes the database: `db.init_db()`.  
- Creates bot and dispatcher objects (`aiogram`).  
- Connects the router from `handlers.py`.  
- Sets up middleware for message/button press logging.  
- Starts long-polling to allow the bot to handle commands and callbacks in real time.

### nutrition_api.py  
File responsible for retrieving product calorie data through USDA FoodData Central: sends a request by product name, parses the response, and returns the calorie value.

### requirements.txt  
List of Python dependencies.

### weather_api.py  
File for retrieving information about the current temperature and time in the given city via the OpenWeatherMap API: returns the temperature in °C and local time considering the timezone.

## Running Locally

1. Open a terminal and navigate to the root folder of the project.

2. Ensure that the file `config.py` contains all tokens and keys (`BOT_TOKEN`, `OPENWEATHER_API_KEY`, `USDA_API_KEY`), either reading from environment variables or set statically in the file.

3. Use the following commands:

### To build the image and run the bot:

```bash
docker build -t mybot .
docker run -d --name my_running_bot mybot
```

### Or, to save user data on the local machine:

```bash
docker run -d -v "/path/to/local/db/bot_database.db:/app/bot_database.db" --name my_running_bot mybot:latest
```

### To view logs:

```bash
docker logs -f my_running_bot
```
