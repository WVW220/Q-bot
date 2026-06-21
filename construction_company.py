"""
🏗️ СТРОИТЕЛЬНАЯ КОМПАНИЯ
Команда: стройка
"""
import time
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils import get_user, get_balance, update_balance, save_user_data, format_amount

router = Router()

# ══════════════════════════════════════════════════════════════
#  КОНФИГ
# ══════════════════════════════════════════════════════════════

REGISTRATION_COST  = 150_000
STARTING_BALANCE   = 75_000
BANKRUPTCY_LIMIT   = -1_500_000
BANKRUPTCY_TIMEOUT = 3600          # 1 час

COMMISSION_PREMIUM = 0.03
COMMISSION_VIP     = 0.05
COMMISSION_NORMAL  = 0.10
COMMISSION_MIN     = 10            # комиссия только от суммы > 10$

# ─── Офисы ────────────────────────────────────────────────────
OFFICES = {
    1: {"name": "🏠 Стартовый",  "max_emp": 5,  "max_mach": 3,  "max_contracts": 1, "warehouse": 200,  "price": 0},
    2: {"name": "🏢 Малый",      "max_emp": 10, "max_mach": 6,  "max_contracts": 2, "warehouse": 500,  "price": 200_000},
    3: {"name": "🏗 Средний",    "max_emp": 20, "max_mach": 12, "max_contracts": 3, "warehouse": 1000, "price": 600_000},
    4: {"name": "🏬 Крупный",    "max_emp": 35, "max_mach": 20, "max_contracts": 4, "warehouse": 2000, "price": 1_600_000},
    5: {"name": "🏛 Элитный",    "max_emp": 50, "max_mach": 30, "max_contracts": 5, "warehouse": 5000, "price": 4_000_000},
}
MAX_OFFICE = 5

# ─── Здания ───────────────────────────────────────────────────
BUILDINGS = {
    "house":    {"name": "🏠 Частный дом",     "cost": 50_000,    "reward": 80_000,    "rep": 1,  "time": 1800,   "req_research": 0, "resources": {"brick": 20, "wood": 15}},
    "office":   {"name": "🏢 Офисное здание",  "cost": 200_000,   "reward": 350_000,   "rep": 2,  "time": 7200,   "req_research": 0, "resources": {"brick": 80, "metal": 50, "blueprints": 2}},
    "mall":     {"name": "🏬 Торговый центр",  "cost": 500_000,   "reward": 900_000,   "rep": 4,  "time": 21600,  "req_research": 1, "resources": {"brick": 150, "metal": 120, "blueprints": 5}},
    "school":   {"name": "🏫 Школа",           "cost": 800_000,   "reward": 1_500_000, "rep": 6,  "time": 43200,  "req_research": 2, "resources": {"brick": 200, "wood": 100, "metal": 80, "blueprints": 8}},
    "hospital": {"name": "🏥 Больница",        "cost": 1_500_000, "reward": 3_000_000, "rep": 10, "time": 86400,  "req_research": 3, "resources": {"brick": 300, "metal": 200, "blueprints": 15}},
    "bridge":   {"name": "🌉 Мост",            "cost": 3_000_000, "reward": 6_500_000, "rep": 18, "time": 172800, "req_research": 4, "resources": {"metal": 500, "tech": 20, "blueprints": 25}},
    "stadium":  {"name": "🏟 Стадион",         "cost": 8_000_000, "reward": 18_000_000,"rep": 35, "time": 345600, "req_research": 5, "resources": {"brick": 1000, "metal": 800, "tech": 50, "blueprints": 50}},
}

# ─── Сотрудники ───────────────────────────────────────────────
EMPLOYEES = {
    "worker":    {"name": "👷 Рабочий",    "cost": 5_000,   "speed": 2,  "reward": 0,  "desc": "Выполняет строительные работы"},
    "foreman":   {"name": "🔨 Бригадир",   "cost": 20_000,  "speed": 5,  "reward": 0,  "desc": "Ускоряет строительство"},
    "architect": {"name": "📐 Архитектор", "cost": 50_000,  "speed": 0,  "reward": 3,  "desc": "Открывает сложные проекты"},
    "engineer":  {"name": "🚜 Инженер",    "cost": 80_000,  "speed": 8,  "reward": 2,  "desc": "Повышает эффективность техники"},
    "manager":   {"name": "📊 Прораб",     "cost": 150_000, "speed": 10, "reward": 5,  "desc": "Улучшает производительность"},
}

# ─── Техника ──────────────────────────────────────────────────
MACHINES = {
    "bulldozer": {"name": "🚜 Бульдозер", "cost": 30_000,  "speed": 5},
    "crane":     {"name": "🏗 Кран",      "cost": 60_000,  "speed": 8},
    "truck":     {"name": "🚚 Грузовик",  "cost": 25_000,  "speed": 3},
    "dumptruck": {"name": "🚛 Самосвал",  "cost": 45_000,  "speed": 4},
}

# ─── Ресурсы ──────────────────────────────────────────────────
RESOURCES = {
    "brick":      {"name": "🧱 Кирпич",    "price": 500,    "unit": "шт"},
    "wood":       {"name": "🪵 Древесина",  "price": 300,    "unit": "шт"},
    "metal":      {"name": "🔩 Металл",     "price": 800,    "unit": "шт"},
    "tech":       {"name": "🚚 Техника",    "price": 20_000, "unit": "ед"},
    "blueprints": {"name": "📐 Проекты",   "price": 50_000, "unit": "шт"},
}
RES_BUY_PACK = 10   # покупается партиями по 10

# ─── Исследования ─────────────────────────────────────────────
RESEARCH = {
    0: {"name": "Нет",                      "cost": 0,          "speed": 0,  "reward": 0},
    1: {"name": "Базовые технологии",       "cost": 100_000,    "speed": 5,  "reward": 0},
    2: {"name": "Продвинутые материалы",    "cost": 500_000,    "speed": 10, "reward": 5},
    3: {"name": "Современные методы",       "cost": 1_500_000,  "speed": 15, "reward": 10},
    4: {"name": "Автоматизация",            "cost": 5_000_000,  "speed": 25, "reward": 15},
    5: {"name": "Элитные технологии",       "cost": 15_000_000, "speed": 40, "reward": 25},
}
MAX_RESEARCH = 5

# ─── Контракты ────────────────────────────────────────────────
CONTRACT_TYPES = {
    "private":    {"name": "🏗 Частный заказ",          "min": 50_000,    "max": 200_000,   "dur": 14400,  "rep_req": 0,  "rep": 1},
    "corporate":  {"name": "🏢 Корпоративный проект",   "min": 500_000,   "max": 1_000_000, "dur": 43200,  "rep_req": 10, "rep": 3},
    "government": {"name": "🏛 Государственный контракт","min": 2_000_000, "max": 5_000_000, "dur": 86400,  "rep_req": 30, "rep": 8},
}

