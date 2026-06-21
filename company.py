"""
🏗 СТРОИТЕЛЬНАЯ КОМПАНИЯ
Команды: стройка, ск
"""
import time
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import utils as _utils
from utils import get_user, get_balance, update_balance, save_user_data

router = Router()

# ══════════════════════════════════════════════════════════════
#  КОНФИГ
# ══════════════════════════════════════════════════════════════

REGISTRATION_COST  = 100_000
STARTING_BALANCE   = 50_000
BANKRUPTCY_LIMIT   = -1_000_000
BANKRUPTCY_TIMEOUT = 3600          # секунд до банкротства

COMMISSION_PREMIUM = 0.03
COMMISSION_VIP     = 0.05
COMMISSION_NORMAL  = 0.10
COMMISSION_MIN     = 10

WORKPLACE_COST  = 5_000            # $ за рабочее место
TECH_COST       = 50_000           # $ за единицу техники (разовая)
TECH_RENT_HOUR  = 3_600            # $/ч аренда техники
TECH_CAPACITY   = 6_000            # заказчиков на 1 единицу техники
PROMO_COST      = 10_000           # $ за запуск маркетинга
PROMO_DURATION  = 5 * 60           # 5 минут
PROMO_HOURLY    = 2_500            # $/ч пока маркетинг активен (на сервис)
PROMO_QUICK_COST     = 3_000       # $ за быстрый маркетинг (5 мин)
PROMO_QUICK_DURATION = 5 * 60      # 5 минут
PROMO_QUICK_GAIN_PCT = 5           # % аудитории от быстрого маркетинга

# ─── Штабы ────────────────────────────────────────────────────
OFFICES = {
    1: {"name": "Бытовка",          "max_places": 10,  "max_tech": 5,   "max_objects": 1, "rent_day": 10_000},
    2: {"name": "Прорабская",       "max_places": 30,  "max_tech": 20,  "max_objects": 2, "rent_day": 50_000},
    3: {"name": "Проектный офис",   "max_places": 60,  "max_tech": 60,  "max_objects": 3, "rent_day": 200_000},
    4: {"name": "Инженерный центр", "max_places": 180, "max_tech": 120, "max_objects": 4, "rent_day": 900_000},
    5: {"name": "Головной офис",    "max_places": 360, "max_tech": 300, "max_objects": 5, "rent_day": 3_000_000},
}
MAX_OFFICE = 5

# ─── Строительные технологии (Фреймворк) ──────────────────────
FRAMEWORKS = {
    0: {"name": "Кустарная",      "slots": 2,  "max_level": 1, "cost": 0},
    1: {"name": "Типовая",        "slots": 4,  "max_level": 2, "cost": 100_000},
    2: {"name": "Современная",    "slots": 6,  "max_level": 3, "cost": 500_000},
    3: {"name": "Передовая",      "slots": 8,  "max_level": 4, "cost": 2_000_000},
    4: {"name": "Инновационная",  "slots": 99, "max_level": 5, "cost": 8_000_000},
}
MAX_FRAMEWORK = 4

# ─── Инновации (Исследования) ─────────────────────────────────
RESEARCH = {
    0: {"name": "Нет",                   "cost": 0,          "promo_bonus": 0,  "income_bonus": 0,  "res_bonus": 0},
    1: {"name": "Оптимизация процессов", "cost": 100_000,    "promo_bonus": 20, "income_bonus": 0,  "res_bonus": 0},
    2: {"name": "BIM-технологии",        "cost": 500_000,    "promo_bonus": 20, "income_bonus": 0,  "res_bonus": 0},
    3: {"name": "Умные технологии",      "cost": 2_000_000,  "promo_bonus": 20, "income_bonus": 0,  "res_bonus": 0},
    4: {"name": "Роботизация",           "cost": 8_000_000,  "promo_bonus": 20, "income_bonus": 20, "res_bonus": 0},
    5: {"name": "Нейросети",             "cost": 25_000_000, "promo_bonus": 20, "income_bonus": 20, "res_bonus": 30},
}
MAX_RESEARCH = 5

# ─── Персонал ─────────────────────────────────────────────────
# Эмодзи намеренно совпадают с Matvey4ikbot для единого UX
EMPLOYEES = {
    "researcher": {
        "name": "📐 Инженер-проектировщик",
        "hire": 8_000, "salary_hour": 2_000,
        "gen": {"research": 100, "network": 50},
        "emoji": "📐",
    },
    "developer": {
        "name": "🔨 Прораб",
        "hire": 6_000, "salary_hour": 1_500,
        "gen": {"dev": 100, "brick": 50},
        "emoji": "🔨",
    },
    "designer": {
        "name": "🎨 Архитектор",
        "hire": 7_000, "salary_hour": 1_800,
        "gen": {"design": 100, "module": 50},
        "emoji": "🎨",
    },
}

# ─── Виды строительных работ (Функции) ────────────────────────
FUNCTIONS = {
    "search":    {"name": "🏗 Монтажные работы",     "audience": 50_000,  "req_research": 0, "cost_money": 10_000, "cost_res": {"dev": 20, "brick": 10, "network": 5}},
    "chat":      {"name": "🔌 Электромонтаж",         "audience": 80_000,  "req_research": 0, "cost_money": 15_000, "cost_res": {"dev": 15, "module": 10, "network": 10}},
    "notify":    {"name": "💧 Сантехника",            "audience": 40_000,  "req_research": 0, "cost_money": 8_000,  "cost_res": {"dev": 10, "brick": 10, "module": 5}},
    "analytics": {"name": "🪟 Остекление",            "audience": 60_000,  "req_research": 0, "cost_money": 12_000, "cost_res": {"research": 25, "dev": 10, "module": 5}},
    "auth":      {"name": "🔒 Охрана и безопасность", "audience": 30_000,  "req_research": 0, "cost_money": 10_000, "cost_res": {"dev": 15, "brick": 15, "network": 10}},
    "ads":       {"name": "📢 Маркетинг-отдел",       "audience": 0,       "req_research": 0, "cost_money": 20_000, "cost_res": {"design": 20, "module": 15, "network": 10}},
    "recommend": {"name": "🎯 Дизайн интерьера",      "audience": 70_000,  "req_research": 2, "cost_money": 25_000, "cost_res": {"research": 30, "dev": 20, "design": 15}},
    "payments":  {"name": "💎 Премиум-отделка",       "audience": 100_000, "req_research": 3, "cost_money": 30_000, "cost_res": {"dev": 25, "brick": 20, "network": 20}},
}

# ─── Типы объектов ────────────────────────────────────────────
OBJECT_TYPES = {
    "mobile": "🏠 Жилой дом",
    "web":    "🏢 Торговый центр",
    "game":   "🏭 Промышленный объект",
    "api":    "🌉 Инфраструктура",
    "market": "🏗 Жилой комплекс",
}

# ─── Строительные контракты ───────────────────────────────────
CONTRACTS = {
    1: {"name": "Частная застройка",    "min": 50_000,    "max": 200_000,   "dur": 4*3600,  "ads_level": 1},
    2: {"name": "Коммерческая стройка", "min": 300_000,   "max": 1_000_000, "dur": 12*3600, "ads_level": 2},
    3: {"name": "Госзаказ",             "min": 2_000_000, "max": 8_000_000, "dur": 24*3600, "ads_level": 3},
}

# ─── Достижения ───────────────────────────────────────────────
ACHIEVEMENTS = [
    {"id": "first_contract",  "name": "📋 Первый объект",       "desc": "Сдать первый строительный контракт",    "check": lambda c: c.get("contracts_done", 0) >= 1},
    {"id": "contracts_10",    "name": "📑 Подрядчик",           "desc": "Выполнить 10 контрактов",               "check": lambda c: c.get("contracts_done", 0) >= 10},
    {"id": "contracts_50",    "name": "🏆 Строительный магнат", "desc": "Выполнить 50 контрактов",               "check": lambda c: c.get("contracts_done", 0) >= 50},
    {"id": "audience_100k",   "name": "👷 100к заказчиков",     "desc": "Привлечь 100 000 заказчиков",           "check": lambda c: _total_audience(c) >= 100_000},
    {"id": "audience_1m",     "name": "🌍 Миллион",             "desc": "Привлечь 1 000 000 заказчиков",         "check": lambda c: _total_audience(c) >= 1_000_000},
    {"id": "staff_10",        "name": "👥 Бригада",             "desc": "Нанять 10 сотрудников",                 "check": lambda c: _total_emp(c) >= 10},
    {"id": "staff_50",        "name": "🏢 Большая компания",    "desc": "Нанять 50 сотрудников",                 "check": lambda c: _total_emp(c) >= 50},
    {"id": "office_4",        "name": "🏗 Инженерный центр",    "desc": "Открыть Инженерный центр",              "check": lambda c: c.get("office_level", 1) >= 4},
    {"id": "office_5",        "name": "🏛 Головной офис",       "desc": "Открыть Головной офис",                 "check": lambda c: c.get("office_level", 1) >= 5},
    {"id": "tech_4",          "name": "⚙️ Передовые техно.",    "desc": "Освоить Передовые технологии",          "check": lambda c: c.get("framework_level", 0) >= 3},
    {"id": "tech_max",        "name": "⚡ Инновационные техно.","desc": "Освоить Инновационные технологии",      "check": lambda c: c.get("framework_level", 0) >= 4},
    {"id": "research_max",    "name": "🤖 Нейросети",           "desc": "Достичь макс. уровня инноваций",        "check": lambda c: c.get("research_level", 0) >= 5},
    {"id": "max_objects",     "name": "🏙 Застройщик",          "desc": "Иметь 5 активных объектов",             "check": lambda c: len(c.get("services", [])) >= 5},
]

