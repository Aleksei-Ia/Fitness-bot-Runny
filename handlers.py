import math
import re
import sqlite3
from datetime import datetime, timedelta
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from googletrans import Translator

from db import (
    get_user_data,
    create_or_update_user,
    log_water,
    log_food,
    log_workout
)
from weather_api import get_temperature, get_local_time_for_city
from nutrition_api import get_product_calories
from config import DB_NAME

router = Router()


class ProfileStates(StatesGroup):
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_activity = State()
    waiting_for_goal = State()
    waiting_for_city = State()


class FoodLogStates(StatesGroup):
    waiting_for_food_name = State()
    waiting_for_food_weight = State()
    waiting_for_manual_calorie = State()


class WaterLogStates(StatesGroup):
    waiting_for_amount = State()


class WorkoutStates(StatesGroup):
    waiting_for_workout_type = State()
    waiting_for_intensity = State()
    waiting_for_duration = State()


activity_factor = {
    'min': 1.2,
    'low': 1.375,
    'med': 1.55,
    'high': 1.725,
    'vhigh': 1.9
}

goal_factor = {
    'loss': 0.85,
    'maint': 1.0,
    'gain': 1.15
}

workout_alias = {
    'hodba': 'Ходьба',
    'beg': 'Бег',
    'velo': 'Езда на велосипеде',
    'ellip': 'Эллипсоид',
    'erg': 'Гребля',
    'step': 'Степпер',
    'hiit': 'HIIT',
    'hike': 'Пеший туризм',
    'yoga': 'Йога',
    'func': 'Функционально-силовая тренировка',
    'dance': 'Танцы',
    'recovery': 'Восстановление',
    'core': 'Кор-тренировка',
    'pilates': 'Пилатес',
    'taichi': 'Тайцзи',
    'swim': 'Плавание',
    'kick': 'Кикбоксинг'
}

workout_types = {
    'hodba': 4.0,
    'beg': 9.0,
    'velo': 8.0,
    'ellip': 6.0,
    'erg': 8.0,
    'step': 7.0,
    'hiit': 10.0,
    'hike': 5.0,
    'yoga': 4.0,
    'func': 7.0,
    'dance': 6.0,
    'recovery': 3.0,
    'core': 6.0,
    'pilates': 4.5,
    'taichi': 4.0,
    'swim': 8.0,
    'kick': 10.0
}

intensity_cal_factor = {
    'слабая': 0.8,
    'средняя': 1.0,
    'высокая': 1.2
}

intensity_water_bonus = {
    'слабая': 0.25,
    'средняя': 0.40,
    'высокая': 0.50
}


def main_menu_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='Вода', callback_data='CMD:/log_water'),
            InlineKeyboardButton(text='Еда', callback_data='CMD:/log_food'),
        ],
        [
            InlineKeyboardButton(text='Тренировка', callback_data='CMD:/log_workout'),
            InlineKeyboardButton(text='Прогресс', callback_data='CMD:/check_progress'),
        ],
        [
            InlineKeyboardButton(text='Графики', callback_data='CMD:/show_charts'),
            InlineKeyboardButton(text='Рекомендации', callback_data='CMD:/recommend'),
        ]
    ])
    return kb


def raw_bmr(weight, height, age, gender):
    if gender == 'м':
        return 10 * weight + 6.25 * height - 5 * age + 5
    elif gender == 'ж':
        return 10 * weight + 6.25 * height - 5 * age - 161
    else:
        return 10 * weight + 6.25 * height - 5 * age


def calculate_daily_calories(weight, height, age, gender, activity, goal):
    bmr_val = raw_bmr(weight, height, age, gender)
    act_mult = activity_factor.get(activity, 1.2)
    goal_mult = goal_factor.get(goal, 1.0)
    return bmr_val * act_mult * goal_mult