# ─── Достижения ───────────────────────────────────────────────
ACHIEVEMENTS = [
    {"id": "first_build",    "name": "🏠 Первая стройка",      "desc": "Завершить первый объект",           "check": lambda c: len(c.get("completed", [])) >= 1},
    {"id": "builder_5",      "name": "🏗 Строитель",           "desc": "Завершить 5 объектов",              "check": lambda c: len(c.get("completed", [])) >= 5},
    {"id": "builder_20",     "name": "🏙 Застройщик",          "desc": "Завершить 20 объектов",             "check": lambda c: len(c.get("completed", [])) >= 20},
    {"id": "first_contract", "name": "📋 Первый контракт",     "desc": "Выполнить первый контракт",         "check": lambda c: c.get("contracts_done", 0) >= 1},
    {"id": "contracts_10",   "name": "📑 Подрядчик",           "desc": "Выполнить 10 контрактов",           "check": lambda c: c.get("contracts_done", 0) >= 10},
    {"id": "contracts_50",   "name": "🏆 Мастер контрактов",   "desc": "Выполнить 50 контрактов",           "check": lambda c: c.get("contracts_done", 0) >= 50},
    {"id": "staff_10",       "name": "👥 Команда",             "desc": "Нанять 10 сотрудников",             "check": lambda c: _total_emp(c) >= 10},
    {"id": "staff_30",       "name": "🏢 Большой штат",        "desc": "Нанять 30 сотрудников",             "check": lambda c: _total_emp(c) >= 30},
    {"id": "rep_20",         "name": "⭐ Известная компания",  "desc": "Достичь 20 репутации",              "check": lambda c: c.get("reputation", 0) >= 20},
    {"id": "rep_80",         "name": "🌟 Легенда рынка",       "desc": "Достичь 80 репутации",              "check": lambda c: c.get("reputation", 0) >= 80},
    {"id": "big_building",   "name": "🏟 Стадион",             "desc": "Построить стадион",                 "check": lambda c: any(b["type"] == "stadium" for b in c.get("completed", []))},
    {"id": "elite_office",   "name": "🏛 Элита",               "desc": "Получить элитный офис",             "check": lambda c: c.get("office_level", 1) >= 5},
]


# ══════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════

def _total_emp(company: dict) -> int:
    return sum(company.get("employees", {}).values())


def _total_mach(company: dict) -> int:
    return sum(company.get("machines", {}).values())


def get_company(user_id) -> dict | None:
    return get_user(user_id).get("construction_company")


def create_company(user_id) -> dict:
    user = get_user(user_id)
    company = {
        "name":           "Моя компания",
        "balance":        STARTING_BALANCE,
        "reputation":     0,
        "office_level":   1,
        "employees":      {k: 0 for k in EMPLOYEES},
        "machines":       {k: 0 for k in MACHINES},
        "resources":      {k: 0 for k in RESOURCES},
        "research_level": 0,
        "completed":      [],
        "active":         None,
        "contracts":      [],
        "contracts_done": 0,
        "achievements":   [],
        "created_at":     int(time.time()),
        "debt_since":     None,
        "warned_5min":    False,
    }
    user["construction_company"] = company
    save_user_data()
    return company


def fmt(n: float) -> str:
    return f"{int(n):,}".replace(",", ".")


def fmt_time(seconds: int) -> str:
    if seconds <= 0:
        return "✅ Готово"
    h, r = divmod(int(seconds), 3600)
    m, s = divmod(r, 60)
    if h > 0:
        return f"{h}ч {m}м"
    if m > 0:
        return f"{m}м {s}с"
    return f"{s}с"


def speed_bonus(company: dict) -> float:
    b = 0.0
    for k, cnt in company.get("employees", {}).items():
        b += EMPLOYEES[k]["speed"] * cnt
    for k, cnt in company.get("machines", {}).items():
        b += MACHINES[k]["speed"] * cnt
    b += RESEARCH[company.get("research_level", 0)]["speed"]
    return min(b, 90.0)


def reward_bonus(company: dict) -> float:
    b = 0.0
    for k, cnt in company.get("employees", {}).items():
        b += EMPLOYEES[k]["reward"] * cnt
    b += RESEARCH[company.get("research_level", 0)]["reward"]
    return min(b, 100.0)


def eff_time(base: int, company: dict) -> int:
    return max(60, int(base * (1 - speed_bonus(company) / 100)))


def eff_reward(base: int, company: dict) -> int:
    return int(base * (1 + reward_bonus(company) / 100))


def rep_title(rep: int) -> str:
    if rep < 5:   return "🔘 Новичок"
    if rep < 15:  return "🟡 Известный"
    if rep < 35:  return "🟠 Уважаемый"
    if rep < 70:  return "🔵 Авторитетный"
    if rep < 120: return "🟣 Именитый"
    return "⭐ Легенда"


def check_bankruptcy(company: dict) -> str | None:
    bal = company.get("balance", 0)
    if bal >= BANKRUPTCY_LIMIT:
        company["debt_since"] = None
        company["warned_5min"] = False
        return None
    now = int(time.time())
    if not company.get("debt_since"):
        company["debt_since"] = now
        return "warn"
    elapsed = now - company["debt_since"]
    if elapsed >= BANKRUPTCY_TIMEOUT:
        return "bankrupt"
    if elapsed >= BANKRUPTCY_TIMEOUT - 300 and not company.get("warned_5min"):
        company["warned_5min"] = True
        return "warn5"
    return "debt"


def get_commission_rate(user_id) -> float:
    try:
        from donate import is_vip
        if is_vip(user_id):
            return COMMISSION_VIP
    except Exception:
        pass
    user = get_user(user_id)
    if user.get("donate_coins", 0) > 0 or user.get("premium"):
        return COMMISSION_PREMIUM
    return COMMISSION_NORMAL


def check_achievements(company: dict) -> list[str]:
    """Проверяет новые достижения, возвращает список новых."""
    earned = company.get("achievements", [])
    new_ones = []
    for ach in ACHIEVEMENTS:
        if ach["id"] not in earned:
            try:
                if ach["check"](company):
                    earned.append(ach["id"])
                    new_ones.append(ach["name"])
            except Exception:
                pass
    company["achievements"] = earned
    return new_ones


def warehouse_used(company: dict) -> int:
    return sum(company.get("resources", {}).values())


def warehouse_max(company: dict) -> int:
    return OFFICES[company.get("office_level", 1)]["warehouse"]


# ══════════════════════════════════════════════════════════════
#  КЛАВИАТУРЫ
# ══════════════════════════════════════════════════════════════

def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏗 Объекты",      callback_data="sk_buildings"),
            InlineKeyboardButton(text="👷 Сотрудники",   callback_data="sk_employees"),
        ],
        [
            InlineKeyboardButton(text="📦 Склад",        callback_data="sk_warehouse"),
            InlineKeyboardButton(text="🚜 Техника",      callback_data="sk_machines"),
        ],
        [
            InlineKeyboardButton(text="🔬 Исследования", callback_data="sk_research"),
            InlineKeyboardButton(text="📋 Контракты",    callback_data="sk_contracts"),
        ],
        [
            InlineKeyboardButton(text="🏢 Офис",         callback_data="sk_office"),
            InlineKeyboardButton(text="💰 Баланс",       callback_data="sk_balance"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки",   callback_data="sk_settings"),
            InlineKeyboardButton(text="🔄 Обновить",     callback_data="sk_main"),
        ],
    ])


def back_kb(target: str = "sk_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=target)],
    ])


# ══════════════════════════════════════════════════════════════
#  ТЕКСТЫ ГЛАВНОГО МЕНЮ
# ══════════════════════════════════════════════════════════════

def main_text(company: dict) -> str:
    bal    = company.get("balance", 0)
    rep    = company.get("reputation", 0)
    office = OFFICES[company.get("office_level", 1)]
    active = company.get("active")
    bk     = check_bankruptcy(company)

    bk_line = ""
    if bk == "bankrupt":
        bk_line = "\n\n⛔ <b>КОМПАНИЯ БАНКРОТ!</b>"
    elif bk == "warn5":
        bk_line = "\n\n🔴 <b>До банкротства &lt;5 минут!</b>"
    elif bk in ("warn", "debt"):
        bk_line = "\n\n🔔 <b>Критический долг!</b> Банкротство через 1 час."

    constr = ""
    if active:
        left = active["finish_at"] - int(time.time())
        constr = f"\n🔨 <b>Строим:</b> {BUILDINGS[active['type']]['name']} — {fmt_time(left)}"

    total_done = len(company.get("completed", []))
    achiev     = len(company.get("achievements", []))

    company_name = company.get("name", "Моя компания")
    return (
        f"🏗️ <b>{company_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Баланс: <b>{fmt(bal)}$</b>\n"
        f"⭐ Репутация: <b>{rep}</b> — {rep_title(rep)}\n"
        f"🏢 Офис: <b>{office['name']}</b>\n"
        f"👷 Сотрудников: <b>{_total_emp(company)}/{office['max_emp']}</b>\n"
        f"🚜 Техники: <b>{_total_mach(company)}/{office['max_mach']}</b>\n"
        f"📦 Склад: <b>{warehouse_used(company)}/{warehouse_max(company)}</b>\n"
        f"🏗 Построено объектов: <b>{total_done}</b>\n"
        f"🏅 Достижений: <b>{achiev}/{len(ACHIEVEMENTS)}</b>"
        f"{constr}{bk_line}"
    )


