import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Получаем токен из переменных окружения
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("BOT_TOKEN не найден. Установите переменную окружения.")

# Инициализация бота
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Путь к БД
db_path = "repairs.db"

# Создание таблицы при первом запуске
def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT,
            repair_type TEXT,
            brand TEXT,
            model TEXT,
            repair_price REAL,
            prepayment REAL,
            balance_due REAL,
            parts_cost REAL,
            client_name TEXT,
            client_phone TEXT,
            master_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- Состояния FSM ----------
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

class StatusUpdate(StatesGroup):
    order_id = State()
    new_status = State()

# ---------- Команды ----------

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("🔧 Создание нового заказа. Введите статус ремонта:")
    await OrderForm.status.set()

@dp.message_handler(state=OrderForm.status)
async def process_status(message: types.Message, state: FSMContext):
    await state.update_data(status=message.text)
    await message.answer("Введите вид ремонта:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.repair_type)
async def process_type(message: types.Message, state: FSMContext):
    await state.update_data(repair_type=message.text)
    await message.answer("Введите производителя устройства:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.brand)
async def process_brand(message: types.Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await message.answer("Введите модель устройства:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.model)
async def process_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Введите цену ремонта (пример: 4500):")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.repair_price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        await state.update_data(repair_price=float(message.text))
        await message.answer("Введите задаток (пример: 1000):")
        await OrderForm.next()
    except:
        await message.answer("Ошибка: введите число, например 4500.")

@dp.message_handler(state=OrderForm.prepayment)
async def process_prepayment(message: types.Message, state: FSMContext):
    try:
        await state.update_data(prepayment=float(message.text))
        await message.answer("Введите стоимость запчастей:")
        await OrderForm.next()
    except:
        await message.answer("Ошибка: введите число.")

@dp.message_handler(state=OrderForm.parts_cost)
async def process_parts(message: types.Message, state: FSMContext):
    try:
        await state.update_data(parts_cost=float(message.text))
        await message.answer("Введите имя клиента:")
        await OrderForm.next()
    except:
        await message.answer("Ошибка: введите число.")

@dp.message_handler(state=OrderForm.client_name)
async def process_client(message: types.Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    await message.answer("Введите номер телефона клиента:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.client_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(client_phone=message.text)
    await message.answer("Введите имя мастера:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.master_name)
async def process_master(message: types.Message, state: FSMContext):
    await state.update_data(master_name=message.text)
    data = await state.get_data()
    balance_due = data['repair_price'] - data['prepayment']

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO repairs (status, repair_type, brand, model, repair_price, prepayment, balance_due,
                             parts_cost, client_name, client_phone, master_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['status'], data['repair_type'], data['brand'], data['model'],
        data['repair_price'], data['prepayment'], balance_due,
        data['parts_cost'], data['client_name'], data['client_phone'], data['master_name']
    ))
    conn.commit()
    conn.close()

    await message.answer("✅ Заказ сохранён.")
    await state.finish()

@dp.message_handler(commands=['all_orders'])
async def all_orders(message: types.Message):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, client_name, model, status FROM repairs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("📭 Заказов пока нет.")
        return

    response = "📋 Список заказов:\n"
    for r in rows:
        response += f"ID: {r[0]} | Клиент: {r[1]} | Модель: {r[2]} | Статус: {r[3]}\n"
    await message.answer(response)

@dp.message_handler(commands=['update_status'])
async def cmd_update(message: types.Message):
    await message.answer("Введите ID заказа, который хотите обновить:")
    await StatusUpdate.order_id.set()

@dp.message_handler(state=StatusUpdate.order_id)
async def process_order_id(message: types.Message, state: FSMContext):
    try:
        await state.update_data(order_id=int(message.text))
        await message.answer("Введите новый статус:")
        await StatusUpdate.next()
    except:
        await message.answer("Ошибка: введите корректный ID (число).")

@dp.message_handler(state=StatusUpdate.new_status)
async def process_new_status(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data['order_id']
    new_status = message.text

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

    await message.answer(f"🔄 Статус заказа ID {order_id} обновлён на: {new_status}")
    await state.finish()

# ---------- Запуск ----------
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