def calculate_daily_water(weight, activity_level, temp):
    base = weight * 30
    lvl_map = {
        'min': 0,
        'low': 30,
        'med': 60,
        'high': 90,
        'vhigh': 120
    }
    mins = lvl_map.get(activity_level, 30)
    extra_act = (mins // 30) * 500
    extra_weather = 500 if temp and temp > 25 else 0
    return base + extra_act + extra_weather


@router.message(Command('help'))
async def cmd_help(message: Message, bot: Bot):
    text = (
        'Доступные команды:\n'
        '/set_profile — настройка профиля\n'
        '/log_water — лог воды\n'
        '/log_food — лог еды\n'
        '/log_workout — лог тренировки\n'
        '/check_progress — прогресс\n'
        '/show_charts — графики за 7 дней\n'
        '/recommend — рекомендации\n'
        '/help — это сообщение'
    )
    await message.answer(text)


class ProfileStates(StatesGroup):
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_activity = State()
    waiting_for_goal = State()
    waiting_for_city = State()


async def set_profile_flow(bot: Bot, user_id: int, state: FSMContext):
    await bot.send_message(user_id, 'Введите ваш вес (кг):')
    await state.set_state(ProfileStates.waiting_for_weight)


@router.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user = get_user_data(message.from_user.id)
    if not user:
        await message.answer('Профиль не найден, давайте создадим!')
        await set_profile_flow(bot, message.from_user.id, state)
    else:
        await message.answer(
            'Добро пожаловать! Что хотите сделать?',
            reply_markup=main_menu_keyboard()
        )


@router.message(Command('set_profile'))
async def cmd_set_profile(message: Message, state: FSMContext, bot: Bot):
    await set_profile_flow(bot, message.from_user.id, state)


@router.message(ProfileStates.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext, bot: Bot):
    try:
        w = float(message.text)
    except ValueError:
        await message.answer('Введите число (кг).')
        return
    await state.update_data(weight=w)
    await message.answer('Введите ваш рост (см):')
    await state.set_state(ProfileStates.waiting_for_height)


@router.message(ProfileStates.waiting_for_height)
async def process_height(message: Message, state: FSMContext, bot: Bot):
    try:
        h = float(message.text)
    except ValueError:
        await message.answer('Введите число (см).')
        return
    await state.update_data(height=h)
    await message.answer('Введите ваш возраст (полных лет):')
    await state.set_state(ProfileStates.waiting_for_age)


@router.message(ProfileStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext, bot: Bot):
    try:
        a = int(message.text)
    except ValueError:
        await message.answer('Введите число (полных лет).')
        return
    await state.update_data(age=a)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='М', callback_data='G:м'),
            InlineKeyboardButton(text='Ж', callback_data='G:ж'),
            InlineKeyboardButton(text='Attack Helicopter', callback_data='G:attack')
        ]
    ])
    await message.answer('Выберите ваш пол:', reply_markup=kb)
    await state.set_state(ProfileStates.waiting_for_gender)


@router.callback_query(F.data.startswith('G:'))
async def callback_gender(callback: CallbackQuery, state: FSMContext, bot: Bot):
    gval = callback.data.split('G:')[1]
    if gval == 'attack':
        await state.update_data(gender='attack')
        await callback.message.answer('Я сомневаюсь что Вам действительно нужен этот бот... Но ок.')
    else:
        await state.update_data(gender=gval)
    await callback.answer()
    act_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='Минимальная', callback_data='ACT:min'),
            InlineKeyboardButton(text='Низкая', callback_data='ACT:low')
        ],
        [
            InlineKeyboardButton(text='Средняя', callback_data='ACT:med'),
            InlineKeyboardButton(text='Высокая', callback_data='ACT:high')
        ],
        [
            InlineKeyboardButton(text='Очень высокая', callback_data='ACT:vhigh')
        ]
    ])
    txt = (
        'Уровень активности:\n'
        'Минимальная: сидячая работа.\n'
        'Низкая: редкие тренировки.\n'
        'Средняя: 3-5 раз/нед.\n'
        'Высокая: 6-7 раз/нед.\n'
        'Очень высокая: 6+ раз/нед + физ.работа.\n'
    )
    await callback.message.answer(txt, reply_markup=act_kb)
    await state.set_state(ProfileStates.waiting_for_activity)