# ══════════════════════════════════════════════════════════════
#  ГЛАВНЫЕ ХЭНДЛЕРЫ
# ══════════════════════════════════════════════════════════════

@router.message(F.text.lower().regexp(r"^ск создать\s+(.+)$"))
async def cmd_sk_create_named(message: Message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    if get_company(user_id):
        await message.answer(
            "❌ У вас уже есть строительная компания. Введите <b>стройка</b> для управления.",
            parse_mode="HTML"
        )
        return
    bal = get_balance(user_id)
    if bal < REGISTRATION_COST:
        await message.answer(
            f"❌ Недостаточно средств!\n"
            f"Нужно: <b>{fmt(REGISTRATION_COST)}$</b>\n"
            f"У вас: <b>{fmt(bal)}$</b>",
            parse_mode="HTML"
        )
        return
    parts = message.text.strip().split(None, 2)
    name = parts[2].strip() if len(parts) >= 3 else "Моя компания"
    if len(name) > 32:
        await message.answer("❌ Название слишком длинное (максимум 32 символа).")
        return
    update_balance(user_id, bal - REGISTRATION_COST)
    company = create_company(user_id)
    company["name"] = name
    save_user_data()
    await message.answer(
        f"✅ <b>Строительная компания создана!</b>\n\n"
        f"🏗 Название: <b>{name}</b>\n"
        f"💸 Списано: {fmt(REGISTRATION_COST)}$\n"
        f"🏦 Баланс компании: {fmt(STARTING_BALANCE)}$\n"
        f"🏢 Офис: {OFFICES[1]['name']}\n\n"
        f"Стройте, нанимайте, побеждайте!",
        parse_mode="HTML",
        reply_markup=main_kb()
    )


@router.message(F.text.lower().in_(["стройка", "строительная компания", "/стройка", "ск", "/ск", "🏗 стройка"]))
async def cmd_sk(message: Message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    company = get_company(user_id)
    if not company:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🏗 Создать компанию — {fmt(REGISTRATION_COST)}$",
                callback_data="sk_create"
            )],
        ])
        await message.answer(
            f"🏗️ <b>Строительная Компания</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Создайте собственную строительную империю, нанимайте рабочих, "
            f"возводите здания, выполняйте государственные контракты и станьте "
            f"крупнейшим застройщиком!\n\n"
            f"<b>Стоимость регистрации:</b> {fmt(REGISTRATION_COST)}$\n"
            f"<b>Стартовый баланс компании:</b> {fmt(STARTING_BALANCE)}$\n\n"
            f"<b>Как начать:</b>\n"
            f"1. Создай строительную компанию\n"
            f"2. Построй первый объект\n"
            f"3. Найми сотрудников\n"
            f"4. Закупи технику и ресурсы\n"
            f"5. Выполняй контракты и расширяй компанию",
            parse_mode="HTML",
            reply_markup=kb
        )
        return
    bk = check_bankruptcy(company)
    if bk == "bankrupt":
        await _do_bankruptcy(message, user_id, company)
        return
    save_user_data()
    await message.answer(main_text(company), parse_mode="HTML", reply_markup=main_kb())


@router.callback_query(F.data == "sk_main")
async def cb_sk_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Компании нет.", show_alert=True)
        return
    bk = check_bankruptcy(company)
    if bk == "bankrupt":
        await _do_bankruptcy(callback.message, user_id, company)
        await callback.answer()
        return
    new_ach = check_achievements(company)
    save_user_data()
    try:
        await callback.message.edit_text(main_text(company), parse_mode="HTML", reply_markup=main_kb())
    except Exception:
        pass
    if new_ach:
        await callback.message.answer(
            "🏅 <b>Новые достижения!</b>\n\n" + "\n".join(f"• {a}" for a in new_ach),
            parse_mode="HTML"
        )
    await callback.answer()


async def _do_bankruptcy(message, user_id, company):
    user = get_user(user_id)
    user.pop("construction_company", None)
    save_user_data()
    await message.answer(
        "⛔ <b>Банкротство!</b>\n\n"
        "Ваша строительная компания обанкротилась из-за критического долга.\n"
        "Все активы ликвидированы. Вы можете создать новую компанию.",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════
#  СОЗДАНИЕ
# ══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "sk_create")
async def cb_sk_create(callback: CallbackQuery):
    user_id = callback.from_user.id
    if get_company(user_id):
        await callback.answer("У вас уже есть компания!", show_alert=True)
        return
    bal = get_balance(user_id)
    if bal < REGISTRATION_COST:
        await callback.answer(
            f"❌ Нужно {fmt(REGISTRATION_COST)}$, у вас {fmt(bal)}$",
            show_alert=True
        )
        return
    update_balance(user_id, bal - REGISTRATION_COST)
    company = create_company(user_id)
    await callback.message.edit_text(
        f"✅ <b>Строительная компания создана!</b>\n\n"
        f"💸 Списано: {fmt(REGISTRATION_COST)}$\n"
        f"🏦 Баланс компании: {fmt(STARTING_BALANCE)}$\n"
        f"🏢 Офис: {OFFICES[1]['name']}\n\n"
        f"Стройте, нанимайте, побеждайте!",
        parse_mode="HTML",
        reply_markup=main_kb()
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════
#  ФИНАНСЫ
# ══════════════════════════════════════════════════════════════

class SKFinance(StatesGroup):
    deposit  = State()
    withdraw = State()

class SKSettings(StatesGroup):
    rename = State()


@router.callback_query(F.data == "sk_balance")
async def cb_sk_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    rate = get_commission_rate(user_id)
    comm_str = f"{int(rate * 100)}%"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Пополнить",  callback_data="sk_dep_prompt")],
        [InlineKeyboardButton(text="💸 Снять",      callback_data="sk_wit_prompt")],
        [InlineKeyboardButton(text="💸 Снять всё",  callback_data="sk_wit_all")],
        [InlineKeyboardButton(text="◀️ Назад",      callback_data="sk_main")],
    ])
    await callback.message.edit_text(
        f"💰 <b>Финансы компании</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 Баланс компании: <b>{fmt(company['balance'])}$</b>\n"
        f"👤 Ваш баланс: <b>{fmt(get_balance(user_id))}$</b>\n\n"
        f"📊 Ваша комиссия: <b>{comm_str}</b> (от суммы &gt; {COMMISSION_MIN}$)",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "sk_dep_prompt")
async def cb_sk_dep_prompt(callback: CallbackQuery, state: FSMContext):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await state.set_state(SKFinance.deposit)
    await callback.message.edit_text(
        f"💵 <b>Пополнение баланса компании</b>\n\n"
        f"Ваш баланс: <b>{fmt(get_balance(callback.from_user.id))}$</b>\n\n"
        f"Введите сумму:",
        parse_mode="HTML",
        reply_markup=back_kb("sk_balance")
    )
    await callback.answer()


