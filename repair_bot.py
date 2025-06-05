import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import filters
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

db_path = 'repairs.db'

# ---------- FSM для добавления заказа ----------
class OrderForm(StatesGroup):
    status = State()
    repair_type = State()
    brand = State()
    model = State()
    repair_price = State()
    prepayment = State()
    parts_cost = State()
    client_name = State()
    client_phone = State()
    master_name = State()

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Введите статус (например: В работе, Готово, Ожидает запчасть):")
    await OrderForm.status.set()

@dp.message_handler(state=OrderForm.status)
async def step_status(message: types.Message, state: FSMContext):
    await state.update_data(status=message.text)
    await message.answer("Введите вид ремонта:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.repair_type)
async def step_repair_type(message: types.Message, state: FSMContext):
    await state.update_data(repair_type=message.text)
    await message.answer("Введите производителя устройства:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.brand)
async def step_brand(message: types.Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await message.answer("Введите модель устройства:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.model)
async def step_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Введите цену ремонта:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.repair_price)
async def step_price(message: types.Message, state: FSMContext):
    await state.update_data(repair_price=float(message.text))
    await message.answer("Введите задаток:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.prepayment)
async def step_prepayment(message: types.Message, state: FSMContext):
    await state.update_data(prepayment=float(message.text))
    await message.answer("Введите стоимость запчастей:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.parts_cost)
async def step_parts_cost(message: types.Message, state: FSMContext):
    await state.update_data(parts_cost=float(message.text))
    await message.answer("Введите имя клиента:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.client_name)
async def step_client_name(message: types.Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    await message.answer("Введите номер телефона клиента:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.client_phone)
async def step_client_phone(message: types.Message, state: FSMContext):
    await state.update_data(client_phone=message.text)
    await message.answer("Введите имя мастера:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.master_name)
async def step_master_name(message: types.Message, state: FSMContext):
    await state.update_data(master_name=message.text)
    data = await state.get_data()

    balance_due = data['repair_price'] - data['prepayment']

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO repairs (status, repair_type, brand, model, repair_price, prepayment, balance_due, parts_cost, client_name, client_phone, master_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['status'], data['repair_type'], data['brand'], data['model'],
        data['repair_price'], data['prepayment'], balance_due, data['parts_cost'],
        data['client_name'], data['client_phone'], data['master_name']
    ))
    conn.commit()
    conn.close()

    await message.answer("Заказ сохранён.")
    await state.finish()

# ---------- Команда для просмотра заказов ----------
@dp.message_handler(commands=['all_orders'])
async def all_orders(message: types.Message):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, client_name, model, status FROM repairs ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("Заказов пока нет.")
        return

    text = "📋 Заказы:\n"
    for row in rows:
        text += f"ID: {row[0]}, Клиент: {row[1]}, Модель: {row[2]}, Статус: {row[3]}\n"

    await message.answer(text)

# ---------- FSM для изменения статуса ----------
class StatusUpdate(StatesGroup):
    order_id = State()
    new_status = State()

@dp.message_handler(commands=['update_status'])
async def update_status_start(message: types.Message):
    await message.answer("Введите ID заказа, у которого хотите изменить статус:")
    await StatusUpdate.order_id.set()

@dp.message_handler(state=StatusUpdate.order_id)
async def get_order_id(message: types.Message, state: FSMContext):
    await state.update_data(order_id=int(message.text))
    await message.answer("Введите новый статус:")
    await StatusUpdate.next()

@dp.message_handler(state=StatusUpdate.new_status)
async def get_new_status(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data['order_id']
    new_status = message.text

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

    await message.answer(f"Статус заказа {order_id} обновлён на: {new_status}")
    await state.finish()

# ---------- Запуск ----------
if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