@router.callback_query(F.data.startswith('ACT:'))
async def callback_activity(callback: CallbackQuery, state: FSMContext, bot: Bot):
    act_val = callback.data.split('ACT:')[1]
    await state.update_data(activity_level=act_val)
    await callback.answer()
    goal_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='Похудение', callback_data='GOAL:loss'),
            InlineKeyboardButton(text='Поддержание', callback_data='GOAL:maint'),
            InlineKeyboardButton(text='Набор массы', callback_data='GOAL:gain')
        ]
    ])
    await callback.message.answer(
        'Какая цель?',
        reply_markup=goal_kb
    )
    await state.set_state(ProfileStates.waiting_for_goal)


@router.callback_query(F.data.startswith('GOAL:'))
async def callback_goal(callback: CallbackQuery, state: FSMContext, bot: Bot):
    g = callback.data.split('GOAL:')[1]
    await state.update_data(goal=g)
    await callback.answer()
    await callback.message.answer('В каком городе вы находитесь?')
    await state.set_state(ProfileStates.waiting_for_city)


@router.message(ProfileStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext, bot: Bot):
    c = message.text.strip()
    data = await state.get_data()
    create_or_update_user(
        user_id=message.from_user.id,
        weight=data['weight'],
        height=data['height'],
        age=data['age'],
        gender=data['gender'],
        activity_level=data['activity_level'],
        goal=data['goal'],
        city=c
    )
    await message.answer('Профиль сохранён! Что дальше?', reply_markup=main_menu_keyboard())
    await state.clear()


@router.message(Command('log_water'))
async def cmd_log_water(message: Message, bot: Bot, state: FSMContext):
    user = get_user_data(message.from_user.id)
    if not user:
        await message.answer('Нет профиля. Сначала /set_profile')
        return
    await log_water_command(bot, message.from_user.id, state)


@router.message(Command('log_food'))
async def cmd_log_food(message: Message, bot: Bot, state: FSMContext):
    user = get_user_data(message.from_user.id)
    if not user:
        await message.answer('Нет профиля. Сначала /set_profile')
        return
    await log_food_command(bot, message.from_user.id, state)


@router.message(Command('log_workout'))
async def cmd_log_workout(message: Message, bot: Bot, state: FSMContext):
    user = get_user_data(message.from_user.id)
    if not user:
        await message.answer('Нет профиля. Сначала /set_profile')
        return
    await log_workout_command(bot, message.from_user.id, state)


@router.message(Command('check_progress'))
async def cmd_check_progress(message: Message, bot: Bot):
    user = get_user_data(message.from_user.id)
    if not user:
        await message.answer('Нет профиля. Сначала /set_profile')
        return
    await show_progress(bot, message.from_user.id)


@router.message(Command('show_charts'))
async def cmd_show_charts(message: Message, bot: Bot):
    user = get_user_data(message.from_user.id)
    if not user:
        await message.answer('Нет профиля. Сначала /set_profile')
        return
    await show_charts(bot, message.from_user.id)


@router.message(Command('recommend'))
async def cmd_recommend(message: Message, bot: Bot):
    user = get_user_data(message.from_user.id)
    if not user:
        await message.answer('Нет профиля. Сначала /set_profile')
        return
    await cmd_recommend_menu(bot, message.from_user.id)