HELP_TEXT = (
    "ℹ️ <b>Помощь по строительной компании</b>\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "<b>Команда:</b> стройка\n"
    "<b>Счёт:</b> стройка пополнить [сумма], стройка снять [сумма|все]\n\n"
    "<b>Комиссия на пополнение и снятие:</b> обычная 10%, VIP 5%, Premium 3%.\n"
    "Комиссия удерживается только для сумм от 10$.\n\n"
    "<b>Создание:</b>\n"
    "Если компании нет, команда стройка покажет описание и кнопку создания.\n"
    "Стоимость создания: 100 000$, из них 50 000$ сразу на счёте компании.\n\n"
    "<b>Как запустить:</b>\n"
    "1) Создай объект (жилой дом, ТЦ...)\n"
    "2) В объекте добавь нужные виды работ\n"
    "3) Запусти 🚀 Маркетинг (привлечение заказчиков)\n"
    "4) Установи работу 📢 Маркетинг-отдел и принимай контракты\n\n"
    "<b>Зачем нужны работы:</b> они повышают лимит заказчиков объекта.\n"
    "Техника этот лимит не увеличивает: она даёт запас по загрузке.\n\n"
    "<b>Откуда доход:</b>\n"
    "• Доход идёт от контрактов (📢 Маркетинг-отдел) на счёт компании\n"
    "• Чем больше заказчиков и лучше объект, тем выше доход\n"
    "• Если техника перегружена, объект теряет эффективность\n\n"
    "<b>Ресурсы и компоненты:</b>\n"
    "• 📐 Проект, 🔨 Труд, 🎨 Дизайн — очки ресурсов\n"
    "• 📐 дают инженеры, 🔨 дают прорабы, 🎨 дают архитекторы\n"
    "• 🧱 Кирпич, 🪵 Блок, ⚡ Кабель — компоненты для работ\n"
    "• 🧱 дают прорабы, 🪵 дают архитекторы, ⚡ дают инженеры\n\n"
    "<b>Технологии строительства:</b>\n"
    "• Технология ограничивает количество работ на объекте\n"
    "• Технология ограничивает максимальный уровень работ\n\n"
    "<b>Важно:</b>\n"
    "• 1 сотрудник = 1 рабочее место\n"
    "• Штаб ограничивает места и технику\n"
    "• Переезд: цена = x2 аренды нового штаба\n"
    "• Банкротство: если долг ниже -1 000 000$ дольше 1 часа\n"
    "• При критическом долге бот пришлёт уведомление и за 5 минут до банкротства\n\n"
    "<b>Интерфейс:</b>\n"
    "• В главном меню кнопки 🏅 Настройки и 🔄 Обновить в одном ряду"
)


# ══════════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ══════════════════════════════════════════════════════════════

def get_company(user_id) -> dict | None:
    return get_user(user_id).get("company")


def create_company(user_id, name: str = "Моя компания") -> dict:
    user = get_user(user_id)
    c = {
        "name":                 name,
        "balance":              STARTING_BALANCE,
        "office_level":         1,
        "workplaces_purchased": 0,
        "employees":            {k: 0 for k in EMPLOYEES},
        "resources":            {"research": 0, "dev": 0, "design": 0, "brick": 0, "module": 0, "network": 0},
        "last_calc":            int(time.time()),
        "services":             [],
        "framework_level":      0,
        "research_level":       0,
        "debt_since":           None,
        "warned_5min":          False,
        "created_at":           int(time.time()),
        "achievements":         [],
        "contracts_done":       0,
    }
    user["company"] = c
    save_user_data()
    return c


def fmt(n) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def fmt_time(sec: int) -> str:
    if sec <= 0:
        return "✅ Готово"
    h, r = divmod(int(sec), 3600)
    m, s = divmod(r, 60)
    if h > 0:   return f"{h}ч {m}м"
    if m > 0:   return f"{m}м {s}с"
    return f"{s}с"


def _total_emp(c: dict) -> int:
    return sum(c.get("employees", {}).values())


def _total_audience(c: dict) -> int:
    return sum(s.get("audience", 0) for s in c.get("services", []))


def _total_tech(c: dict) -> int:
    return sum(s.get("servers", 0) for s in c.get("services", []))


def _obj_max_audience(obj: dict, fw_level: int) -> int:
    max_lvl = FRAMEWORKS[fw_level]["max_level"]
    return sum(
        FUNCTIONS[fk]["audience"] * min(flvl, max_lvl)
        for fk, flvl in obj.get("functions", {}).items()
        if fk in FUNCTIONS
    )


def _obj_tech_capacity(obj: dict) -> int:
    return obj.get("servers", 0) * TECH_CAPACITY


def _obj_load(obj: dict) -> float:
    cap = _obj_tech_capacity(obj)
    if cap == 0:
        return 2.0 if obj.get("audience", 0) > 0 else 0.0
    return obj.get("audience", 0) / cap


def _obj_efficiency(obj: dict) -> float:
    load = _obj_load(obj)
    if load <= 0.7:  return 1.0
    if load <= 0.9:  return 0.95
    if load <= 1.0:  return 0.85
    if load <= 1.2:  return 0.70
    return 0.50


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


def _promo_expense_hour(c: dict) -> int:
    now = int(time.time())
    return sum(
        PROMO_HOURLY
        for s in c.get("services", [])
        if s.get("promotion_finish") and s["promotion_finish"] > now
    )


def _income_per_hour(c: dict) -> int:
    res_b = 1 + RESEARCH[c.get("research_level", 0)]["income_bonus"] / 100
    total = 0
    for obj in c.get("services", []):
        contract = obj.get("ad_contract")
        if not contract:
            continue
        reward    = contract["reward"]
        dur_h     = max(1, contract["dur"] / 3600)
        eff       = _obj_efficiency(obj)
        aud_max   = _obj_max_audience(obj, c.get("framework_level", 0))
        aud_ratio = min(1.0, obj.get("audience", 0) / max(1, aud_max)) if aud_max > 0 else 0
        total    += int(reward / dur_h * eff * aud_ratio * res_b)
    return total


def _expenses_breakdown(c: dict) -> dict:
    office  = OFFICES[c.get("office_level", 1)]
    rent_h  = office["rent_day"] // 24
    tech_h  = _total_tech(c) * TECH_RENT_HOUR
    sal_h   = sum(EMPLOYEES[k]["salary_hour"] * v for k, v in c.get("employees", {}).items())
    promo_h = _promo_expense_hour(c)
    return {
        "rent":   rent_h,
        "tech":   tech_h,
        "salary": sal_h,
        "promo":  promo_h,
        "total":  rent_h + tech_h + sal_h + promo_h,
    }


def flush_passive(c: dict):
    now     = int(time.time())
    elapsed = max(0, now - c.get("last_calc", now))
    if elapsed <= 0:
        c["last_calc"] = now
        return
    hours = elapsed / 3600

    # ── Ресурсы от сотрудников
    res_mult = 1 + RESEARCH[c.get("research_level", 0)]["res_bonus"] / 100
    for etype, cnt in c.get("employees", {}).items():
        if cnt <= 0:
            continue
        for rkey, rate in EMPLOYEES[etype]["gen"].items():
            c["resources"][rkey] = c["resources"].get(rkey, 0) + int(rate * cnt * hours * res_mult)

    # ── Завершение обычного маркетинга → прирост заказчиков (15%)
    for obj in c.get("services", []):
        pf = obj.get("promotion_finish")
        if pf and now >= pf:
            research = c.get("research_level", 0)
            promo_b  = sum(RESEARCH[i]["promo_bonus"] for i in range(1, research + 1))
            max_aud  = _obj_max_audience(obj, c.get("framework_level", 0))
            gain     = int(max_aud * 0.15 * (1 + promo_b / 100))
            obj["audience"] = min(max_aud, obj.get("audience", 0) + gain)
            obj["promotion_finish"] = None
        # ── Завершение быстрого маркетинга (5 мин) → прирост 5%
        qf = obj.get("quick_promo_finish")
        if qf and now >= qf:
            research = c.get("research_level", 0)
            promo_b  = sum(RESEARCH[i]["promo_bonus"] for i in range(1, research + 1))
            max_aud  = _obj_max_audience(obj, c.get("framework_level", 0))
            gain     = int(max_aud * (PROMO_QUICK_GAIN_PCT / 100) * (1 + promo_b / 100))
            obj["audience"] = min(max_aud, obj.get("audience", 0) + gain)
            obj["quick_promo_finish"] = None

    # ── Доход и расход
    inc = _income_per_hour(c)
    exp = _expenses_breakdown(c)["total"]
    c["balance"]  = c.get("balance", 0) + int(inc * hours) - int(exp * hours)
    c["last_calc"] = now


def check_bankruptcy_state(c: dict) -> str | None:
    """Возвращает: None | 'warn' | 'warn5' | 'debt' | 'bankrupt'"""
    if c.get("balance", 0) >= BANKRUPTCY_LIMIT:
        c["debt_since"]  = None
        c["warned_5min"] = False
        return None
    now = int(time.time())
    if not c.get("debt_since"):
        c["debt_since"] = now
        return "warn"
    elapsed = now - c["debt_since"]
    if elapsed >= BANKRUPTCY_TIMEOUT:
        return "bankrupt"
    if elapsed >= BANKRUPTCY_TIMEOUT - 300 and not c.get("warned_5min"):
        c["warned_5min"] = True
        return "warn5"
    return "debt"


def check_achievements(c: dict) -> list[str]:
    earned = c.get("achievements", [])
    new    = []
    for ach in ACHIEVEMENTS:
        if ach["id"] not in earned:
            try:
                if ach["check"](c):
                    earned.append(ach["id"])
                    new.append(ach["name"])
            except Exception:
                pass
    c["achievements"] = earned
    return new


# ══════════════════════════════════════════════════════════════
#  АВТОПРОВЕРКА ДОЛГА (APScheduler)
# ══════════════════════════════════════════════════════════════