@router.message(SKFinance.deposit)
async def msg_sk_deposit(message: Message, state: FSMContext):
    user_id = message.from_user.id
    company = get_company(user_id)
    if not company:
        await state.clear()
        return
    try:
        from utils import parse_k
        amount = int(parse_k(message.text.strip()))
    except Exception:
        await message.answer("❌ Введите корректную сумму.")
        return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть положительной.")
        return
    rate = get_commission_rate(user_id)
    commission = int(amount * rate) if amount > COMMISSION_MIN else 0
    total_needed = amount + commission
    bal = get_balance(user_id)
    if bal < total_needed:
        await message.answer(
            f"❌ Недостаточно средств!\n"
            f"Сумма: {fmt(amount)}$\n"
            f"Комиссия: {fmt(commission)}$\n"
            f"Итого нужно: {fmt(total_needed)}$\n"
            f"У вас: {fmt(bal)}$"
        )
        return
    update_balance(user_id, bal - total_needed)
    company["balance"] = company.get("balance", 0) + amount
    save_user_data()
    await state.clear()
    await message.answer(
        f"✅ <b>Пополнено!</b>\n\n"
        f"Зачислено: <b>{fmt(amount)}$</b>\n"
        f"Комиссия: <b>{fmt(commission)}$</b>\n"
        f"Баланс компании: <b>{fmt(company['balance'])}$</b>",
        parse_mode="HTML",
        reply_markup=main_kb()
    )


@router.callback_query(F.data == "sk_wit_prompt")
async def cb_sk_wit_prompt(callback: CallbackQuery, state: FSMContext):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    rate = get_commission_rate(callback.from_user.id)
    await state.set_state(SKFinance.withdraw)
    await callback.message.edit_text(
        f"💸 <b>Снятие с баланса компании</b>\n\n"
        f"Баланс компании: <b>{fmt(company['balance'])}$</b>\n"
        f"Комиссия: <b>{int(rate * 100)}%</b>\n\n"
        f"Введите сумму:",
        parse_mode="HTML",
        reply_markup=back_kb("sk_balance")
    )
    await callback.answer()


@router.message(SKFinance.withdraw)
async def msg_sk_withdraw(message: Message, state: FSMContext):
    user_id = message.from_user.id
    company = get_company(user_id)
    if not company:
        await state.clear()
        return
    try:
        from utils import parse_k
        amount = int(parse_k(message.text.strip()))
    except Exception:
        await message.answer("❌ Введите корректную сумму.")
        return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть положительной.")
        return
    comp_bal = company.get("balance", 0)
    if amount > comp_bal:
        await message.answer(f"❌ На счёте компании только {fmt(comp_bal)}$")
        return
    rate = get_commission_rate(user_id)
    commission = int(amount * rate) if amount > COMMISSION_MIN else 0
    net = amount - commission
    company["balance"] = comp_bal - amount
    update_balance(user_id, get_balance(user_id) + net)
    save_user_data()
    await state.clear()
    await message.answer(
        f"✅ <b>Снято!</b>\n\n"
        f"Запрошено: <b>{fmt(amount)}$</b>\n"
        f"Комиссия: <b>{fmt(commission)}$</b>\n"
        f"Получено: <b>{fmt(net)}$</b>\n"
        f"Баланс компании: <b>{fmt(company['balance'])}$</b>",
        parse_mode="HTML",
        reply_markup=main_kb()
    )


@router.callback_query(F.data == "sk_wit_all")
async def cb_sk_wit_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    comp_bal = company.get("balance", 0)
    if comp_bal <= 0:
        await callback.answer("На счёте нет средств.", show_alert=True)
        return
    rate = get_commission_rate(user_id)
    commission = int(comp_bal * rate) if comp_bal > COMMISSION_MIN else 0
    net = comp_bal - commission
    company["balance"] = 0
    update_balance(user_id, get_balance(user_id) + net)
    save_user_data()
    await callback.message.edit_text(
        f"✅ <b>Снято всё!</b>\n\n"
        f"Было: <b>{fmt(comp_bal)}$</b>\n"
        f"Комиссия: <b>{fmt(commission)}$</b>\n"
        f"Получено: <b>{fmt(net)}$</b>",
        parse_mode="HTML",
        reply_markup=back_kb("sk_balance")
    )
    await callback.answer()