@router.callback_query(F.data.startswith('CMD:'))
async def callback_main_commands(callback: CallbackQuery, bot: Bot, state: FSMContext):
    cmd = callback.data.split('CMD:')[1]
    await callback.answer()
    uid = callback.from_user.id
    user = get_user_data(uid)
    if cmd in ['/log_water', '/log_food', '/log_workout', '/check_progress', '/show_charts', '/recommend'] and not user:
        await callback.message.answer('Нет профиля. Сначала /set_profile')
        return
    if cmd == '/log_water':
        await log_water_command(bot, uid, state)
    elif cmd == '/log_food':
        await log_food_command(bot, uid, state)
    elif cmd == '/log_workout':
        await log_workout_command(bot, uid, state)
    elif cmd == '/check_progress':
        await show_progress(bot, uid)
    elif cmd == '/show_charts':
        await show_charts(bot, uid)
    elif cmd == '/recommend':
        await cmd_recommend_menu(bot, uid)
    else:
        await callback.message.answer('Неизвестная команда.')


async def log_water_command(bot: Bot, user_id: int, state: FSMContext):
    await bot.send_message(user_id, 'Сколько воды (мл)?')
    await state.set_state(WaterLogStates.waiting_for_amount)


@router.message(WaterLogStates.waiting_for_amount)
async def process_water_amount(message: Message, bot: Bot, state: FSMContext):
    try:
        amt = float(message.text)
    except ValueError:
        await message.answer('Введите число (мл).')
        return
    log_water(message.from_user.id, amt)
    await message.answer(f'Записано {amt} мл воды.', reply_markup=main_menu_keyboard())
    await state.clear()


async def log_food_command(bot: Bot, user_id: int, state: FSMContext):
    await bot.send_message(user_id, 'Введите название продукта:')
    await state.set_state(FoodLogStates.waiting_for_food_name)


@router.message(FoodLogStates.waiting_for_food_name)
async def process_food_name(message: Message, bot: Bot, state: FSMContext):
    await state.update_data(food_name=message.text.strip())
    await message.answer('Сколько грамм?')
    await state.set_state(FoodLogStates.waiting_for_food_weight)


@router.message(FoodLogStates.waiting_for_food_weight)
async def process_food_weight(message: Message, bot: Bot, state: FSMContext):
    try:
        grams = float(message.text)
    except ValueError:
        await message.answer('Введите число (г).')
        return
    data = await state.get_data()
    pname = data['food_name']
    if re.search(r'[а-яА-Я]', pname):
        translator = Translator()
        en = translator.translate(pname, src='ru', dest='en').text
    else:
        en = pname
    kcal_100g = get_product_calories(en)
    if kcal_100g is None:
        await state.update_data(grams=grams)
        await message.answer(f'Не нашли "{pname}" ("{en}"). Введите ккал/100г вручную:')
        await state.set_state(FoodLogStates.waiting_for_manual_calorie)
        return
    total_kcal = (kcal_100g / 100.0) * grams
    log_food(message.from_user.id, pname, total_kcal, grams)
    await message.answer(f'Записано: {pname} — {total_kcal:.1f} ккал.', reply_markup=main_menu_keyboard())
    await state.clear()


@router.message(FoodLogStates.waiting_for_manual_calorie)
async def process_food_manual_cal(message: Message, bot: Bot, state: FSMContext):
    try:
        cals_100g = float(message.text)
    except ValueError:
        await message.answer('Введите число (ккал/100г).')
        return
    data = await state.get_data()
    pname = data['food_name']
    grams = data['grams']
    total_kcal = (cals_100g / 100.0) * grams
    log_food(message.from_user.id, pname, total_kcal, grams)
    await message.answer(f'Записано вручную: {pname} — {total_kcal:.1f} ккал.', reply_markup=main_menu_keyboard())
    await state.clear()


async def log_workout_command(bot: Bot, user_id: int, state: FSMContext):
    rows = []
    for alias, full_name in workout_alias.items():
        btn = InlineKeyboardButton(text=full_name, callback_data=f'WT:{alias}')
        rows.append([btn])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await bot.send_message(user_id, 'Выберите вид тренировки:', reply_markup=kb)
    await state.set_state(WorkoutStates.waiting_for_workout_type)


