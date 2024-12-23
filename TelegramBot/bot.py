import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, \
    CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

from TelegramBot import weather_client

API_TOKEN = '7630168834:AAEA5z37I3kQzpZEVNJZOmC4uUP5pMEMiU8'
WEATHER_API_TOKEN = 'YOUR_ACCUWEATHER_API_TOKEN'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

dp.include_router(router)

class RouteStates(StatesGroup):
    start_city = State()
    end_city = State()

@router.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer(
        "Привет! Я бот для прогноза погоды. "
        "Отправь /weather, чтобы получить прогноз для маршрута, или /help для справки."
    )

@router.message(Command("help"))
async def send_help(message: Message):
    await message.answer(
        "/weather - Получить прогноз погоды\n"
        "Введите начальную и конечную точки маршрута и выберите временной интервал прогноза (например, 3 дня или 5 дней)."
    )

@router.message(Command("weather"))
async def weather_command(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отправить местоположение", request_location=True)]])
    await message.answer("Введите начальный город для маршрута или отправьте своё местоположение:",
                         reply_markup=keyboard)
    await state.set_state(RouteStates.start_city)


@router.message(RouteStates.start_city)
async def process_start_city(message: Message, state: FSMContext):
    if message.location is not None:
        await state.update_data(start_city=f"GPS:{message.location.latitude},{message.location.longitude}")
    else:
        await state.update_data(start_city=message.text)
    await message.answer("Теперь введите конечный город:")
    await state.set_state(RouteStates.end_city)


@router.message(RouteStates.end_city)
async def process_end_city(message: Message, state: FSMContext):
    if message.location is not None:
        await state.update_data(end_city=f"GPS:{message.location.latitude},{message.location.longitude}")
    else:
        await state.update_data(end_city=message.text)
    await message.answer("Выберите временной интервал прогноза:", reply_markup=create_interval_keyboard())


def create_interval_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Прогноз на 3 дня", callback_data="interval_3"),
        InlineKeyboardButton(text="Прогноз на 5 дней", callback_data="interval_5")
    ]])
    return keyboard

def map_forecast_to_str(forecast, interval):
    result = ''
    for i in range(interval):
        day = forecast[i]
        result += (f'Дата: {day["date"].split('T')[0]}\n'
                   f'Температура: {round(day["temperature"], 2)}°C\n'
                   f'Вероятность осадков: {day["rain_percent"]}\n'
                   f'Влажность: {day["humidity"]}\n\n')
    return result

@router.callback_query()
async def interval_chosen(callback_query: CallbackQuery, state: FSMContext):
    interval = int(callback_query.data.split("_")[1])
    data = await state.get_data()
    start_city, end_city = data["start_city"], data["end_city"]

    start_forecast = ''
    end_forecast = ''

    if 'GPS' in start_city:
        start_forecast = weather_client.get_weather_from_location(start_city.split(':')[1].split(',')[0], start_city.split(':')[1].split(',')[1])
    else:
        start_forecast = weather_client.get_weather_from_city_name(start_city)

    if 'GPS' in end_city:
        end_forecast = weather_client.get_weather_from_location(end_city.split(':')[1].split(',')[0], end_city.split(':')[1].split(',')[1])
    else:
        end_forecast = weather_client.get_weather_from_city_name(end_city)

    if start_forecast is None:
        start_forecast = 'Не смогли определить погоду'
    else:
        start_forecast = map_forecast_to_str(start_forecast, interval)

    if end_forecast is None:
        end_forecast = 'Не смогли определить погоду'
    else:
        end_forecast = map_forecast_to_str(end_forecast, interval)

    await callback_query.message.answer(
        f"Прогноз для маршрута на {interval} дней:\n\n"
        f"Начальная точка:\n{start_forecast}\n\nКонечная точка:\n{end_forecast}"
    )
if __name__ == '__main__':
    dp.run_polling(bot, skip_updates=True)