# Текстовые команды финансов
@router.message(F.text.lower().regexp(r"^стройка пополнить\s+(.+)$"))
async def cmd_sk_dep_text(message: Message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    company = get_company(user_id)
    if not company:
        await message.answer("❌ У вас нет строительной компании. Введите <b>стройка</b>.", parse_mode="HTML")
        return
    parts = message.text.strip().split(None, 2)
    if len(parts) < 3:
        return
    try:
        from utils import parse_k
        amount = int(parse_k(parts[2]))
    except Exception:
        await message.answer("❌ Некорректная сумма.")
        return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть положительной.")
        return
    rate = get_commission_rate(user_id)
    commission = int(amount * rate) if amount > COMMISSION_MIN else 0
    total_needed = amount + commission
    bal = get_balance(user_id)
    if bal < total_needed:
        await message.answer(f"❌ Нужно {fmt(total_needed)}$ (вкл. комиссию {fmt(commission)}$), у вас {fmt(bal)}$")
        return
    update_balance(user_id, bal - total_needed)
    company["balance"] = company.get("balance", 0) + amount
    save_user_data()
    await message.answer(
        f"✅ Пополнено <b>{fmt(amount)}$</b> (комиссия {fmt(commission)}$). "
        f"Баланс компании: <b>{fmt(company['balance'])}$</b>",
        parse_mode="HTML"
    )


@router.message(F.text.lower().in_(["стройка снять все", "стройка снять всё"]))
async def cmd_sk_wit_all_text(message: Message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    company = get_company(user_id)
    if not company:
        await message.answer("❌ У вас нет строительной компании.")
        return
    comp_bal = company.get("balance", 0)
    if comp_bal <= 0:
        await message.answer("❌ На счёте нет средств.")
        return
    rate = get_commission_rate(user_id)
    commission = int(comp_bal * rate) if comp_bal > COMMISSION_MIN else 0
    net = comp_bal - commission
    company["balance"] = 0
    update_balance(user_id, get_balance(user_id) + net)
    save_user_data()
    await message.answer(
        f"✅ Снято <b>{fmt(comp_bal)}$</b>, комиссия <b>{fmt(commission)}$</b>, получено <b>{fmt(net)}$</b>",
        parse_mode="HTML"
    )


@router.message(F.text.lower().regexp(r"^стройка снять\s+(.+)$"))
async def cmd_sk_wit_text(message: Message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    company = get_company(user_id)
    if not company:
        await message.answer("❌ У вас нет строительной компании.")
        return
    parts = message.text.strip().split(None, 2)
    if len(parts) < 3:
        return
    arg = parts[2].lower()
    if arg in ("все", "всё", "all"):
        await cmd_sk_wit_all_text(message)
        return
    try:
        from utils import parse_k
        amount = int(parse_k(arg))
    except Exception:
        await message.answer("❌ Некорректная сумма.")
        return
    comp_bal = company.get("balance", 0)
    if amount > comp_bal:
        await message.answer(f"❌ На счёте только {fmt(comp_bal)}$")
        return
    rate = get_commission_rate(user_id)
    commission = int(amount * rate) if amount > COMMISSION_MIN else 0
    net = amount - commission
    company["balance"] = comp_bal - amount
    update_balance(user_id, get_balance(user_id) + net)
    save_user_data()
    await message.answer(
        f"✅ Снято <b>{fmt(amount)}$</b>, комиссия <b>{fmt(commission)}$</b>, получено <b>{fmt(net)}$</b>",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════
#  ОБЪЕКТЫ
# ══════════════════════════════════════════════════════════════

def buildings_list_kb(company: dict) -> InlineKeyboardMarkup:
    research = company.get("research_level", 0)
    active   = company.get("active")
    rows = []
    for key, b in BUILDINGS.items():
        unlocked = research >= b["req_research"]
        if not unlocked:
            icon = "🔒"
        elif active and active["type"] == key:
            icon = "🏗"
        else:
            icon = "▶️"
        rows.append([InlineKeyboardButton(
            text=f"{icon} {b['name']} — {fmt(b['cost'])}$",
            callback_data=f"sk_build_info:{key}" if unlocked else "sk_build_locked"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sk_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "sk_buildings")
async def cb_sk_buildings(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    active = company.get("active")
    line = ""
    if active:
        left = active["finish_at"] - int(time.time())
        line = f"\n🔨 <b>Сейчас строится:</b> {BUILDINGS[active['type']]['name']} — {fmt_time(left)}"
    await callback.message.edit_text(
        f"🏗 <b>Строительные объекты</b>\n"
        f"━━━━━━━━━━━━━━━━━━{line}\n\n"
        f"Выберите объект:",
        parse_mode="HTML",
        reply_markup=buildings_list_kb(company)
    )
    await callback.answer()


@router.callback_query(F.data == "sk_build_locked")
async def cb_sk_build_locked(callback: CallbackQuery):
    await callback.answer("🔒 Нужно улучшить Проектное бюро!", show_alert=True)


@router.callback_query(F.data.startswith("sk_build_info:"))
async def cb_sk_build_info(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    key = callback.data.split(":")[1]
    b   = BUILDINGS.get(key)
    if not b:
        await callback.answer("Неверный объект.", show_alert=True)
        return

    active      = company.get("active")
    build_time  = eff_time(b["time"], company)
    build_reward= eff_reward(b["reward"], company)
    sp          = speed_bonus(company)
    rb          = reward_bonus(company)

    res_lines = []
    can_build  = True
    for rk, rv in b["resources"].items():
        have = company["resources"].get(rk, 0)
        ok   = have >= rv
        if not ok:
            can_build = False
        icon = "✅" if ok else "❌"
        res_lines.append(f"  {icon} {RESOURCES[rk]['name']}: {have}/{rv}")

    if company.get("balance", 0) < b["cost"]:
        can_build = False

    rows = []
    if active and active["type"] == key:
        left = active["finish_at"] - int(time.time())
        if left <= 0:
            rows.append([InlineKeyboardButton(text="✅ Получить награду", callback_data=f"sk_collect:{key}")])
        else:
            rows.append([InlineKeyboardButton(text=f"⏳ {fmt_time(left)}", callback_data="sk_noop")])
    elif active:
        rows.append([InlineKeyboardButton(text="⚠️ Уже идёт другая стройка", callback_data="sk_noop")])
    else:
        if can_build:
            rows.append([InlineKeyboardButton(text="🏗 Начать строительство", callback_data=f"sk_build_start:{key}")])
        else:
            rows.append([InlineKeyboardButton(text="❌ Недостаточно ресурсов/средств", callback_data="sk_noop")])

    rows.append([InlineKeyboardButton(text="◀️ К объектам", callback_data="sk_buildings")])

    await callback.message.edit_text(
        f"{b['name']}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Стоимость: <b>{fmt(b['cost'])}$</b> (счёт: {fmt(company['balance'])}$)\n"
        f"🏆 Награда: <b>{fmt(build_reward)}$</b> (+{rb:.0f}% бонус)\n"
        f"⭐ Репутация: <b>+{b['rep']}</b>\n"
        f"⏱ Время: <b>{fmt_time(build_time)}</b> (−{sp:.0f}% ускорение)\n\n"
        f"📦 <b>Требуемые ресурсы:</b>\n" + "\n".join(res_lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data == "sk_noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("sk_build_start:"))
async def cb_sk_build_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    key = callback.data.split(":")[1]
    b   = BUILDINGS.get(key)
    if not b:
        await callback.answer("Неверный объект.", show_alert=True)
        return
    if company.get("active"):
        await callback.answer("⚠️ Уже идёт строительство!", show_alert=True)
        return
    if company.get("balance", 0) < b["cost"]:
        await callback.answer(f"❌ Нужно {fmt(b['cost'])}$", show_alert=True)
        return
    for rk, rv in b["resources"].items():
        if company["resources"].get(rk, 0) < rv:
            await callback.answer(f"❌ Не хватает {RESOURCES[rk]['name']}!", show_alert=True)
            return

    company["balance"] -= b["cost"]
    for rk, rv in b["resources"].items():
        company["resources"][rk] -= rv

    build_time   = eff_time(b["time"], company)
    build_reward = eff_reward(b["reward"], company)
    company["active"] = {
        "type":       key,
        "started_at": int(time.time()),
        "finish_at":  int(time.time()) + build_time,
        "reward":     build_reward,
    }
    save_user_data()
    await callback.message.edit_text(
        f"🏗 <b>Строительство началось!</b>\n\n"
        f"{b['name']}\n"
        f"⏱ Время: <b>{fmt_time(build_time)}</b>\n"
        f"🏆 Ожидаемая награда: <b>{fmt(build_reward)}$</b>\n\n"
        f"Вернитесь, когда объект будет готов!",
        parse_mode="HTML",
        reply_markup=back_kb("sk_buildings")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sk_collect:"))
async def cb_sk_collect(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    active = company.get("active")
    if not active:
        await callback.answer("Нет активного строительства.", show_alert=True)
        return
    if int(time.time()) < active["finish_at"]:
        left = active["finish_at"] - int(time.time())
        await callback.answer(f"⏳ Ещё не готово! Осталось: {fmt_time(left)}", show_alert=True)
        return
    key    = active["type"]
    b      = BUILDINGS[key]
    reward = active.get("reward", b["reward"])
    company["balance"] = company.get("balance", 0) + reward
    company["reputation"] = company.get("reputation", 0) + b["rep"]
    if "completed" not in company:
        company["completed"] = []
    company["completed"].append({"type": key, "at": int(time.time())})
    company["active"] = None
    new_ach = check_achievements(company)
    save_user_data()
    text = (
        f"🎉 <b>{b['name']} построено!</b>\n\n"
        f"💰 Получено: <b>{fmt(reward)}$</b>\n"
        f"⭐ Репутация: <b>+{b['rep']}</b> (итого: {company['reputation']})\n"
        f"🏦 Баланс компании: <b>{fmt(company['balance'])}$</b>"
    )
    if new_ach:
        text += "\n\n🏅 <b>Новые достижения:</b>\n" + "\n".join(f"• {a}" for a in new_ach)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_kb())
    await callback.answer()


# ══════════════════════════════════════════════════════════════
#  СОТРУДНИКИ
# ══════════════════════════════════════════════════════════════

def emp_text(company: dict) -> str:
    office = OFFICES[company.get("office_level", 1)]
    total  = _total_emp(company)
    lines  = []
    for key, e in EMPLOYEES.items():
        cnt  = company["employees"].get(key, 0)
        sb   = f"⚡+{e['speed']}%" if e["speed"] else ""
        rb   = f"💰+{e['reward']}%" if e["reward"] else ""
        bon  = " ".join(filter(None, [sb, rb])) or "—"
        lines.append(f"  {e['name']}: <b>{cnt}</b> ({bon}) | {fmt(e['cost'])}$")
    return (
        f"👷 <b>Сотрудники</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Занято мест: <b>{total}/{office['max_emp']}</b>\n\n"
        + "\n".join(lines) +
        f"\n\n⚡ Суммарное ускорение: <b>+{speed_bonus(company):.0f}%</b>\n"
        f"💰 Бонус наград: <b>+{reward_bonus(company):.0f}%</b>\n"
        f"💰 Баланс компании: <b>{fmt(company['balance'])}$</b>"
    )


def emp_kb(company: dict) -> InlineKeyboardMarkup:
    office = OFFICES[company.get("office_level", 1)]
    total  = _total_emp(company)
    rows   = []
    for key, e in EMPLOYEES.items():
        cnt     = company["employees"].get(key, 0)
        can_hire = total < office["max_emp"] and company.get("balance", 0) >= e["cost"]
        rows.append([
            InlineKeyboardButton(text=f"➕ {e['name']}", callback_data=f"sk_hire:{key}" if can_hire else "sk_hire_no"),
            InlineKeyboardButton(text=f"➖ ({cnt})",      callback_data=f"sk_fire:{key}"),
        ])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sk_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "sk_employees")
async def cb_sk_emp(callback: CallbackQuery):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(emp_text(company), parse_mode="HTML", reply_markup=emp_kb(company))
    await callback.answer()


@router.callback_query(F.data.startswith("sk_hire:"))
async def cb_sk_hire(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    key = callback.data.split(":")[1]
    e   = EMPLOYEES.get(key)
    if not e:
        await callback.answer("Неверный тип.", show_alert=True)
        return
    office = OFFICES[company.get("office_level", 1)]
    if _total_emp(company) >= office["max_emp"]:
        await callback.answer("❌ Нет свободных мест! Улучшите офис.", show_alert=True)
        return
    if company.get("balance", 0) < e["cost"]:
        await callback.answer(f"❌ Нужно {fmt(e['cost'])}$", show_alert=True)
        return
    company["balance"]        -= e["cost"]
    company["employees"][key]  = company["employees"].get(key, 0) + 1
    new_ach = check_achievements(company)
    save_user_data()
    await callback.answer(f"✅ {e['name']} нанят!", show_alert=False)
    await callback.message.edit_text(emp_text(company), parse_mode="HTML", reply_markup=emp_kb(company))
    if new_ach:
        await callback.message.answer(
            "🏅 <b>Новые достижения!</b>\n" + "\n".join(f"• {a}" for a in new_ach),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "sk_hire_no")
async def cb_sk_hire_no(callback: CallbackQuery):
    await callback.answer("❌ Нет средств или свободных мест.", show_alert=True)


@router.callback_query(F.data.startswith("sk_fire:"))
async def cb_sk_fire(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    key = callback.data.split(":")[1]
    e   = EMPLOYEES.get(key)
    cnt = company["employees"].get(key, 0)
    if cnt <= 0:
        await callback.answer("❌ Нет таких сотрудников.", show_alert=True)
        return
    company["employees"][key] = cnt - 1
    save_user_data()
    await callback.answer(f"👋 {e['name']} уволен.", show_alert=False)
    await callback.message.edit_text(emp_text(company), parse_mode="HTML", reply_markup=emp_kb(company))


# ══════════════════════════════════════════════════════════════
#  СКЛАД
# ══════════════════════════════════════════════════════════════

def wh_text(company: dict) -> str:
    used = warehouse_used(company)
    wmax = warehouse_max(company)
    lines = []
    for key, r in RESOURCES.items():
        amt   = company["resources"].get(key, 0)
        price = r["price"] * RES_BUY_PACK
        lines.append(f"  {r['name']}: <b>{amt} {r['unit']}</b> | ×{RES_BUY_PACK} = {fmt(price)}$")
    return (
        f"📦 <b>Склад</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Занято: <b>{used}/{wmax}</b>\n\n"
        + "\n".join(lines) +
        f"\n\n💰 Баланс компании: <b>{fmt(company['balance'])}$</b>"
    )


def wh_kb(company: dict) -> InlineKeyboardMarkup:
    wmax = warehouse_max(company)
    used = warehouse_used(company)
    rows = []
    for key, r in RESOURCES.items():
        price   = r["price"] * RES_BUY_PACK
        can_buy = (
            company.get("balance", 0) >= price and
            used + RES_BUY_PACK <= wmax
        )
        rows.append([InlineKeyboardButton(
            text=f"🛒 {r['name']} ×{RES_BUY_PACK}",
            callback_data=f"sk_buy_res:{key}" if can_buy else "sk_res_no"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sk_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "sk_warehouse")
async def cb_sk_warehouse(callback: CallbackQuery):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(wh_text(company), parse_mode="HTML", reply_markup=wh_kb(company))
    await callback.answer()


@router.callback_query(F.data.startswith("sk_buy_res:"))
async def cb_sk_buy_res(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    key   = callback.data.split(":")[1]
    r     = RESOURCES.get(key)
    if not r:
        await callback.answer("Неверный ресурс.", show_alert=True)
        return
    price = r["price"] * RES_BUY_PACK
    if company.get("balance", 0) < price:
        await callback.answer(f"❌ Нужно {fmt(price)}$", show_alert=True)
        return
    if warehouse_used(company) + RES_BUY_PACK > warehouse_max(company):
        await callback.answer("❌ Склад переполнен! Улучшите офис.", show_alert=True)
        return
    company["balance"]         -= price
    company["resources"][key]   = company["resources"].get(key, 0) + RES_BUY_PACK
    save_user_data()
    await callback.answer(f"✅ Куплено {RES_BUY_PACK} ед. {r['name']}!", show_alert=False)
    await callback.message.edit_text(wh_text(company), parse_mode="HTML", reply_markup=wh_kb(company))


@router.callback_query(F.data == "sk_res_no")
async def cb_sk_res_no(callback: CallbackQuery):
    await callback.answer("❌ Нет средств или склад заполнен.", show_alert=True)


# ══════════════════════════════════════════════════════════════
#  ТЕХНИКА
# ══════════════════════════════════════════════════════════════

def mach_text(company: dict) -> str:
    office = OFFICES[company.get("office_level", 1)]
    total  = _total_mach(company)
    mach_speed = sum(MACHINES[k]["speed"] * v for k, v in company["machines"].items())
    lines = []
    for key, m in MACHINES.items():
        cnt = company["machines"].get(key, 0)
        lines.append(f"  {m['name']}: <b>{cnt} шт.</b> | ⚡+{m['speed']}% | {fmt(m['cost'])}$")
    return (
        f"🚜 <b>Техника</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Всего: <b>{total}/{office['max_mach']}</b>\n\n"
        + "\n".join(lines) +
        f"\n\n⚡ Бонус скорости от техники: <b>+{mach_speed:.0f}%</b>\n"
        f"💰 Баланс компании: <b>{fmt(company['balance'])}$</b>"
    )


def mach_kb(company: dict) -> InlineKeyboardMarkup:
    office = OFFICES[company.get("office_level", 1)]
    total  = _total_mach(company)
    rows   = []
    for key, m in MACHINES.items():
        cnt     = company["machines"].get(key, 0)
        can_buy = total < office["max_mach"] and company.get("balance", 0) >= m["cost"]
        rows.append([
            InlineKeyboardButton(text=f"➕ {m['name']}", callback_data=f"sk_buy_mach:{key}" if can_buy else "sk_mach_no"),
            InlineKeyboardButton(text=f"➖ ({cnt})",      callback_data=f"sk_sell_mach:{key}"),
        ])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sk_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "sk_machines")
async def cb_sk_machines(callback: CallbackQuery):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(mach_text(company), parse_mode="HTML", reply_markup=mach_kb(company))
    await callback.answer()


@router.callback_query(F.data.startswith("sk_buy_mach:"))
async def cb_sk_buy_mach(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    key = callback.data.split(":")[1]
    m   = MACHINES.get(key)
    if not m:
        await callback.answer("Неверный тип.", show_alert=True)
        return
    office = OFFICES[company.get("office_level", 1)]
    if _total_mach(company) >= office["max_mach"]:
        await callback.answer("❌ Нет места! Улучшите офис.", show_alert=True)
        return
    if company.get("balance", 0) < m["cost"]:
        await callback.answer(f"❌ Нужно {fmt(m['cost'])}$", show_alert=True)
        return
    company["balance"]      -= m["cost"]
    company["machines"][key] = company["machines"].get(key, 0) + 1
    save_user_data()
    await callback.answer(f"✅ {m['name']} куплен!", show_alert=False)
    await callback.message.edit_text(mach_text(company), parse_mode="HTML", reply_markup=mach_kb(company))


@router.callback_query(F.data == "sk_mach_no")
async def cb_sk_mach_no(callback: CallbackQuery):
    await callback.answer("❌ Нет средств или места для техники.", show_alert=True)


@router.callback_query(F.data.startswith("sk_sell_mach:"))
async def cb_sk_sell_mach(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    key = callback.data.split(":")[1]
    m   = MACHINES.get(key)
    cnt = company["machines"].get(key, 0)
    if cnt <= 0:
        await callback.answer("❌ Нет такой техники.", show_alert=True)
        return
    refund = int(m["cost"] * 0.5)
    company["machines"][key] = cnt - 1
    company["balance"]        = company.get("balance", 0) + refund
    save_user_data()
    await callback.answer(f"✅ {m['name']} продан за {fmt(refund)}$.", show_alert=False)
    await callback.message.edit_text(mach_text(company), parse_mode="HTML", reply_markup=mach_kb(company))


# ══════════════════════════════════════════════════════════════
#  ИССЛЕДОВАНИЯ
# ══════════════════════════════════════════════════════════════

def research_text(company: dict) -> str:
    lvl  = company.get("research_level", 0)
    r    = RESEARCH[lvl]
    nlvl = lvl + 1
    nr   = RESEARCH.get(nlvl)

    unlocked = [b["name"] for bkey, b in BUILDINGS.items() if b["req_research"] <= lvl]
    locked   = [b["name"] for bkey, b in BUILDINGS.items() if b["req_research"] == nlvl] if nr else []

    next_section = ""
    if nr:
        next_section = (
            f"\n\n<b>Следующий уровень:</b> {nr['name']}\n"
            f"  💰 Стоимость: {fmt(nr['cost'])}$\n"
            f"  ⚡ Ускорение: +{nr['speed']}%\n"
            f"  💰 Бонус наград: +{nr['reward']}%"
        )
        if locked:
            next_section += "\n  🔓 Открывает: " + ", ".join(locked)

    return (
        f"🔬 <b>Проектное бюро</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Уровень: <b>{lvl}/{MAX_RESEARCH}</b> — {r['name']}\n"
        f"⚡ Бонус ускорения: <b>+{r['speed']}%</b>\n"
        f"💰 Бонус наград: <b>+{r['reward']}%</b>\n\n"
        f"<b>Доступные объекты ({len(unlocked)}):</b>\n"
        + "\n".join(f"  ✅ {n}" for n in unlocked)
        + next_section
        + f"\n\n💰 Баланс компании: <b>{fmt(company.get('balance', 0))}$</b>"
    )


def research_kb(company: dict) -> InlineKeyboardMarkup:
    lvl = company.get("research_level", 0)
    rows = []
    if lvl < MAX_RESEARCH:
        nr  = RESEARCH[lvl + 1]
        can = company.get("balance", 0) >= nr["cost"]
        rows.append([InlineKeyboardButton(
            text=f"🔬 Исследовать — {fmt(nr['cost'])}$",
            callback_data="sk_do_research" if can else "sk_res_bal_no"
        )])
    else:
        rows.append([InlineKeyboardButton(text="⭐ Максимальный уровень", callback_data="sk_noop")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sk_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "sk_research")
async def cb_sk_research(callback: CallbackQuery):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(research_text(company), parse_mode="HTML", reply_markup=research_kb(company))
    await callback.answer()


@router.callback_query(F.data == "sk_do_research")
async def cb_sk_do_research(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    lvl = company.get("research_level", 0)
    if lvl >= MAX_RESEARCH:
        await callback.answer("Максимальный уровень!", show_alert=True)
        return
    nr = RESEARCH[lvl + 1]
    if company.get("balance", 0) < nr["cost"]:
        await callback.answer(f"❌ Нужно {fmt(nr['cost'])}$", show_alert=True)
        return
    company["balance"]        -= nr["cost"]
    company["research_level"]  = lvl + 1
    save_user_data()
    await callback.answer(f"✅ {nr['name']} исследовано!", show_alert=True)
    await callback.message.edit_text(research_text(company), parse_mode="HTML", reply_markup=research_kb(company))


@router.callback_query(F.data == "sk_res_bal_no")
async def cb_sk_res_bal_no(callback: CallbackQuery):
    await callback.answer("❌ Недостаточно средств на счёте компании.", show_alert=True)


# ══════════════════════════════════════════════════════════════
#  КОНТРАКТЫ
# ══════════════════════════════════════════════════════════════

def contracts_text(company: dict) -> str:
    rep    = company.get("reputation", 0)
    active = company.get("contracts", [])
    office = OFFICES[company.get("office_level", 1)]

    lines = []
    for c in active:
        left   = c["finish_at"] - int(time.time())
        status = fmt_time(left) if left > 0 else "✅ Готов!"
        lines.append(f"  [{c['id']}] {c['name']}\n     💰 {fmt(c['reward'])}$ | ⭐+{c['rep']} | {status}")

    avail = []
    for ctype, ct in CONTRACT_TYPES.items():
        if rep >= ct["rep_req"]:
            avail.append(f"  ✅ {ct['name']} ({fmt(ct['min'])}–{fmt(ct['max'])}$)")
        else:
            avail.append(f"  🔒 {ct['name']} — нужно {ct['rep_req']} репутации")

    return (
        f"📋 <b>Контракты</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ Репутация: <b>{rep}</b> — {rep_title(rep)}\n"
        f"📂 Слоты: <b>{len(active)}/{office['max_contracts']}</b>\n"
        f"✅ Выполнено всего: <b>{company.get('contracts_done', 0)}</b>\n\n"
        f"<b>Активные контракты:</b>\n"
        + ("\n".join(lines) if lines else "  Нет активных контрактов") +
        f"\n\n<b>Доступные типы:</b>\n" + "\n".join(avail)
    )


def contracts_kb(company: dict) -> InlineKeyboardMarkup:
    rep    = company.get("reputation", 0)
    active = company.get("contracts", [])
    office = OFFICES[company.get("office_level", 1)]
    rows   = []

    for c in active:
        if int(time.time()) >= c["finish_at"]:
            rows.append([InlineKeyboardButton(
                text=f"✅ Получить {fmt(c['reward'])}$ [{c['id']}]",
                callback_data=f"sk_coll_c:{c['id']}"
            )])

    if len(active) < office["max_contracts"]:
        for ctype, ct in CONTRACT_TYPES.items():
            if rep >= ct["rep_req"]:
                rows.append([InlineKeyboardButton(
                    text=f"📋 Взять {ct['name']}",
                    callback_data=f"sk_take_c:{ctype}"
                )])

    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sk_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "sk_contracts")
async def cb_sk_contracts(callback: CallbackQuery):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(contracts_text(company), parse_mode="HTML", reply_markup=contracts_kb(company))
    await callback.answer()


@router.callback_query(F.data.startswith("sk_take_c:"))
async def cb_sk_take_c(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    ctype = callback.data.split(":")[1]
    ct    = CONTRACT_TYPES.get(ctype)
    if not ct:
        await callback.answer("Неверный тип.", show_alert=True)
        return
    office = OFFICES[company.get("office_level", 1)]
    active = company.get("contracts", [])
    if len(active) >= office["max_contracts"]:
        await callback.answer("❌ Все слоты заняты!", show_alert=True)
        return
    if company.get("reputation", 0) < ct["rep_req"]:
        await callback.answer(f"❌ Нужно {ct['rep_req']} репутации!", show_alert=True)
        return
    reward   = random.randint(ct["min"], ct["max"])
    rep_mult = 1 + company.get("reputation", 0) * 0.01
    reward   = int(reward * rep_mult)
    contract = {
        "id":       int(time.time() * 1000) % 100_000,
        "type":     ctype,
        "name":     ct["name"],
        "reward":   reward,
        "rep":      ct["rep"],
        "started":  int(time.time()),
        "finish_at":int(time.time()) + ct["dur"],
    }
    active.append(contract)
    company["contracts"] = active
    save_user_data()
    await callback.answer(f"✅ Контракт взят! Время: {fmt_time(ct['dur'])}", show_alert=True)
    await callback.message.edit_text(contracts_text(company), parse_mode="HTML", reply_markup=contracts_kb(company))


@router.callback_query(F.data.startswith("sk_coll_c:"))
async def cb_sk_coll_c(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    cid    = int(callback.data.split(":")[1])
    active = company.get("contracts", [])
    c      = next((x for x in active if x["id"] == cid), None)
    if not c:
        await callback.answer("Контракт не найден.", show_alert=True)
        return
    if int(time.time()) < c["finish_at"]:
        left = c["finish_at"] - int(time.time())
        await callback.answer(f"⏳ Ещё не готово! Осталось: {fmt_time(left)}", show_alert=True)
        return
    company["balance"]         = company.get("balance", 0) + c["reward"]
    company["reputation"]      = company.get("reputation", 0) + c["rep"]
    company["contracts"]       = [x for x in active if x["id"] != cid]
    company["contracts_done"]  = company.get("contracts_done", 0) + 1
    new_ach = check_achievements(company)
    save_user_data()
    text = (
        f"✅ <b>Контракт выполнен!</b>\n\n"
        f"{c['name']}\n"
        f"💰 +{fmt(c['reward'])}$\n"
        f"⭐ +{c['rep']} репутации (итого: {company['reputation']})\n"
        f"🏦 Баланс: {fmt(company['balance'])}$"
    )
    if new_ach:
        text += "\n\n🏅 <b>Новые достижения:</b>\n" + "\n".join(f"• {a}" for a in new_ach)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_kb())
    await callback.answer()


# ══════════════════════════════════════════════════════════════
#  ОФИС
# ══════════════════════════════════════════════════════════════

def office_text(company: dict) -> str:
    lvl    = company.get("office_level", 1)
    office = OFFICES[lvl]
    noffice = OFFICES.get(lvl + 1)
    move_cost = noffice["price"] * 2 if noffice else 0

    next_section = ""
    if noffice:
        next_section = (
            f"\n\n<b>Следующий офис:</b> {noffice['name']}\n"
            f"  👷 Мест: {noffice['max_emp']}\n"
            f"  🚜 Техники: {noffice['max_mach']}\n"
            f"  📦 Склад: {noffice['warehouse']} ед.\n"
            f"  📋 Контрактов: {noffice['max_contracts']}\n"
            f"  💰 Переезд: {fmt(move_cost)}$"
        )
    return (
        f"🏢 <b>Офис</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Текущий: <b>{office['name']}</b> (ур. {lvl}/{MAX_OFFICE})\n\n"
        f"👷 Мест: <b>{_total_emp(company)}/{office['max_emp']}</b>\n"
        f"🚜 Техники: <b>{_total_mach(company)}/{office['max_mach']}</b>\n"
        f"📦 Склад: <b>{warehouse_used(company)}/{office['warehouse']}</b>\n"
        f"📋 Контрактов: <b>{len(company.get('contracts', []))}/{office['max_contracts']}</b>"
        f"{next_section}"
        f"\n\n💰 Баланс компании: <b>{fmt(company.get('balance', 0))}$</b>"
    )


def office_kb(company: dict) -> InlineKeyboardMarkup:
    lvl  = company.get("office_level", 1)
    rows = []
    if lvl < MAX_OFFICE:
        noffice   = OFFICES[lvl + 1]
        move_cost = noffice["price"] * 2
        can       = company.get("balance", 0) >= move_cost
        rows.append([InlineKeyboardButton(
            text=f"🏗 Переехать — {fmt(move_cost)}$",
            callback_data="sk_upgrade_office" if can else "sk_office_no"
        )])
    else:
        rows.append([InlineKeyboardButton(text="⭐ Максимальный офис", callback_data="sk_noop")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sk_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "sk_office")
async def cb_sk_office(callback: CallbackQuery):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(office_text(company), parse_mode="HTML", reply_markup=office_kb(company))
    await callback.answer()


@router.callback_query(F.data == "sk_upgrade_office")
async def cb_sk_upgrade_office(callback: CallbackQuery):
    user_id = callback.from_user.id
    company = get_company(user_id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    lvl = company.get("office_level", 1)
    if lvl >= MAX_OFFICE:
        await callback.answer("Уже максимальный офис!", show_alert=True)
        return
    noffice   = OFFICES[lvl + 1]
    move_cost = noffice["price"] * 2
    if company.get("balance", 0) < move_cost:
        await callback.answer(f"❌ Нужно {fmt(move_cost)}$", show_alert=True)
        return
    company["balance"]      -= move_cost
    company["office_level"]  = lvl + 1
    new_ach = check_achievements(company)
    save_user_data()
    await callback.answer(f"✅ Переехали в {noffice['name']}!", show_alert=True)
    await callback.message.edit_text(office_text(company), parse_mode="HTML", reply_markup=office_kb(company))
    if new_ach:
        await callback.message.answer(
            "🏅 <b>Новые достижения!</b>\n" + "\n".join(f"• {a}" for a in new_ach),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "sk_office_no")
async def cb_sk_office_no(callback: CallbackQuery):
    await callback.answer("❌ Недостаточно средств.", show_alert=True)


# ══════════════════════════════════════════════════════════════
#  НАСТРОЙКИ И ДОСТИЖЕНИЯ
# ══════════════════════════════════════════════════════════════

def settings_text(company: dict) -> str:
    earned  = company.get("achievements", [])
    achiev  = [a for a in ACHIEVEMENTS if a["id"] in earned]
    locked  = [a for a in ACHIEVEMENTS if a["id"] not in earned]
    lines_e = [f"  🏅 <b>{a['name']}</b> — {a['desc']}" for a in achiev]
    lines_l = [f"  🔒 {a['name']} — {a['desc']}" for a in locked]
    name    = company.get("name", "Моя компания")
    return (
        f"⚙️ <b>Настройки</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🏗 Название: <b>{name}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏅 <b>Достижения: {len(earned)}/{len(ACHIEVEMENTS)}</b>\n\n"
        + ("\n".join(lines_e) if lines_e else "  Пока нет достижений") +
        (f"\n\n<b>Не получено:</b>\n" + "\n".join(lines_l) if lines_l else "")
    )


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Переименовать компанию", callback_data="sk_rename")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="sk_main")],
    ])


@router.callback_query(F.data == "sk_settings")
async def cb_sk_settings(callback: CallbackQuery):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    new_ach = check_achievements(company)
    save_user_data()
    await callback.message.edit_text(settings_text(company), parse_mode="HTML", reply_markup=settings_kb())
    if new_ach:
        await callback.message.answer(
            "🏅 <b>Новые достижения!</b>\n" + "\n".join(f"• {a}" for a in new_ach),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "sk_rename")
async def cb_sk_rename(callback: CallbackQuery, state: FSMContext):
    company = get_company(callback.from_user.id)
    if not company:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await state.set_state(SKSettings.rename)
    await callback.message.edit_text(
        f"✏️ <b>Переименование компании</b>\n\n"
        f"Текущее название: <b>{company.get('name', 'Моя компания')}</b>\n\n"
        f"Введите новое название (макс. 32 символа):",
        parse_mode="HTML",
        reply_markup=back_kb("sk_settings")
    )
    await callback.answer()


@router.message(SKSettings.rename)
async def msg_sk_rename(message: Message, state: FSMContext):
    user_id = message.from_user.id
    company = get_company(user_id)
    if not company:
        await state.clear()
        return
    name = message.text.strip()
    if len(name) > 32:
        await message.answer("❌ Слишком длинное название (максимум 32 символа). Введите другое:")
        return
    if len(name) < 2:
        await message.answer("❌ Слишком короткое название (минимум 2 символа). Введите другое:")
        return
    old_name = company.get("name", "Моя компания")
    company["name"] = name
    save_user_data()
    await state.clear()
    await message.answer(
        f"✅ <b>Компания переименована!</b>\n\n"
        f"Было: <b>{old_name}</b>\n"
        f"Стало: <b>{name}</b>",
        parse_mode="HTML",
        reply_markup=main_kb()
    )