@router.callback_query(F.data.startswith('WT:'))
async def callback_workout_type(callback: CallbackQuery, bot: Bot, state: FSMContext):
    alias = callback.data.replace('WT:', '')
    await state.update_data(workout_alias=alias)
    await callback.answer()
    intens_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='Слабая', callback_data='INT:слабая'),
            InlineKeyboardButton(text='Средняя', callback_data='INT:средняя'),
            InlineKeyboardButton(text='Высокая', callback_data='INT:высокая')
        ]
    ])
    w_name = workout_alias[alias]
    await callback.message.answer(f'Тренировка: {w_name}\nВыберите интенсивность:', reply_markup=intens_kb)
    await state.set_state(WorkoutStates.waiting_for_intensity)


@router.callback_query(F.data.startswith('INT:'))
async def callback_workout_intensity(callback: CallbackQuery, bot: Bot, state: FSMContext):
    intens = callback.data.split('INT:')[1]
    await state.update_data(intensity=intens)
    await callback.answer()
    await callback.message.answer('Сколько минут тренировались?')
    await state.set_state(WorkoutStates.waiting_for_duration)


@router.message(WorkoutStates.waiting_for_duration)
async def process_workout_duration(message: Message, bot: Bot, state: FSMContext):
    try:
        dur = float(message.text)
    except ValueError:
        await message.answer('Введите число (минут).')
        return
    data = await state.get_data()
    alias = data['workout_alias']
    intens = data['intensity']
    user = get_user_data(message.from_user.id)
    if not user:
        await message.answer('Нет профиля. Сначала /set_profile')
        await state.clear()
        return
    weight = user[1]
    city = user[7] if len(user) >= 8 else None
    met = workout_types[alias]
    w_name = workout_alias[alias]
    base_burned = met * weight * (dur / 60.0)
    burned = base_burned * intensity_cal_factor[intens]
    log_workout(message.from_user.id, w_name, dur, burned)
    temp = get_temperature(city) if city else None
    water_loss = burned * (1 + intensity_water_bonus[intens])
    if temp and temp > 25:
        water_loss *= 1.15
    rec = ''
    if dur > 60:
        rec = '\nИспользуйте напитки с электролитами.'
    msg = (
        f'Тренировка: {w_name}\n'
        f'Интенсивность: {intens}\n'
        f'Продолжительность: {dur} мин\n\n'
        f'Сожжено: ~{burned:.0f} ккал.\n'
        f'Потеря жидкости: ~{water_loss:.0f} мл.'
        f'{rec}'
    )
    await message.answer(msg, reply_markup=main_menu_keyboard())
    await state.clear()