async def check_company_debts(bot):
    """Запускать каждые 2 минуты через APScheduler."""
    try:
        all_users = dict(_utils.user_data)
    except Exception:
        return

    for user_id_str, user_data in all_users.items():
        c = user_data.get("company")
        if not c:
            continue
        flush_passive(c)
        state = check_bankruptcy_state(c)

        if state == "bankrupt":
            user_data.pop("company", None)
            save_user_data()
            try:
                await bot.send_message(
                    int(user_id_str),
                    "⛔ <b>Банкротство!</b>\n\n"
                    "Ваша строительная компания ликвидирована из-за долга ниже -1 000 000$ более 1 часа.\n"
                    "Вы можете основать новую компанию командой <b>стройка</b>.",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        elif state == "warn":
            save_user_data()
            try:
                await bot.send_message(
                    int(user_id_str),
                    "🔔 <b>Критический долг!</b>\n\n"
                    f"Баланс компании: <b>{fmt(c.get('balance', 0))}$</b>\n"
                    "Если долг останется ниже <b>-1 000 000$</b> более 1 часа — наступит банкротство!\n\n"
                    "Пополните счёт: <code>стройка пополнить [сумма]</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        elif state == "warn5":
            save_user_data()
            try:
                await bot.send_message(
                    int(user_id_str),
                    "🔴 <b>До банкротства менее 5 минут!</b>\n\n"
                    f"Баланс компании: <b>{fmt(c.get('balance', 0))}$</b>\n"
                    "Срочно пополните счёт: <code>стройка пополнить [сумма]</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        else:
            save_user_data()


# ══════════════════════════════════════════════════════════════
#  КЛАВИАТУРЫ
# ══════════════════════════════════════════════════════════════

def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏗 Объекты",      callback_data="co_objects"),
            InlineKeyboardButton(text="👷 Персонал",     callback_data="co_employees"),
        ],
        [
            InlineKeyboardButton(text="🏢 Штаб",         callback_data="co_office"),
            InlineKeyboardButton(text="⚙️ Технологии",   callback_data="co_framework"),
        ],
        [
            InlineKeyboardButton(text="💡 Инновации",    callback_data="co_research"),
            InlineKeyboardButton(text="🏅 Настройки",    callback_data="co_settings"),
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить",     callback_data="co_main"),
        ],
    ])


def back_kb(target: str = "co_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=target)],
    ])


# ══════════════════════════════════════════════════════════════
#  ТЕКСТ ГЛАВНОГО МЕНЮ
# ══════════════════════════════════════════════════════════════

def main_text(c: dict) -> str:
    office    = OFFICES[c.get("office_level", 1)]
    exp       = _expenses_breakdown(c)
    inc_h     = _income_per_hour(c)
    objs      = c.get("services", [])
    emp       = c.get("employees", {})
    res       = c.get("resources", {})
    bal       = c.get("balance", 0)
    name      = c.get("name", "Моя компания")
    emp_cnt   = _total_emp(c)
    tech_cnt  = _total_tech(c)
    total_aud = _total_audience(c)
    max_aud   = sum(_obj_max_audience(o, c.get("framework_level", 0)) for o in objs)
    total_cap = sum(_obj_tech_capacity(o) for o in objs)
    load_pct  = int(total_aud / max(1, total_cap) * 100) if total_cap > 0 else 0

    bk = check_bankruptcy_state(c)
    bk_line = ""
    if bk == "bankrupt":
        bk_line = "\n\n⛔ <b>БАНКРОТСТВО!</b>"
    elif bk == "warn5":
        bk_line = "\n\n🔴 <b>До банкротства &lt;5 минут!</b>"
    elif bk in ("warn", "debt"):
        bk_line = "\n\n🔔 <b>Критический долг!</b> Банкротство через 1 час."

    # порядок как в Matvey4ikbot: 💻/🔬/🎨
    dev = emp.get("developer", 0)
    res_e = emp.get("researcher", 0)
    des = emp.get("designer", 0)

    return (
        f"🏗 <b>{name}</b>\n\n"
        f"🏢 Штаб: <b>{office['name']}</b> ({emp_cnt}/{office['max_places']} мест)\n"
        f"🏷️ Аренда штаба: <b>{fmt(office['rent_day'])}$/сутки</b>\n"
        f"🏦 Счёт компании: <b>{fmt(bal)}$</b>\n"
        f"💰 Доход: <b>{fmt(inc_h)}$/час</b>\n"
        f"📉 Общий расход: <b>{fmt(exp['total'])}$/час</b>\n"
        f"   └ 🏷️ Штаб: {fmt(exp['rent'])}$/час\n"
        f"   └ 🚜 Техника: {fmt(exp['tech'])}$/час\n"
        f"   └ 👥 Зарплаты: {fmt(exp['salary'])}$/час\n"
        f"   └ 🚀 Маркетинг: {fmt(exp['promo'])}$/час\n\n"
        f"📊 <b>Сводка:</b>\n"
        f"Объекты: <b>{len(objs)}</b> | 👷 Сотрудники: <b>{emp_cnt}</b> "
        f"(💻{dev}/🔬{res_e}/🎨{des})\n"
        f"Заказчики: <b>{fmt(total_aud)}/{fmt(max_aud)}</b> | Загрузка: <b>{load_pct}%</b> ({fmt(total_aud)}/{fmt(total_cap)})\n"
        f"Техника в штабе: <b>{tech_cnt}/{office['max_tech']}</b>\n"
        f"Ресурсы: 🔬{fmt(res.get('research',0))} 💻{fmt(res.get('dev',0))} 🎨{fmt(res.get('design',0))}\n"
        f"Компоненты: 🧱{fmt(res.get('brick',0))} 🧩{fmt(res.get('module',0))} 🌐{fmt(res.get('network',0))}"
        f"{bk_line}\n\n"
        f"ℹ️ Помощь по компании: <code>помощь стройка</code>\n"
        f"🏗 Стройка"
    )


# ══════════════════════════════════════════════════════════════
#  ОСНОВНЫЕ ХЭНДЛЕРЫ
# ══════════════════════════════════════════════════════════════

@router.message(F.text.lower().in_(["помощь стройка", "помощь ск", "помощь строительная компания"]))
async def cmd_co_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(F.text.lower().regexp(r"^(стройка|ск) создать\s+(.+)$"))
async def cmd_co_create_named(message: Message):
    uid = message.from_user.id
    if get_company(uid):
        await message.answer("❌ У вас уже есть строительная компания. Напишите <b>стройка</b>.", parse_mode="HTML")
        return
    bal = get_balance(uid)
    if bal < REGISTRATION_COST:
        await message.answer(f"❌ Нужно <b>{fmt(REGISTRATION_COST)}$</b>, у вас <b>{fmt(bal)}$</b>.", parse_mode="HTML")
        return
    parts = message.text.strip().split(None, 2)
    name  = parts[2].strip()[:32] if len(parts) >= 3 else "Моя компания"
    if len(name) < 2:
        name = "Моя компания"
    update_balance(uid, bal - REGISTRATION_COST)
    c = create_company(uid, name)
    await message.answer(
        f"✅ <b>Строительная компания основана!</b>\n\n"
        f"🏗 Название: <b>{name}</b>\n"
        f"💸 Списано: {fmt(REGISTRATION_COST)}$\n"
        f"🏦 Стартовый баланс: {fmt(STARTING_BALANCE)}$",
        parse_mode="HTML", reply_markup=main_kb()
    )


@router.message(F.text.lower().in_(["стройка", "/стройка", "ск", "/ск", "строительная компания", "🏗 стройка"]))
async def cmd_co_main(message: Message):
    uid = message.from_user.id
    c   = get_company(uid)
    if not c:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🏗 Основать компанию — {fmt(REGISTRATION_COST)}$", callback_data="co_create")],
        ])
        await message.answer(
            f"🏗 <b>Строительная компания</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Основайте строительную компанию, возводите объекты, набирайте заказчиков и зарабатывайте на строительных контрактах!\n\n"
            f"<b>Как начать:</b>\n"
            f"1) Создай объект (жилой дом, ТЦ...)\n"
            f"2) В объекте добавь виды строительных работ\n"
            f"3) Запусти 🚀 Маркетинг для привлечения заказчиков\n"
            f"4) Установи 📢 Маркетинг-отдел и принимай контракты\n\n"
            f"💰 Стоимость основания: <b>{fmt(REGISTRATION_COST)}$</b>\n"
            f"🏦 Стартовый баланс: <b>{fmt(STARTING_BALANCE)}$</b>\n\n"
            f"<i>Также: ск создать [Название]</i>\n"
            f"ℹ️ Помощь: <code>помощь стройка</code>",
            parse_mode="HTML", reply_markup=kb
        )
        return
    flush_passive(c)
    if check_bankruptcy_state(c) == "bankrupt":
        await _do_bankruptcy(message, uid)
        return
    save_user_data()
    await message.answer(main_text(c), parse_mode="HTML", reply_markup=main_kb())


