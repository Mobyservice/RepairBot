import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = '7786941832:AAHt5glecJPOkvNveniTb-Y_cy885SZwX1o'  # Замените на токен вашего бота

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

db_path = 'repairs.db'

class OrderForm(StatesGroup):
    client_name = State()
    client_phone = State()
    brand = State()
    model = State()
    repair_type = State()
    repair_price = State()
    prepayment = State()
    parts_cost = State()
    master_name = State()

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    buttons = [[KeyboardButton("📋 Новый заказ")], [KeyboardButton("🔍 Статус заказа")]]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Добро пожаловать. Выберите действие:", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "📋 Новый заказ")
async def new_order(message: types.Message):
    await message.answer("Введите имя клиента:")
    await OrderForm.client_name.set()

@dp.message_handler(state=OrderForm.client_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    await message.answer("Введите телефон клиента:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.client_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(client_phone=message.text)
    await message.answer("Введите бренд устройства:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.brand)
async def process_brand(message: types.Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await message.answer("Введите модель устройства:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.model)
async def process_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Введите вид ремонта:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.repair_type)
async def process_type(message: types.Message, state: FSMContext):
    await state.update_data(repair_type=message.text)
    await message.answer("Введите цену ремонта:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.repair_price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(repair_price=float(message.text))
    await message.answer("Введите задаток:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.prepayment)
async def process_prepayment(message: types.Message, state: FSMContext):
    await state.update_data(prepayment=float(message.text))
    await message.answer("Введите стоимость запчастей:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.parts_cost)
async def process_parts(message: types.Message, state: FSMContext):
    await state.update_data(parts_cost=float(message.text))
    await message.answer("Введите ваше имя (мастер):")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.master_name)
async def process_master(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    balance_due = data['repair_price'] - data['prepayment']

    cursor.execute("""
        INSERT INTO repairs (
            status, repair_type, brand, model, repair_price, prepayment,
            balance_due, parts_cost, client_name, client_phone, master_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "В работе", data['repair_type'], data['brand'], data['model'],
        data['repair_price'], data['prepayment'], balance_due, data['parts_cost'],
        data['client_name'], data['client_phone'], message.text
    ))
    conn.commit()
    conn.close()

    await message.answer("Заказ успешно добавлен!")
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "🔍 Статус заказа")
async def check_status(message: types.Message):
    await message.answer("Введите номер телефона клиента:")

@dp.message_handler()
async def search_order(message: types.Message):
    phone = message.text
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, brand, model, repair_type, repair_price, prepayment, balance_due, parts_cost FROM repairs WHERE client_phone = ? ORDER BY created_at DESC LIMIT 1", (phone,))
    row = cursor.fetchone()
    conn.close()

    if row:
        reply = f"📦 Заказ #{row[0]}\nСтатус: {row[1]}\nУстройство: {row[2]} {row[3]}\nРемонт: {row[4]}\nЦена: {row[5]}₽\nЗадаток: {row[6]}₽\nОстаток: {row[7]}₽\nЗапчасти: {row[8]}₽"
    else:
        reply = "Заказ не найден."

    await message.answer(reply)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