async def show_progress(bot: Bot, user_id: int):
    user = get_user_data(user_id)
    if not user:
        await bot.send_message(user_id, 'Нет профиля. /set_profile')
        return
    u_id = user[0]
    weight = user[1]
    height = user[2]
    age = user[3]
    gender = user[4]
    act_level = user[5]
    goal = user[6]
    city = user[7] if len(user) >= 8 else None
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    today_str = datetime.now().strftime('%Y-%m-%d')
    cur.execute('SELECT SUM(amount) FROM water_logs WHERE user_id=? AND date(timestamp)=?', (u_id, today_str))
    water_sum = cur.fetchone()[0] or 0
    cur.execute('SELECT SUM(calories) FROM food_logs WHERE user_id=? AND date(timestamp)=?', (u_id, today_str))
    food_sum = cur.fetchone()[0] or 0
    cur.execute('SELECT SUM(calories_burned) FROM workout_logs WHERE user_id=? AND date(timestamp)=?', (u_id, today_str))
    burned_sum = cur.fetchone()[0] or 0
    conn.close()
    temp = get_temperature(city) if city else None
    bmr_val = raw_bmr(weight, height, age, gender)
    daily_c = calculate_daily_calories(weight, height, age, gender, act_level, goal)
    goal_mult = goal_factor.get(goal, 1.0)
    burn_goal = daily_c - (bmr_val * goal_mult)
    water_need = calculate_daily_water(weight, act_level, temp)
    w_left = water_need - water_sum
    if w_left < 0:
        w_left = 0
    consume_left = daily_c - food_sum
    if consume_left < 0:
        consume_left = 0
    burn_left = burn_goal - burned_sum
    if burn_left < 0:
        burn_left = 0
    text = (
        f'Прогресс за сегодня {today_str}:\n\n'
        f'<b>Вода</b>:\n'
        f' - Выпито: {water_sum:.0f} мл / {water_need:.0f} мл\n'
        f' - Осталось: {w_left:.0f} мл\n\n'
        f'<b>Калории</b>:\n'
        f' - Потреблено: {food_sum:.0f} ккал\n'
        f' - Сожжено: {burned_sum:.0f} ккал\n'
        f' - Цель потребления: {daily_c:.0f} ккал\n'
        f' - Цель сжигания: {burn_goal:.0f} ккал\n'
        f' - Осталось потребить: {consume_left:.0f} ккал\n'
        f' - Осталось сжечь: {burn_left:.0f} ккал\n'
    )
    await bot.send_message(user_id, text, reply_markup=main_menu_keyboard())


async def show_charts(bot: Bot, user_id: int):
    user = get_user_data(user_id)
    if not user:
        await bot.send_message(user_id, 'Нет профиля. /set_profile')
        return
    city = user[7] if len(user) >= 8 else None
    local_now = get_local_time_for_city(city) if city else datetime.now()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    days_dt = []
    water_data = []
    eaten_data = []
    burned_data = []
    for i in range(7):
        local_day = local_now - timedelta(days=i)
        day_str = local_day.strftime('%Y-%m-%d')
        days_dt.append(local_day)
        cursor.execute('SELECT SUM(amount) FROM water_logs WHERE user_id=? AND date(timestamp)=?', (user_id, day_str))
        wsum = cursor.fetchone()[0] or 0
        water_data.append(wsum)
        cursor.execute('SELECT SUM(calories) FROM food_logs WHERE user_id=? AND date(timestamp)=?', (user_id, day_str))
        esum = cursor.fetchone()[0] or 0
        eaten_data.append(esum)
        cursor.execute('SELECT SUM(calories_burned) FROM workout_logs WHERE user_id=? AND date(timestamp)=?', (user_id, day_str))
        bsum = cursor.fetchone()[0] or 0
        burned_data.append(bsum)
    conn.close()
    days_dt.reverse()
    water_data.reverse()
    eaten_data.reverse()
    burned_data.reverse()
    fig, ax = plt.subplots(nrows=3, ncols=1, figsize=(6, 10))
    ax[0].plot(days_dt, water_data, marker='o', color='blue')
    ax[0].set_title('Вода (мл) за 7 дней')
    ax[0].grid(True)
    ax[0].tick_params(axis='x', rotation=45)
    ax[0].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax[1].plot(days_dt, eaten_data, marker='o', color='red')
    ax[1].set_title('Потреблённые ккал за 7 дней')
    ax[1].grid(True)
    ax[1].tick_params(axis='x', rotation=45)
    ax[1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax[2].plot(days_dt, burned_data, marker='o', color='green')
    ax[2].set_title('Сожжённые ккал за 7 дней')
    ax[2].grid(True)
    ax[2].tick_params(axis='x', rotation=45)
    ax[2].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.tight_layout()
    bio = BytesIO()
    plt.savefig(bio, format='png')
    bio.seek(0)
    plt.close(fig)
    chart_file = BufferedInputFile(bio.getvalue(), filename='progress.png')
    await bot.send_photo(user_id, chart_file, caption='Прогресс за 7 дней', reply_markup=main_menu_keyboard())


async def cmd_recommend_menu(bot: Bot, user_id: int):
    user = get_user_data(user_id)
    if not user:
        await bot.send_message(user_id, 'Нет профиля. /set_profile')
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='Еда', callback_data='RC:foods'),
        InlineKeyboardButton(text='Тренировки', callback_data='RC:workouts')
    ]])
    await bot.send_message(user_id, 'Что хотите узнать?', reply_markup=kb)