@router.callback_query(F.data == "co_main")
async def cb_co_main(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    flush_passive(c)
    if check_bankruptcy_state(c) == "bankrupt":
        await _do_bankruptcy(callback.message, uid)
        await callback.answer()
        return
    new_ach = check_achievements(c)
    save_user_data()
    try:
        await callback.message.edit_text(main_text(c), parse_mode="HTML", reply_markup=main_kb())
    except Exception:
        pass
    if new_ach:
        await callback.message.answer(
            "🏅 <b>Новые достижения!</b>\n" + "\n".join(f"• {a}" for a in new_ach),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "co_create")
async def cb_co_create(callback: CallbackQuery):
    uid = callback.from_user.id
    if get_company(uid):
        await callback.answer("Компания уже есть!", show_alert=True)
        return
    bal = get_balance(uid)
    if bal < REGISTRATION_COST:
        await callback.answer(f"❌ Нужно {fmt(REGISTRATION_COST)}$, у вас {fmt(bal)}$", show_alert=True)
        return
    update_balance(uid, bal - REGISTRATION_COST)
    create_company(uid)
    await callback.message.edit_text(
        f"✅ <b>Строительная компания основана!</b>\n\n"
        f"💸 Списано: {fmt(REGISTRATION_COST)}$\n"
        f"🏦 Баланс: {fmt(STARTING_BALANCE)}$\n\n"
        f"<i>Совет: создайте объект в разделе 🏗 Объекты</i>",
        parse_mode="HTML", reply_markup=main_kb()
    )
    await callback.answer()


async def _do_bankruptcy(message, uid):
    user = get_user(uid)
    user.pop("company", None)
    save_user_data()
    await message.answer(
        "⛔ <b>Банкротство!</b>\n"
        "Ваша строительная компания ликвидирована из-за долга.\n"
        "Вы можете основать новую командой <b>стройка</b>.",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════
#  ФИНАНСЫ
# ══════════════════════════════════════════════════════════════

class CoFinance(StatesGroup):
    deposit  = State()
    withdraw = State()


@router.callback_query(F.data == "co_balance")
async def cb_co_balance(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    rate = get_commission_rate(uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Пополнить", callback_data="co_dep")],
        [InlineKeyboardButton(text="💸 Снять",     callback_data="co_wit")],
        [InlineKeyboardButton(text="💸 Снять всё", callback_data="co_wit_all")],
        [InlineKeyboardButton(text="◀️ Назад",     callback_data="co_main")],
    ])
    await callback.message.edit_text(
        f"💰 <b>Финансы</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 Баланс компании: <b>{fmt(c['balance'])}$</b>\n"
        f"👤 Ваш баланс: <b>{fmt(get_balance(uid))}$</b>\n\n"
        f"📊 Комиссия: <b>{int(rate*100)}%</b> (от суммы &gt; {COMMISSION_MIN}$)\n\n"
        f"<i>Также: стройка пополнить [сумма]</i>\n"
        f"<i>стройка снять [сумма|все]</i>",
        parse_mode="HTML", reply_markup=kb
    )
    await callback.answer()


def _apply_deposit(uid, c, amount):
    rate = get_commission_rate(uid)
    commission = int(amount * rate) if amount > COMMISSION_MIN else 0
    total = amount + commission
    bal = get_balance(uid)
    if bal < total:
        return None, commission, bal
    update_balance(uid, bal - total)
    c["balance"] += amount
    save_user_data()
    return total, commission, bal


def _apply_withdraw(uid, c, amount):
    if amount > c.get("balance", 0):
        return False, 0, 0
    rate = get_commission_rate(uid)
    commission = int(amount * rate) if amount > COMMISSION_MIN else 0
    net = amount - commission
    c["balance"] -= amount
    update_balance(uid, get_balance(uid) + net)
    save_user_data()
    return True, commission, net


@router.callback_query(F.data == "co_dep")
async def cb_co_dep(callback: CallbackQuery, state: FSMContext):
    if not get_company(callback.from_user.id):
        await callback.answer("Нет компании.", show_alert=True)
        return
    await state.set_state(CoFinance.deposit)
    await callback.message.edit_text(
        f"💵 <b>Пополнение счёта компании</b>\n\n"
        f"Ваш баланс: <b>{fmt(get_balance(callback.from_user.id))}$</b>\n\n"
        f"Введите сумму:",
        parse_mode="HTML", reply_markup=back_kb("co_balance")
    )
    await callback.answer()


@router.message(CoFinance.deposit)
async def msg_co_dep(message: Message, state: FSMContext):
    uid = message.from_user.id
    c   = get_company(uid)
    if not c:
        await state.clear()
        return
    try:
        from utils import parse_k
        amount = int(parse_k(message.text.strip()))
        assert amount > 0
    except Exception:
        await message.answer("❌ Некорректная сумма.")
        return
    total, comm, bal = _apply_deposit(uid, c, amount)
    if total is None:
        await message.answer(f"❌ Нужно {fmt(amount + comm)}$ (вкл. комиссию {fmt(comm)}$), у вас {fmt(bal)}$")
        return
    await state.clear()
    await message.answer(
        f"✅ Зачислено <b>{fmt(amount)}$</b>, комиссия <b>{fmt(comm)}$</b>.\n"
        f"Баланс компании: <b>{fmt(c['balance'])}$</b>",
        parse_mode="HTML", reply_markup=main_kb()
    )


@router.callback_query(F.data == "co_wit")
async def cb_co_wit(callback: CallbackQuery, state: FSMContext):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    rate = get_commission_rate(callback.from_user.id)
    await state.set_state(CoFinance.withdraw)
    await callback.message.edit_text(
        f"💸 <b>Снятие со счёта компании</b>\n\n"
        f"Баланс компании: <b>{fmt(c['balance'])}$</b>\n"
        f"Комиссия: <b>{int(rate*100)}%</b>\n\n"
        f"Введите сумму:",
        parse_mode="HTML", reply_markup=back_kb("co_balance")
    )
    await callback.answer()


@router.message(CoFinance.withdraw)
async def msg_co_wit(message: Message, state: FSMContext):
    uid = message.from_user.id
    c   = get_company(uid)
    if not c:
        await state.clear()
        return
    try:
        from utils import parse_k
        amount = int(parse_k(message.text.strip()))
        assert amount > 0
    except Exception:
        await message.answer("❌ Некорректная сумма.")
        return
    ok, comm, net = _apply_withdraw(uid, c, amount)
    if not ok:
        await message.answer(f"❌ На счёте только {fmt(c.get('balance',0))}$")
        return
    await state.clear()
    await message.answer(
        f"✅ Снято <b>{fmt(amount)}$</b>, комиссия <b>{fmt(comm)}$</b>, получено <b>{fmt(net)}$</b>.",
        parse_mode="HTML", reply_markup=main_kb()
    )


@router.callback_query(F.data == "co_wit_all")
async def cb_co_wit_all(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    bal = c.get("balance", 0)
    if bal <= 0:
        await callback.answer("На счёте нет средств.", show_alert=True)
        return
    ok, comm, net = _apply_withdraw(uid, c, bal)
    await callback.message.edit_text(
        f"✅ <b>Снято всё!</b>\n\n"
        f"Было: <b>{fmt(bal)}$</b>\n"
        f"Комиссия: <b>{fmt(comm)}$</b>\n"
        f"Получено: <b>{fmt(net)}$</b>",
        parse_mode="HTML", reply_markup=back_kb("co_balance")
    )
    await callback.answer()


# Текстовые команды финансов
@router.message(F.text.lower().regexp(r"^(стройка|ск) пополнить\s+(.+)$"))
async def cmd_dep_text(message: Message):
    uid = message.from_user.id
    c   = get_company(uid)
    if not c:
        await message.answer("❌ У вас нет строительной компании. Напишите <b>стройка</b>.", parse_mode="HTML")
        return
    parts = message.text.strip().split(None, 2)
    try:
        from utils import parse_k
        amount = int(parse_k(parts[2]))
        assert amount > 0
    except Exception:
        await message.answer("❌ Некорректная сумма.")
        return
    total, comm, bal = _apply_deposit(uid, c, amount)
    if total is None:
        await message.answer(f"❌ Нужно {fmt(amount + comm)}$ (вкл. комиссию {fmt(comm)}$), у вас {fmt(bal)}$")
        return
    await message.answer(
        f"✅ Пополнено <b>{fmt(amount)}$</b> (комиссия {fmt(comm)}$). Баланс: <b>{fmt(c['balance'])}$</b>",
        parse_mode="HTML"
    )


@router.message(F.text.lower().in_(["стройка снять все", "стройка снять всё", "ск снять все", "ск снять всё"]))
async def cmd_wit_all_text(message: Message):
    uid = message.from_user.id
    c   = get_company(uid)
    if not c:
        await message.answer("❌ У вас нет строительной компании.")
        return
    bal = c.get("balance", 0)
    if bal <= 0:
        await message.answer("❌ На счёте нет средств.")
        return
    ok, comm, net = _apply_withdraw(uid, c, bal)
    await message.answer(
        f"✅ Снято <b>{fmt(bal)}$</b>, комиссия <b>{fmt(comm)}$</b>, получено <b>{fmt(net)}$</b>.",
        parse_mode="HTML"
    )


@router.message(F.text.lower().regexp(r"^(стройка|ск|су) (снять вб|пополнить вб)\s+(.+)$"))
async def cmd_vb_shortcut(message: Message):
    """Алиасы: ск/су снять вб [сумма] / ск/су пополнить вб [сумма]"""
    from utils import parse_k
    uid   = message.from_user.id
    c     = get_company(uid)
    if not c:
        await message.answer("❌ У вас нет строительной компании. Напишите <b>стройка</b>.", parse_mode="HTML")
        return
    # "ск пополнить вб 10000" → split на 4 части → parts[3] = "10000"
    parts = message.text.strip().split(None, 3)
    action     = parts[1].lower() if len(parts) > 1 else ""
    amount_raw = parts[3].strip() if len(parts) > 3 else ""
    if not amount_raw:
        await message.answer(
            "❌ Укажите сумму.\n"
            "Пример: <code>ск пополнить вб 10000</code> / <code>су снять вб 5к</code>",
            parse_mode="HTML"
        )
        return
    try:
        amount = int(parse_k(amount_raw))
        assert amount > 0
    except Exception:
        await message.answer(
            f"❌ Некорректная сумма: <code>{amount_raw}</code>\n"
            f"Используйте число или сокращение: <code>10к</code>, <code>1.5м</code>, <code>500000</code>",
            parse_mode="HTML"
        )
        return
    if action == "пополнить":
        total, comm, bal = _apply_deposit(uid, c, amount)
        if total is None:
            await message.answer(f"❌ Нужно {fmt(amount + comm)}$ (вкл. комиссию {fmt(comm)}$), у вас {fmt(bal)}$")
            return
        await message.answer(
            f"✅ Пополнено <b>{fmt(amount)}$</b> (комиссия {fmt(comm)}$). Баланс СК: <b>{fmt(c['balance'])}$</b>",
            parse_mode="HTML"
        )
    else:
        ok, comm, net = _apply_withdraw(uid, c, amount)
        if not ok:
            await message.answer(f"❌ На счёте только {fmt(c.get('balance', 0))}$")
            return
        await message.answer(
            f"✅ Снято <b>{fmt(amount)}$</b>, комиссия <b>{fmt(comm)}$</b>, получено <b>{fmt(net)}$</b>.",
            parse_mode="HTML"
        )


@router.message(F.text.lower().regexp(r"^(стройка|ск) снять\s+(.+)$"))
async def cmd_wit_text(message: Message):
    uid = message.from_user.id
    c   = get_company(uid)
    if not c:
        await message.answer("❌ У вас нет строительной компании.")
        return
    parts = message.text.strip().split(None, 2)
    arg   = parts[2].lower() if len(parts) >= 3 else ""
    if arg in ("все", "всё", "all"):
        await cmd_wit_all_text(message)
        return
    try:
        from utils import parse_k
        amount = int(parse_k(arg))
        assert amount > 0
    except Exception:
        await message.answer("❌ Некорректная сумма.")
        return
    ok, comm, net = _apply_withdraw(uid, c, amount)
    if not ok:
        await message.answer(f"❌ На счёте только {fmt(c.get('balance',0))}$")
        return
    await message.answer(
        f"✅ Снято <b>{fmt(amount)}$</b>, комиссия <b>{fmt(comm)}$</b>, получено <b>{fmt(net)}$</b>.",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════
#  ОБЪЕКТЫ (СЕРВИСЫ)
# ══════════════════════════════════════════════════════════════

class CoObject(StatesGroup):
    choosing_type = State()
    entering_name = State()


def objects_text(c: dict) -> str:
    objs   = c.get("services", [])
    office = OFFICES[c.get("office_level", 1)]
    fw     = FRAMEWORKS[c.get("framework_level", 0)]
    lines  = []
    for i, o in enumerate(objs):
        aud   = o.get("audience", 0)
        max_a = _obj_max_audience(o, c.get("framework_level", 0))
        tech  = o.get("servers", 0)
        load  = int(_obj_load(o) * 100)
        promo = o.get("promotion_finish")
        p_str = f" 🚀{fmt_time(promo - int(time.time()))}" if promo and promo > int(time.time()) else ""
        con   = o.get("ad_contract")
        c_str = f" 📋{fmt_time(con['finish_at'] - int(time.time()))}" if con else ""
        lines.append(
            f"  {i+1}. <b>{o['name']}</b>{p_str}{c_str}\n"
            f"     👥 {fmt(aud)}/{fmt(max_a)} | 🚜 {tech} техн. | ⚡{load}%"
        )
    return (
        f"🏗 <b>Объекты</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Объектов: <b>{len(objs)}/{office['max_objects']}</b>\n"
        f"Технология: <b>{fw['name']}</b> ({fw['slots']} слотов, макс. ур. {fw['max_level']})\n\n"
        + ("\n".join(lines) if lines else "  Нет объектов")
    )


def objects_kb(c: dict) -> InlineKeyboardMarkup:
    objs   = c.get("services", [])
    office = OFFICES[c.get("office_level", 1)]
    rows   = [[InlineKeyboardButton(text=f"🏗 {o['name']}", callback_data=f"co_obj:{i}")]
               for i, o in enumerate(objs)]
    if len(objs) < office["max_objects"]:
        rows.append([InlineKeyboardButton(text="➕ Новый объект", callback_data="co_obj_new")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="co_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "co_objects")
async def cb_co_objects(callback: CallbackQuery):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(objects_text(c), parse_mode="HTML", reply_markup=objects_kb(c))
    await callback.answer()


@router.callback_query(F.data == "co_obj_new")
async def cb_obj_new(callback: CallbackQuery, state: FSMContext):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    office = OFFICES[c.get("office_level", 1)]
    if len(c.get("services", [])) >= office["max_objects"]:
        await callback.answer("❌ Достигнут лимит объектов. Улучшите штаб.", show_alert=True)
        return
    rows = [[InlineKeyboardButton(text=name, callback_data=f"co_obj_type:{key}")]
            for key, name in OBJECT_TYPES.items()]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="co_objects")])
    await state.set_state(CoObject.choosing_type)
    await callback.message.edit_text(
        "🏗 <b>Выберите тип объекта:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("co_obj_type:"))
async def cb_obj_type(callback: CallbackQuery, state: FSMContext):
    otype = callback.data.split(":")[1]
    await state.update_data(otype=otype)
    await state.set_state(CoObject.entering_name)
    await callback.message.edit_text(
        f"📝 Введите название объекта <b>{OBJECT_TYPES.get(otype,'')}</b>:",
        parse_mode="HTML", reply_markup=back_kb("co_objects")
    )
    await callback.answer()


@router.message(CoObject.entering_name)
async def msg_obj_name(message: Message, state: FSMContext):
    uid = message.from_user.id
    c   = get_company(uid)
    if not c:
        await state.clear()
        return
    name = message.text.strip()[:32]
    if len(name) < 2:
        await message.answer("❌ Слишком короткое название.")
        return
    data  = await state.get_data()
    otype = data.get("otype", "mobile")
    office = OFFICES[c.get("office_level", 1)]
    if len(c.get("services", [])) >= office["max_objects"]:
        await message.answer("❌ Достигнут лимит объектов!")
        await state.clear()
        return
    if "services" not in c:
        c["services"] = []
    c["services"].append({
        "id":               len(c["services"]) + 1,
        "type":             otype,
        "name":             name,
        "audience":         0,
        "servers":          0,
        "functions":        {},
        "promotion_finish": None,
        "ad_contract":      None,
    })
    save_user_data()
    await state.clear()
    await message.answer(
        f"✅ <b>Объект создан!</b>\n\n"
        f"{OBJECT_TYPES.get(otype,'')} <b>{name}</b>\n\n"
        f"<i>Добавьте виды строительных работ через меню объекта</i>",
        parse_mode="HTML", reply_markup=main_kb()
    )


# ─── Меню объекта ─────────────────────────────────────────────

def obj_text(c: dict, idx: int) -> str:
    o   = c["services"][idx]
    fw  = FRAMEWORKS[c.get("framework_level", 0)]
    aud = o.get("audience", 0)
    max_a = _obj_max_audience(o, c.get("framework_level", 0))
    tech  = o.get("servers", 0)
    cap   = _obj_tech_capacity(o)
    load  = int(_obj_load(o) * 100)
    eff   = int(_obj_efficiency(o) * 100)
    promo = o.get("promotion_finish")
    p_str = f"🚀 {fmt_time(promo - int(time.time()))}" if promo and promo > int(time.time()) else "—"
    con   = o.get("ad_contract")
    c_str = f"📋 {fmt(con['reward'])}$ ({fmt_time(con['finish_at'] - int(time.time()))})" if con else "—"
    funcs = o.get("functions", {})
    f_lines = "\n".join(
        f"  {FUNCTIONS[fk]['name']} ур.{flvl}"
        for fk, flvl in funcs.items() if fk in FUNCTIONS
    ) or "  Нет работ"
    return (
        f"{OBJECT_TYPES.get(o['type'],'')} <b>{o['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Заказчики: <b>{fmt(aud)}/{fmt(max_a)}</b>\n"
        f"🚜 Техника: <b>{tech}</b> (ёмкость: {fmt(cap)})\n"
        f"⚡ Загрузка: <b>{load}%</b> | Эффективность: <b>{eff}%</b>\n"
        f"🚀 Маркетинг: {p_str}\n"
        f"📋 Контракт: {c_str}\n\n"
        f"<b>Работы ({len(funcs)}/{fw['slots']}):</b>\n{f_lines}"
    )


def obj_kb(c: dict, idx: int) -> InlineKeyboardMarkup:
    o      = c["services"][idx]
    office = OFFICES[c.get("office_level", 1)]
    fw     = FRAMEWORKS[c.get("framework_level", 0)]
    funcs  = o.get("functions", {})
    promo  = o.get("promotion_finish")
    con    = o.get("ad_contract")
    rows   = []
    if len(funcs) < fw["slots"]:
        rows.append([InlineKeyboardButton(text="➕ Добавить работу",   callback_data=f"co_work_add:{idx}")])
    if funcs:
        rows.append([InlineKeyboardButton(text="⬆️ Улучшить работу",  callback_data=f"co_work_upg:{idx}")])
    if _total_tech(c) < office["max_tech"]:
        rows.append([InlineKeyboardButton(text=f"🚜 Купить технику — {fmt(TECH_COST)}$", callback_data=f"co_obj_tech:{idx}")])
    if not (promo and promo > int(time.time())):
        rows.append([InlineKeyboardButton(text=f"🚀 Маркетинг — {fmt(PROMO_COST)}$", callback_data=f"co_promo:{idx}")])
    else:
        rows.append([InlineKeyboardButton(text="⏳ Маркетинг идёт...", callback_data="co_noop")])
    if "ads" in funcs:
        if con:
            left = con["finish_at"] - int(time.time())
            if left <= 0:
                rows.append([InlineKeyboardButton(text="✅ Сдать объект (получить оплату)", callback_data=f"co_collect:{idx}")])
            else:
                rows.append([InlineKeyboardButton(text=f"📋 Контракт: {fmt_time(left)}", callback_data="co_noop")])
        else:
            rows.append([InlineKeyboardButton(text="📋 Взять строительный контракт", callback_data=f"co_contract:{idx}")])
    rows.append([InlineKeyboardButton(text="🗑 Снести объект",         callback_data=f"co_obj_del:{idx}")])
    rows.append([InlineKeyboardButton(text="◀️ К объектам",            callback_data="co_objects")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("co_obj:"))
async def cb_co_obj(callback: CallbackQuery):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    idx = int(callback.data.split(":")[1])
    if idx >= len(c.get("services", [])):
        await callback.answer("Объект не найден.", show_alert=True)
        return
    await callback.message.edit_text(obj_text(c, idx), parse_mode="HTML", reply_markup=obj_kb(c, idx))
    await callback.answer()


@router.callback_query(F.data == "co_noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("co_obj_tech:"))
async def cb_obj_tech(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    idx    = int(callback.data.split(":")[1])
    office = OFFICES[c.get("office_level", 1)]
    if _total_tech(c) >= office["max_tech"]:
        await callback.answer("❌ Лимит техники в штабе исчерпан! Улучшите штаб.", show_alert=True)
        return
    if c.get("balance", 0) < TECH_COST:
        await callback.answer(f"❌ Нужно {fmt(TECH_COST)}$", show_alert=True)
        return
    c["balance"] -= TECH_COST
    c["services"][idx]["servers"] = c["services"][idx].get("servers", 0) + 1
    save_user_data()
    await callback.answer("✅ Техника закуплена!", show_alert=False)
    await callback.message.edit_text(obj_text(c, idx), parse_mode="HTML", reply_markup=obj_kb(c, idx))


@router.callback_query(F.data.startswith("co_promo:"))
async def cb_promo(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    idx = int(callback.data.split(":")[1])
    obj = c["services"][idx]
    if obj.get("promotion_finish") and obj["promotion_finish"] > int(time.time()):
        await callback.answer("Маркетинг уже идёт!", show_alert=True)
        return
    if _obj_max_audience(obj, c.get("framework_level", 0)) <= 0:
        await callback.answer("❌ Сначала добавьте виды работ для набора заказчиков!", show_alert=True)
        return
    if c.get("balance", 0) < PROMO_COST:
        await callback.answer(f"❌ Нужно {fmt(PROMO_COST)}$", show_alert=True)
        return
    c["balance"] -= PROMO_COST
    obj["promotion_finish"] = int(time.time()) + PROMO_DURATION
    save_user_data()
    await callback.answer("🚀 Маркетинг запущен! Завершится через 5 мин.", show_alert=True)
    await callback.message.edit_text(obj_text(c, idx), parse_mode="HTML", reply_markup=obj_kb(c, idx))


@router.callback_query(F.data.startswith("co_obj_del:"))
async def cb_obj_del(callback: CallbackQuery):
    uid  = callback.from_user.id
    c    = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    idx  = int(callback.data.split(":")[1])
    name = c["services"][idx]["name"]
    c["services"].pop(idx)
    save_user_data()
    await callback.answer(f"🗑 Объект '{name}' снесён.", show_alert=True)
    await callback.message.edit_text(objects_text(c), parse_mode="HTML", reply_markup=objects_kb(c))


# ─── Контракты ────────────────────────────────────────────────

def contract_kb(c: dict, idx: int) -> InlineKeyboardMarkup:
    obj     = c["services"][idx]
    ads_lvl = obj.get("functions", {}).get("ads", 0)
    rows    = [
        [InlineKeyboardButton(
            text=f"📋 {ct['name']} ({fmt(ct['min'])}–{fmt(ct['max'])}$, {ct['dur']//3600}ч)",
            callback_data=f"co_con_take:{idx}:{tier}"
        )]
        for tier, ct in CONTRACTS.items() if ads_lvl >= ct["ads_level"]
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"co_obj:{idx}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("co_contract:"))
async def cb_contract(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    idx = int(callback.data.split(":")[1])
    obj = c["services"][idx]
    if obj.get("ad_contract"):
        await callback.answer("Контракт уже активен!", show_alert=True)
        return
    await callback.message.edit_text(
        f"📋 <b>Строительные контракты</b>\n\n"
        f"{OBJECT_TYPES.get(obj['type'],'')} <b>{obj['name']}</b>\n\nВыберите тип контракта:",
        parse_mode="HTML", reply_markup=contract_kb(c, idx)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("co_con_take:"))
async def cb_con_take(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    _, idx_s, tier_s = callback.data.split(":")
    idx  = int(idx_s)
    ct   = CONTRACTS.get(int(tier_s))
    obj  = c["services"][idx]
    reward = random.randint(ct["min"], ct["max"])
    obj["ad_contract"] = {"reward": reward, "dur": ct["dur"], "finish_at": int(time.time()) + ct["dur"]}
    save_user_data()
    await callback.answer(f"✅ Контракт подписан! Ожидаемая оплата: {fmt(reward)}$", show_alert=True)
    await callback.message.edit_text(obj_text(c, idx), parse_mode="HTML", reply_markup=obj_kb(c, idx))


@router.callback_query(F.data.startswith("co_collect:"))
async def cb_collect(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    idx = int(callback.data.split(":")[1])
    obj = c["services"][idx]
    con = obj.get("ad_contract")
    if not con:
        await callback.answer("Нет контракта.", show_alert=True)
        return
    if int(time.time()) < con["finish_at"]:
        await callback.answer(f"⏳ Объект ещё не сдан! Осталось: {fmt_time(con['finish_at'] - int(time.time()))}", show_alert=True)
        return
    reward   = con["reward"]
    eff      = _obj_efficiency(obj)
    max_a    = _obj_max_audience(obj, c.get("framework_level", 0))
    aud_r    = min(1.0, obj.get("audience", 0) / max(1, max_a)) if max_a > 0 else 0
    res_b    = 1 + RESEARCH[c.get("research_level", 0)]["income_bonus"] / 100
    final    = int(reward * eff * aud_r * res_b)
    c["balance"]       = c.get("balance", 0) + final
    c["contracts_done"] = c.get("contracts_done", 0) + 1
    obj["ad_contract"]  = None
    new_ach = check_achievements(c)
    save_user_data()
    text = (
        f"✅ <b>Объект сдан!</b>\n\n"
        f"Сумма контракта: {fmt(reward)}$\n"
        f"Эффективность техники: {int(eff*100)}%\n"
        f"Заполненность заказчиками: {int(aud_r*100)}%\n"
        f"Получено: <b>{fmt(final)}$</b>\n"
        f"Баланс компании: <b>{fmt(c['balance'])}$</b>"
    )
    if new_ach:
        text += "\n\n🏅 <b>Новые достижения:</b>\n" + "\n".join(f"• {a}" for a in new_ach)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("co_objects"))
    await callback.answer()


# ─── Работы (функции объекта) ─────────────────────────────────

def work_add_kb(c: dict, idx: int) -> InlineKeyboardMarkup:
    obj     = c["services"][idx]
    funcs   = obj.get("functions", {})
    res_lvl = c.get("research_level", 0)
    rows    = []
    for fkey, fd in FUNCTIONS.items():
        if fkey in funcs:
            continue
        if fd["req_research"] > res_lvl:
            rows.append([InlineKeyboardButton(text=f"🔒 {fd['name']} (инновации: {fd['req_research']})", callback_data="co_noop")])
        else:
            rows.append([InlineKeyboardButton(text=f"➕ {fd['name']} — {fmt(fd['cost_money'])}$", callback_data=f"co_work_inst:{idx}:{fkey}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"co_obj:{idx}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("co_work_add:"))
async def cb_work_add(callback: CallbackQuery):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    idx = int(callback.data.split(":")[1])
    res = c.get("resources", {})
    await callback.message.edit_text(
        f"➕ <b>Добавить вид работ</b>\n\n"
        f"Ресурсы: 🔬{fmt(res.get('research',0))} 💻{fmt(res.get('dev',0))} 🎨{fmt(res.get('design',0))}\n"
        f"Компоненты: 🧱{fmt(res.get('brick',0))} 🧩{fmt(res.get('module',0))} 🌐{fmt(res.get('network',0))}\n"
        f"Баланс компании: <b>{fmt(c['balance'])}$</b>\n\n"
        f"Выберите работу:",
        parse_mode="HTML", reply_markup=work_add_kb(c, idx)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("co_work_inst:"))
async def cb_work_inst(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    _, idx_s, fkey = callback.data.split(":", 2)
    idx  = int(idx_s)
    fd   = FUNCTIONS.get(fkey)
    if not fd:
        await callback.answer("Неверный вид работ.", show_alert=True)
        return
    obj   = c["services"][idx]
    fw    = FRAMEWORKS[c.get("framework_level", 0)]
    funcs = obj.get("functions", {})
    if len(funcs) >= fw["slots"]:
        await callback.answer("❌ Нет слотов! Улучшите технологию строительства.", show_alert=True)
        return
    if fkey in funcs:
        await callback.answer("Уже добавлено!", show_alert=True)
        return
    if c.get("balance", 0) < fd["cost_money"]:
        await callback.answer(f"❌ Нужно {fmt(fd['cost_money'])}$", show_alert=True)
        return
    res = c.get("resources", {})
    RES_NAMES = {"research": "🔬 Чертежи", "dev": "💻 Труд", "design": "🎨 Дизайн",
                 "brick": "🧱 Кирпич", "module": "🧩 Компоненты", "network": "🌐 Коммуникации"}
    for rk, rv in fd["cost_res"].items():
        if res.get(rk, 0) < rv:
            await callback.answer(f"❌ Не хватает: {RES_NAMES.get(rk,rk)} (нужно {rv}, есть {res.get(rk,0)})", show_alert=True)
            return
    c["balance"] -= fd["cost_money"]
    for rk, rv in fd["cost_res"].items():
        res[rk] = res.get(rk, 0) - rv
    funcs[fkey] = 1
    obj["functions"] = funcs
    save_user_data()
    await callback.answer(f"✅ {fd['name']} добавлено!", show_alert=True)
    await callback.message.edit_text(obj_text(c, idx), parse_mode="HTML", reply_markup=obj_kb(c, idx))


def work_upg_kb(c: dict, idx: int) -> InlineKeyboardMarkup:
    obj   = c["services"][idx]
    funcs = obj.get("functions", {})
    fw    = FRAMEWORKS[c.get("framework_level", 0)]
    rows  = []
    for fkey, flvl in funcs.items():
        fd = FUNCTIONS.get(fkey)
        if not fd:
            continue
        if flvl >= fw["max_level"]:
            rows.append([InlineKeyboardButton(text=f"🔒 {fd['name']} (макс. ур.{fw['max_level']})", callback_data="co_noop")])
        else:
            cost_m = int(fd["cost_money"] * 0.7 * flvl)
            rows.append([InlineKeyboardButton(
                text=f"⬆️ {fd['name']} ур.{flvl}→{flvl+1} — {fmt(cost_m)}$",
                callback_data=f"co_work_up:{idx}:{fkey}"
            )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"co_obj:{idx}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("co_work_upg:"))
async def cb_work_upg(callback: CallbackQuery):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    idx = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "⬆️ <b>Улучшить вид работ</b>\n\nВыберите:",
        parse_mode="HTML", reply_markup=work_upg_kb(c, idx)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("co_work_up:"))
async def cb_work_up(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    _, idx_s, fkey = callback.data.split(":", 2)
    idx   = int(idx_s)
    fd    = FUNCTIONS.get(fkey)
    obj   = c["services"][idx]
    funcs = obj.get("functions", {})
    flvl  = funcs.get(fkey, 0)
    fw    = FRAMEWORKS[c.get("framework_level", 0)]
    if flvl >= fw["max_level"]:
        await callback.answer("Максимальный уровень!", show_alert=True)
        return
    cost_m = int(fd["cost_money"] * 0.7 * flvl)
    cost_r = {rk: int(rv * 0.5 * flvl) for rk, rv in fd["cost_res"].items()}
    if c.get("balance", 0) < cost_m:
        await callback.answer(f"❌ Нужно {fmt(cost_m)}$", show_alert=True)
        return
    res = c.get("resources", {})
    for rk, rv in cost_r.items():
        if res.get(rk, 0) < rv:
            await callback.answer(f"❌ Не хватает ресурса: {rk}", show_alert=True)
            return
    c["balance"] -= cost_m
    for rk, rv in cost_r.items():
        res[rk] = res.get(rk, 0) - rv
    funcs[fkey] = flvl + 1
    save_user_data()
    await callback.answer(f"✅ {fd['name']} улучшено до ур.{flvl+1}!", show_alert=True)
    await callback.message.edit_text(obj_text(c, idx), parse_mode="HTML", reply_markup=obj_kb(c, idx))


# ══════════════════════════════════════════════════════════════
#  ПЕРСОНАЛ
# ══════════════════════════════════════════════════════════════

def emp_text(c: dict) -> str:
    office    = OFFICES[c.get("office_level", 1)]
    max_places = office["max_places"]
    emp = c.get("employees", {})
    cnt = _total_emp(c)
    lines = []
    for key, e in EMPLOYEES.items():
        n   = emp.get(key, 0)
        gen = " ".join(f"{EMOJI_MAP.get(rk,'')}{rate}/ч" for rk, rate in e["gen"].items())
        lines.append(
            f"  {e['name']}: <b>{n}</b> | найм {fmt(e['hire'])}$ | зарп. {fmt(e['salary_hour'])}$/ч\n"
            f"    Генерация: {gen}"
        )
    return (
        f"👷 <b>Персонал</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Занято мест: <b>{cnt}/{max_places}</b>\n\n"
        + "\n".join(lines) +
        f"\n\n💰 Баланс: <b>{fmt(c.get('balance',0))}$</b>"
    )


EMOJI_MAP = {"research": "📐", "dev": "🔨", "design": "🎨",
             "brick": "🧱", "module": "🪵", "network": "⚡"}


def emp_kb(c: dict) -> InlineKeyboardMarkup:
    office     = OFFICES[c.get("office_level", 1)]
    max_places = office["max_places"]
    cnt        = _total_emp(c)
    emp        = c.get("employees", {})
    rows       = []
    for key, e in EMPLOYEES.items():
        n        = emp.get(key, 0)
        has_bal  = c.get("balance", 0) >= e["hire"]
        has_room = cnt < max_places
        can      = has_bal and has_room
        rows.append([
            InlineKeyboardButton(text=f"➕ {e['name']} ({n})", callback_data=f"co_hire:{key}" if can else "co_hire_no"),
            InlineKeyboardButton(text="➖ Уволить",            callback_data=f"co_fire:{key}"),
        ])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="co_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "co_employees")
async def cb_emp(callback: CallbackQuery):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(emp_text(c), parse_mode="HTML", reply_markup=emp_kb(c))
    await callback.answer()


@router.callback_query(F.data.startswith("co_hire:"))
async def cb_hire(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    key        = callback.data.split(":")[1]
    e          = EMPLOYEES.get(key)
    office     = OFFICES[c.get("office_level", 1)]
    max_places = office["max_places"]
    if _total_emp(c) >= max_places:
        await callback.answer(f"❌ Все места заняты! Максимум {max_places} сотрудников для этого штаба.", show_alert=True)
        return
    if c.get("balance", 0) < e["hire"]:
        await callback.answer(f"❌ Нужно {fmt(e['hire'])}$", show_alert=True)
        return
    c["balance"] -= e["hire"]
    c["employees"][key] = c["employees"].get(key, 0) + 1
    new_ach = check_achievements(c)
    save_user_data()
    await callback.answer(f"✅ {e['name']} нанят!", show_alert=False)
    await callback.message.edit_text(emp_text(c), parse_mode="HTML", reply_markup=emp_kb(c))
    if new_ach:
        await callback.message.answer("🏅 <b>Новые достижения!</b>\n" + "\n".join(f"• {a}" for a in new_ach), parse_mode="HTML")


@router.callback_query(F.data == "co_hire_no")
async def cb_hire_no(callback: CallbackQuery):
    await callback.answer("❌ Недостаточно средств на счёте компании.", show_alert=True)


@router.callback_query(F.data.startswith("co_fire:"))
async def cb_fire(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    key = callback.data.split(":")[1]
    e   = EMPLOYEES.get(key)
    cnt = c["employees"].get(key, 0)
    if cnt <= 0:
        await callback.answer("❌ Нет таких сотрудников.", show_alert=True)
        return
    c["employees"][key] = cnt - 1
    save_user_data()
    await callback.answer(f"👋 {e['name']} уволен.", show_alert=False)
    await callback.message.edit_text(emp_text(c), parse_mode="HTML", reply_markup=emp_kb(c))


# ══════════════════════════════════════════════════════════════
#  ШТАБ
# ══════════════════════════════════════════════════════════════

def office_text(c: dict) -> str:
    lvl    = c.get("office_level", 1)
    office = OFFICES[lvl]
    cnt    = _total_emp(c)
    no     = OFFICES.get(lvl + 1)
    nxt    = ""
    if no:
        move = no["rent_day"] * 2
        nxt  = (
            f"\n\n<b>Следующий штаб:</b> {no['name']}\n"
            f"  🪑 Мест: {no['max_places']}\n"
            f"  🚜 Техники: {no['max_tech']}\n"
            f"  🏗 Объектов: {no['max_objects']}\n"
            f"  🏷️ Аренда: {fmt(no['rent_day'])}$/сут\n"
            f"  💰 Переезд: {fmt(move)}$"
        )
    return (
        f"🏢 <b>Штаб</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Штаб: <b>{office['name']}</b> (ур. {lvl}/{MAX_OFFICE})\n"
        f"🪑 Рабочих мест: <b>{cnt}/{office['max_places']}</b>\n"
        f"🚜 Техники в штабе: <b>{_total_tech(c)}/{office['max_tech']}</b>\n"
        f"🏗 Объектов: <b>{len(c.get('services',[]))}/{office['max_objects']}</b>\n"
        f"🏷️ Аренда: <b>{fmt(office['rent_day'])}$/сут</b>"
        f"{nxt}"
        f"\n\n💰 Баланс: <b>{fmt(c.get('balance',0))}$</b>"
    )


def office_kb(c: dict) -> InlineKeyboardMarkup:
    lvl    = c.get("office_level", 1)
    rows   = []
    if lvl < MAX_OFFICE:
        no   = OFFICES[lvl + 1]
        move = no["rent_day"] * 2
        can  = c.get("balance", 0) >= move
        rows.append([InlineKeyboardButton(
            text=f"🚚 Переехать в {no['name']} — {fmt(move)}$",
            callback_data="co_move_office" if can else "co_noop"
        )])
    else:
        rows.append([InlineKeyboardButton(text="⭐ Максимальный штаб", callback_data="co_noop")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="co_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "co_office")
async def cb_office(callback: CallbackQuery):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(office_text(c), parse_mode="HTML", reply_markup=office_kb(c))
    await callback.answer()


@router.callback_query(F.data == "co_buy_wp")
async def cb_buy_wp(callback: CallbackQuery):
    await callback.answer("ℹ️ Рабочие места больше не нужно покупать — они даются автоматически по лимиту штаба.", show_alert=True)


@router.callback_query(F.data == "co_move_office")
async def cb_move_office(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    lvl = c.get("office_level", 1)
    if lvl >= MAX_OFFICE:
        await callback.answer("Максимальный штаб!", show_alert=True)
        return
    no   = OFFICES[lvl + 1]
    move = no["rent_day"] * 2
    if c.get("balance", 0) < move:
        await callback.answer(f"❌ Нужно {fmt(move)}$", show_alert=True)
        return
    c["balance"]     -= move
    c["office_level"] = lvl + 1
    new_ach = check_achievements(c)
    save_user_data()
    await callback.answer(f"✅ Переехали в {no['name']}!", show_alert=True)
    await callback.message.edit_text(office_text(c), parse_mode="HTML", reply_markup=office_kb(c))
    if new_ach:
        await callback.message.answer("🏅 <b>Новые достижения!</b>\n" + "\n".join(f"• {a}" for a in new_ach), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#  ТЕХНОЛОГИИ СТРОИТЕЛЬСТВА (ФРЕЙМВОРК)
# ══════════════════════════════════════════════════════════════

def fw_text(c: dict) -> str:
    lvl = c.get("framework_level", 0)
    fw  = FRAMEWORKS[lvl]
    nfw = FRAMEWORKS.get(lvl + 1)
    nxt = ""
    if nfw:
        nxt = (
            f"\n\n<b>Следующая технология:</b> {nfw['name']}\n"
            f"  📦 Слотов работ: {nfw['slots']}\n"
            f"  ⬆️ Макс. ур. работ: {nfw['max_level']}\n"
            f"  💰 Стоимость: {fmt(nfw['cost'])}$"
        )
    return (
        f"⚙️ <b>Строительные технологии</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Текущая: <b>{fw['name']}</b> (ур. {lvl}/{MAX_FRAMEWORK})\n"
        f"📦 Слотов видов работ: <b>{fw['slots']}</b>\n"
        f"⬆️ Макс. уровень работ: <b>{fw['max_level']}</b>"
        f"{nxt}"
        f"\n\n💰 Баланс: <b>{fmt(c.get('balance',0))}$</b>"
    )


def fw_kb(c: dict) -> InlineKeyboardMarkup:
    lvl  = c.get("framework_level", 0)
    rows = []
    if lvl < MAX_FRAMEWORK:
        nfw = FRAMEWORKS[lvl + 1]
        can = c.get("balance", 0) >= nfw["cost"]
        rows.append([InlineKeyboardButton(
            text=f"⬆️ Освоить {nfw['name']} — {fmt(nfw['cost'])}$",
            callback_data="co_buy_fw" if can else "co_noop"
        )])
    else:
        rows.append([InlineKeyboardButton(text="⭐ Макс. технология", callback_data="co_noop")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="co_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "co_framework")
async def cb_fw(callback: CallbackQuery):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(fw_text(c), parse_mode="HTML", reply_markup=fw_kb(c))
    await callback.answer()


@router.callback_query(F.data == "co_buy_fw")
async def cb_buy_fw(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    lvl = c.get("framework_level", 0)
    if lvl >= MAX_FRAMEWORK:
        await callback.answer("Максимальная технология!", show_alert=True)
        return
    nfw = FRAMEWORKS[lvl + 1]
    if c.get("balance", 0) < nfw["cost"]:
        await callback.answer(f"❌ Нужно {fmt(nfw['cost'])}$", show_alert=True)
        return
    c["balance"]         -= nfw["cost"]
    c["framework_level"]  = lvl + 1
    new_ach = check_achievements(c)
    save_user_data()
    await callback.answer(f"✅ Технология {nfw['name']} освоена!", show_alert=True)
    await callback.message.edit_text(fw_text(c), parse_mode="HTML", reply_markup=fw_kb(c))
    if new_ach:
        await callback.message.answer("🏅 <b>Новые достижения!</b>\n" + "\n".join(f"• {a}" for a in new_ach), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#  ИННОВАЦИИ (ИССЛЕДОВАНИЯ)
# ══════════════════════════════════════════════════════════════

def res_text(c: dict) -> str:
    lvl  = c.get("research_level", 0)
    r    = RESEARCH[lvl]
    nr   = RESEARCH.get(lvl + 1)
    avail = [fd["name"] for fk, fd in FUNCTIONS.items() if fd["req_research"] <= lvl]
    locked = [fd["name"] for fk, fd in FUNCTIONS.items() if fd["req_research"] == lvl + 1] if nr else []
    nxt = ""
    if nr:
        nxt = f"\n\n<b>Следующий уровень:</b> {nr['name']}\n  💰 Стоимость: {fmt(nr['cost'])}$"
        if nr["promo_bonus"]:  nxt += f"\n  🚀 Маркетинг: +{nr['promo_bonus']}%"
        if nr["income_bonus"]: nxt += f"\n  💰 Доход: +{nr['income_bonus']}%"
        if nr["res_bonus"]:    nxt += f"\n  🔬 Генерация: +{nr['res_bonus']}%"
        if locked:             nxt += "\n  🔓 Открывает: " + ", ".join(locked)
    promo_b = sum(RESEARCH[i]["promo_bonus"] for i in range(1, lvl + 1))
    return (
        f"💡 <b>Инновации</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Уровень: <b>{lvl}/{MAX_RESEARCH}</b> — {r['name']}\n"
        f"🚀 Бонус маркетинга: <b>+{promo_b}%</b>\n"
        f"💰 Бонус дохода: <b>+{r['income_bonus']}%</b>\n"
        f"🔬 Бонус генерации: <b>+{r['res_bonus']}%</b>\n\n"
        f"<b>Доступные виды работ:</b>\n" + "\n".join(f"  ✅ {n}" for n in avail)
        + nxt
        + f"\n\n💰 Баланс: <b>{fmt(c.get('balance',0))}$</b>"
    )


def res_kb(c: dict) -> InlineKeyboardMarkup:
    lvl  = c.get("research_level", 0)
    rows = []
    if lvl < MAX_RESEARCH:
        nr  = RESEARCH[lvl + 1]
        can = c.get("balance", 0) >= nr["cost"]
        rows.append([InlineKeyboardButton(
            text=f"💡 Исследовать — {fmt(nr['cost'])}$",
            callback_data="co_do_research" if can else "co_noop"
        )])
    else:
        rows.append([InlineKeyboardButton(text="⭐ Макс. инновации", callback_data="co_noop")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="co_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "co_research")
async def cb_research(callback: CallbackQuery):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await callback.message.edit_text(res_text(c), parse_mode="HTML", reply_markup=res_kb(c))
    await callback.answer()


@router.callback_query(F.data == "co_do_research")
async def cb_do_research(callback: CallbackQuery):
    uid = callback.from_user.id
    c   = get_company(uid)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    lvl = c.get("research_level", 0)
    if lvl >= MAX_RESEARCH:
        await callback.answer("Максимальный уровень!", show_alert=True)
        return
    nr = RESEARCH[lvl + 1]
    if c.get("balance", 0) < nr["cost"]:
        await callback.answer(f"❌ Нужно {fmt(nr['cost'])}$", show_alert=True)
        return
    c["balance"]       -= nr["cost"]
    c["research_level"] = lvl + 1
    new_ach = check_achievements(c)
    save_user_data()
    await callback.answer(f"✅ {nr['name']} освоено!", show_alert=True)
    await callback.message.edit_text(res_text(c), parse_mode="HTML", reply_markup=res_kb(c))
    if new_ach:
        await callback.message.answer("🏅 <b>Новые достижения!</b>\n" + "\n".join(f"• {a}" for a in new_ach), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#  НАСТРОЙКИ И ДОСТИЖЕНИЯ
# ══════════════════════════════════════════════════════════════

class CoSettings(StatesGroup):
    rename = State()


def settings_text(c: dict) -> str:
    earned  = c.get("achievements", [])
    ach_got = [a for a in ACHIEVEMENTS if a["id"] in earned]
    ach_no  = [a for a in ACHIEVEMENTS if a["id"] not in earned]
    return (
        f"🏅 <b>Настройки и достижения</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🏗 Название: <b>{c.get('name','Моя компания')}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏅 <b>Достижения: {len(earned)}/{len(ACHIEVEMENTS)}</b>\n\n"
        + ("\n".join(f"  🏅 <b>{a['name']}</b> — {a['desc']}" for a in ach_got) or "  Пока нет достижений")
        + (("\n\n<b>Не получено:</b>\n" + "\n".join(f"  🔒 {a['name']} — {a['desc']}" for a in ach_no)) if ach_no else "")
    )


@router.callback_query(F.data == "co_settings")
async def cb_settings(callback: CallbackQuery):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    new_ach = check_achievements(c)
    save_user_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Переименовать компанию", callback_data="co_rename")],
        [InlineKeyboardButton(text="◀️ Назад",                  callback_data="co_main")],
    ])
    await callback.message.edit_text(settings_text(c), parse_mode="HTML", reply_markup=kb)
    if new_ach:
        await callback.message.answer("🏅 <b>Новые достижения!</b>\n" + "\n".join(f"• {a}" for a in new_ach), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "co_rename")
async def cb_rename(callback: CallbackQuery, state: FSMContext):
    c = get_company(callback.from_user.id)
    if not c:
        await callback.answer("Нет компании.", show_alert=True)
        return
    await state.set_state(CoSettings.rename)
    await callback.message.edit_text(
        f"✏️ <b>Переименование компании</b>\n\n"
        f"Текущее: <b>{c.get('name','')}</b>\n\n"
        f"Введите новое название (макс. 32 символа):",
        parse_mode="HTML", reply_markup=back_kb("co_settings")
    )
    await callback.answer()


@router.message(CoSettings.rename)
async def msg_rename(message: Message, state: FSMContext):
    uid = message.from_user.id
    c   = get_company(uid)
    if not c:
        await state.clear()
        return
    name = message.text.strip()
    if len(name) > 32 or len(name) < 2:
        await message.answer("❌ Длина названия: 2–32 символа.")
        return
    old = c.get("name", "")
    c["name"] = name
    save_user_data()
    await state.clear()
    await message.answer(
        f"✅ Компания переименована!\n<b>{old}</b> → <b>{name}</b>",
        parse_mode="HTML", reply_markup=main_kb()
    )


# ══════════════════════════════════════════════════════════════
#  БЫСТРЫЙ МАРКЕТИНГ (5 мин) — текстовая команда
# ══════════════════════════════════════════════════════════════

@router.message(F.text.lower().in_([
    "ск маркетинг", "су маркетинг",
    "стройка маркетинг",
    "ск марк", "су марк",
]))
async def cmd_quick_promo(message: Message):
    uid = message.from_user.id
    c   = get_company(uid)
    if not c:
        await message.answer("❌ У вас нет строительной компании. Напишите <b>стройка</b>.", parse_mode="HTML")
        return

    flush_passive(c)
    now      = int(time.time())
    services = c.get("services", [])
    active   = [
        (i, obj) for i, obj in enumerate(services)
        if _obj_max_audience(obj, c.get("framework_level", 0)) > 0
    ]
    if not active:
        await message.answer(
            "❌ Нет объектов с видами работ.\n"
            "Добавьте виды работ к объекту, чтобы набирать заказчиков."
        )
        return

    total_cost = PROMO_QUICK_COST * len(active)
    bal        = c.get("balance", 0)
    if bal < total_cost:
        await message.answer(
            f"❌ Нужно <b>{fmt(total_cost)}$</b> (по {fmt(PROMO_QUICK_COST)}$ на {len(active)} объект(-ов)).\n"
            f"На счёте СК: <b>{fmt(bal)}$</b>",
            parse_mode="HTML"
        )
        return

    launched = []
    skipped  = []
    for i, obj in active:
        if obj.get("quick_promo_finish") and obj["quick_promo_finish"] > now:
            remaining = obj["quick_promo_finish"] - now
            skipped.append(f"  🔸 {obj.get('name','Объект')} — уже идёт ({fmt_time(remaining)})")
            continue
        obj["quick_promo_finish"] = now + PROMO_QUICK_DURATION
        c["balance"] -= PROMO_QUICK_COST
        launched.append(f"  ✅ {obj.get('name','Объект')}")

    save_user_data()

    if not launched:
        await message.answer(
            "⚠️ На всех объектах быстрый маркетинг уже активен:\n" + "\n".join(skipped),
            parse_mode="HTML"
        )
        return

    lines = [
        f"⚡ <b>Быстрый маркетинг запущен!</b>",
        f"",
        f"⏱ Длительность: <b>5 минут</b>",
        f"📈 Прирост аудитории: <b>+{PROMO_QUICK_GAIN_PCT}%</b> от максимума",
        f"💸 Списано: <b>{fmt(PROMO_QUICK_COST * len(launched))}$</b>",
        f"",
        f"<b>Объекты:</b>",
    ] + launched
    if skipped:
        lines += ["", "<b>Уже активен:</b>"] + skipped
    lines += [f"", f"💰 Баланс СК: <b>{fmt(c.get('balance',0))}$</b>"]

    await message.answer("\n".join(lines), parse_mode="HTML")