@router.callback_query(F.data.startswith('RC:'))
async def callback_recommend(callback: CallbackQuery, bot: Bot):
    choice = callback.data.split('RC:')[1]
    user = get_user_data(callback.from_user.id)
    if not user:
        await callback.message.answer('Нет профиля. Сначала /set_profile')
        await callback.answer()
        return
    (u_id, weight, height, age, gender, act_level, goal, city) = user[:8]
    daily_c = calculate_daily_calories(weight, height, age, gender, act_level, goal)
    bmr_val = raw_bmr(weight, height, age, gender)
    goal_mult = goal_factor.get(goal, 1.0)
    burn_goal = daily_c - (bmr_val * 1.2 * goal_mult)
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    today_str = datetime.now().strftime('%Y-%m-%d')
    cur.execute('SELECT SUM(calories) FROM food_logs WHERE user_id=? AND date(timestamp)=?', (u_id, today_str))
    food_sum = cur.fetchone()[0] or 0
    cur.execute('SELECT SUM(calories_burned) FROM workout_logs WHERE user_id=? AND date(timestamp)=?', (u_id, today_str))
    burned_sum = cur.fetchone()[0] or 0
    conn.close()
    local_now = get_local_time_for_city(city) if city else datetime.now()
    hour = local_now.hour
    temp = get_temperature(city) if city else None
    is_hot = (temp and temp > 25)
    partial_c = (daily_c / 18.0) * hour
    food_diff = partial_c - food_sum
    train_diff = burn_goal - burned_sum
    advice = ''
    if choice == 'foods':
        if food_diff < -300:
            advice += 'Вы уже опередили рекомендуемый график.\nЛёгкие блюда, овощи.\n'
            if is_hot:
                advice += 'Жара — холодный суп, вода с лимоном.\n'
        elif food_diff > 300:
            advice += 'Позади графика, можно добавить.\n'
            if hour < 11:
                advice += 'Сытный завтрак.\n'
            elif hour < 17:
                advice += 'Белки/углеводы.\n'
            else:
                advice += 'Вечером не переедаем.\n'
            if is_hot:
                advice += 'Пейте больше воды.\n'
        else:
            advice += 'В пределах рекомендуемого.\n'
            if hour > 18:
                advice += 'Вечером лёгкий приём.\n'
            else:
                advice += 'Сбалансированное питание.\n'
            if is_hot:
                advice += 'В жару больше воды.\n'
        await callback.message.answer(advice)
    elif choice == 'workouts':
        if train_diff < -300:
            advice += 'Цель сжигания перевыполнена.\n'
            if hour < 17:
                advice += 'Пробежка/ходьба.\n'
            else:
                advice += 'Вечером лёгкая йога.\n'
            if is_hot:
                advice += 'При жаре больше воды.\n'
        elif train_diff > 300:
            advice += 'Ещё не достигли цели сжигания.\n'
            if hour < 11:
                advice += 'Зарядка.\n'
            else:
                advice += 'Умеренная силовая или кардио.\n'
            if is_hot:
                advice += 'Лучше бассейн или прохлада.\nНе забудьте больше пить.\n'
        else:
            advice += 'В рамках цели.\n30-40 мин тренировки.\n'
            if is_hot:
                advice += 'Следите за питьевым режимом.\n'
        await callback.message.answer(advice)
    await callback.answer()
