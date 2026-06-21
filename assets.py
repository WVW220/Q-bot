"""
💼 АКТИВЫ — пассивный доход
Механика: купить → прокачать уровни → доход/час накапливается → собрать
"""
import time
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_user, save_user_data

router = Router()

MAX_LEVEL    = 5
MAX_ACCUM_H  = 12      # максимальное накопление — 12 часов

# ══════════════════════════════════════════════════════════════
#  КАТАЛОГ АКТИВОВ
# ══════════════════════════════════════════════════════════════

CATEGORIES = {
    "estate": {
        "name": "🏘 Недвижимость",
        "items": {
            "studio":    {"name": "🛋 Студия",      "buy": 100_000,     "income": 74},
            "cottage":   {"name": "🏡 Коттедж",     "buy": 500_000,     "income": 370},
            "penthouse": {"name": "🏙 Пентхаус",    "buy": 2_500_000,   "income": 1_850},
            "mansion":   {"name": "🏰 Особняк",     "buy": 10_000_000,  "income": 7_770},
            "villa":     {"name": "🌴 Вилла",        "buy": 40_000_000,  "income": 31_450},
        },
    },
    "business": {
        "name": "🏭 Предприятия",
        "items": {
            "cafe":      {"name": "☕ Кафе",           "buy": 150_000,     "income": 111},
            "service":   {"name": "🔧 Автосервис",    "buy": 800_000,     "income": 555},
            "mall":      {"name": "🏬 Торговый центр", "buy": 4_000_000,   "income": 2_960},
            "factory":   {"name": "🏭 Завод",          "buy": 20_000_000,  "income": 11_840},
            "holding":   {"name": "🏛 Холдинг",        "buy": 100_000_000, "income": 46_250},
        },
    },
    "transport": {
        "name": "🚗 Транспорт",
        "items": {
            "sedan":     {"name": "🚗 Седан",           "buy": 200_000,     "income": 148},
            "suv":       {"name": "🚙 Внедорожник",     "buy": 1_000_000,   "income": 740},
            "sportscar": {"name": "🏎 Спорткар",        "buy": 5_000_000,   "income": 3_700},
            "yacht":     {"name": "🛥 Яхта",             "buy": 25_000_000,  "income": 14_800},
            "jet":       {"name": "✈️ Частный джет",    "buy": 120_000_000, "income": 59_200},
        },
    },
}

# ══════════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ══════════════════════════════════════════════════════════════

def fmt(n) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def get_item(item_id: str) -> dict | None:
    for cat in CATEGORIES.values():
        if item_id in cat["items"]:
            return cat["items"][item_id]
    return None


def get_assets(user_id) -> dict:
    return get_user(user_id).setdefault("assets", {})


def income_at_level(base: int, level: int) -> int:
    """Доход в час на уровне N. Растёт ускоренно: +15% бонус за каждый уровень."""
    return int(base * level * (1.0 + 0.15 * (level - 1)))


def upgrade_cost(buy: int, current_level: int) -> int:
    """Стоимость улучшения с level → level+1."""
    return int(buy * 0.0625 * current_level)


def pending_income(entry: dict, base: int, level: int) -> int:
    elapsed_h = min(MAX_ACCUM_H, (time.time() - entry.get("last_collect", time.time())) / 3600)
    return int(income_at_level(base, level) * elapsed_h)


def total_income_per_hour(user_id) -> int:
    assets = get_assets(user_id)
    total  = 0
    for cat in CATEGORIES.values():
        for iid, idata in cat["items"].items():
            entry = assets.get(iid)
            if entry:
                total += income_at_level(idata["income"], entry["level"])
    return total


# ══════════════════════════════════════════════════════════════
#  КЛАВИАТУРЫ
# ══════════════════════════════════════════════════════════════

def assets_main_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=cat["name"], callback_data=f"ast_cat:{cid}")]
        for cid, cat in CATEGORIES.items()
    ]
    rows.append([InlineKeyboardButton(text="💰 Собрать всё", callback_data="ast_collect_all")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="rzv_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_owned_in_cat(cat_id: str, assets: dict) -> str | None:
    """Возвращает item_id купленного актива в категории, или None."""
    cat = CATEGORIES.get(cat_id, {})
    for iid in cat.get("items", {}):
        if iid in assets:
            return iid
    return None


def cat_kb(cat_id: str, assets: dict) -> InlineKeyboardMarkup:
    cat       = CATEGORIES[cat_id]
    owned_iid = get_owned_in_cat(cat_id, assets)
    rows      = []
    for iid, idata in cat["items"].items():
        entry = assets.get(iid)
        if entry:
            lvl    = entry["level"]
            earned = pending_income(entry, idata["income"], lvl)
            lbl    = f"✅ {idata['name']} ур.{lvl} | +{fmt(earned)}$ накоп."
        elif owned_iid:
            lbl = f"🔒 {idata['name']} — слот занят"
        else:
            lbl = f"{idata['name']} — {fmt(idata['buy'])}$"
        rows.append([InlineKeyboardButton(text=lbl, callback_data=f"ast_item:{iid}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="ast_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def item_kb(item_id: str, entry: dict | None, balance: int, locked: bool = False) -> InlineKeyboardMarkup:
    idata = get_item(item_id)
    rows  = []
    if not entry:
        if locked:
            rows.append([InlineKeyboardButton(
                text="🔒 Слот занят — продайте текущий актив",
                callback_data="ast_noop"
            )])
        else:
            can = balance >= idata["buy"]
            rows.append([InlineKeyboardButton(
                text=f"🛒 Купить — {fmt(idata['buy'])}$",
                callback_data=f"ast_buy:{item_id}" if can else "ast_noop"
            )])
    else:
        lvl    = entry["level"]
        earned = pending_income(entry, idata["income"], lvl)
        if earned > 0:
            rows.append([InlineKeyboardButton(
                text=f"💰 Собрать {fmt(earned)}$",
                callback_data=f"ast_collect:{item_id}"
            )])
        if lvl < MAX_LEVEL:
            ucost = upgrade_cost(idata["buy"], lvl)
            can   = balance >= ucost
            rows.append([InlineKeyboardButton(
                text=f"⬆️ Ур.{lvl}→{lvl+1} — {fmt(ucost)}$",
                callback_data=f"ast_upg:{item_id}" if can else "ast_noop"
            )])
        else:
            rows.append([InlineKeyboardButton(text="⭐ Максимальный уровень", callback_data="ast_noop")])
        rows.append([InlineKeyboardButton(
            text=f"💸 Продать (50% от стоимости)",
            callback_data=f"ast_sell:{item_id}"
        )])
    cat_id = _find_cat(item_id)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"ast_cat:{cat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _find_cat(item_id: str) -> str:
    for cid, cat in CATEGORIES.items():
        if item_id in cat["items"]:
            return cid
    return "estate"


# ══════════════════════════════════════════════════════════════
#  ТЕКСТЫ
# ══════════════════════════════════════════════════════════════

def assets_main_text(user_id) -> str:
    assets   = get_assets(user_id)
    total_h  = total_income_per_hour(user_id)
    total_ac = 0
    owned    = 0
    for cat in CATEGORIES.values():
        for iid, idata in cat["items"].items():
            entry = assets.get(iid)
            if entry:
                owned    += 1
                total_ac += pending_income(entry, idata["income"], entry["level"])
    return (
        f"💼 <b>Активы</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Активов куплено: <b>{owned}</b>\n"
        f"💰 Доход в час: <b>{fmt(total_h)}$/ч</b>\n"
        f"⏳ Накоплено сейчас: <b>{fmt(total_ac)}$</b>\n\n"
        f"Выбери категорию:"
    )


def cat_text(cat_id: str, user_id) -> str:
    cat    = CATEGORIES[cat_id]
    assets = get_assets(user_id)
    lines  = []
    for iid, idata in cat["items"].items():
        entry = assets.get(iid)
        if entry:
            lvl    = entry["level"]
            ih     = income_at_level(idata["income"], lvl)
            earned = pending_income(entry, idata["income"], lvl)
            lines.append(
                f"  {idata['name']} ур.<b>{lvl}</b> | {fmt(ih)}$/ч | накоп. <b>{fmt(earned)}$</b>"
            )
        else:
            lines.append(f"  {idata['name']} — <i>не куплено</i> ({fmt(idata['buy'])}$)")
    return (
        f"{cat['name']}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        + "\n".join(lines)
    )


def item_text(item_id: str, entry: dict | None, locked: bool = False) -> str:
    idata = get_item(item_id)
    name  = idata["name"]
    if not entry:
        ih_1 = income_at_level(idata["income"], 1)
        ih_max = income_at_level(idata["income"], MAX_LEVEL)
        lock_note = "\n\n🔒 <i>Слот категории занят. Продайте текущий актив, чтобы купить другой.</i>" if locked else ""
        return (
            f"{name}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Статус: <i>не куплено</i>\n"
            f"💰 Стоимость: <b>{fmt(idata['buy'])}$</b>\n\n"
            f"📈 <b>Доход по уровням:</b>\n"
            f"  Ур. 1:   {fmt(ih_1)}$/ч\n"
            f"  Ур. {MAX_LEVEL} (макс): {fmt(ih_max)}$/ч\n\n"
            f"<i>Накопление до {MAX_ACCUM_H} часов</i>"
            f"{lock_note}"
        )
    lvl    = entry["level"]
    ih_cur = income_at_level(idata["income"], lvl)
    earned = pending_income(entry, idata["income"], lvl)
    elapsed_h = min(MAX_ACCUM_H, (time.time() - entry.get("last_collect", time.time())) / 3600)
    nxt    = ""
    if lvl < MAX_LEVEL:
        ih_nxt = income_at_level(idata["income"], lvl + 1)
        ucost  = upgrade_cost(idata["buy"], lvl)
        nxt    = (
            f"\n⬆️ Следующий уровень:\n"
            f"  Доход: {fmt(ih_nxt)}$/ч (+{fmt(ih_nxt-ih_cur)})\n"
            f"  Стоимость: {fmt(ucost)}$"
        )
    return (
        f"{name}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🔢 Уровень: <b>{lvl}/{MAX_LEVEL}</b>\n"
        f"💰 Доход: <b>{fmt(ih_cur)}$/ч</b>\n"
        f"⏳ Накоплено: <b>{fmt(earned)}$</b> ({elapsed_h:.1f}ч)\n"
        f"{nxt}"
    )


# ══════════════════════════════════════════════════════════════
#  ХЭНДЛЕРЫ
# ══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ast_main")
async def cb_ast_main(callback: CallbackQuery):
    uid = callback.from_user.id
    try:
        await callback.message.edit_text(
            assets_main_text(uid), parse_mode="HTML", reply_markup=assets_main_kb()
        )
    except Exception:
        await callback.message.answer(
            assets_main_text(uid), parse_mode="HTML", reply_markup=assets_main_kb()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ast_cat:"))
async def cb_ast_cat(callback: CallbackQuery):
    uid    = callback.from_user.id
    cat_id = callback.data.split(":")[1]
    if cat_id not in CATEGORIES:
        await callback.answer("Категория не найдена.", show_alert=True)
        return
    assets = get_assets(uid)
    try:
        await callback.message.edit_text(
            cat_text(cat_id, uid), parse_mode="HTML", reply_markup=cat_kb(cat_id, assets)
        )
    except Exception:
        await callback.message.answer(
            cat_text(cat_id, uid), parse_mode="HTML", reply_markup=cat_kb(cat_id, assets)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ast_item:"))
async def cb_ast_item(callback: CallbackQuery):
    uid     = callback.from_user.id
    item_id = callback.data.split(":")[1]
    idata   = get_item(item_id)
    if not idata:
        await callback.answer("Актив не найден.", show_alert=True)
        return
    from utils import get_balance
    assets  = get_assets(uid)
    entry   = assets.get(item_id)
    balance = get_balance(uid)
    cat_id  = _find_cat(item_id)
    owned   = get_owned_in_cat(cat_id, assets)
    locked  = bool(owned and owned != item_id)
    try:
        await callback.message.edit_text(
            item_text(item_id, entry, locked), parse_mode="HTML",
            reply_markup=item_kb(item_id, entry, balance, locked)
        )
    except Exception:
        await callback.message.answer(
            item_text(item_id, entry, locked), parse_mode="HTML",
            reply_markup=item_kb(item_id, entry, balance, locked)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ast_buy:"))
async def cb_ast_buy(callback: CallbackQuery):
    from utils import get_balance, update_balance
    uid     = callback.from_user.id
    item_id = callback.data.split(":")[1]
    idata   = get_item(item_id)
    if not idata:
        await callback.answer("Актив не найден.", show_alert=True)
        return
    assets = get_assets(uid)
    if item_id in assets:
        await callback.answer("Уже куплено!", show_alert=True)
        return
    cat_id = _find_cat(item_id)
    owned  = get_owned_in_cat(cat_id, assets)
    if owned:
        owned_name = get_item(owned)["name"]
        await callback.answer(
            f"🔒 В категории уже есть: {owned_name}.\nПродайте его, чтобы купить другой.",
            show_alert=True
        )
        return
    bal = get_balance(uid)
    if bal < idata["buy"]:
        await callback.answer(f"❌ Нужно {fmt(idata['buy'])}$, у вас {fmt(bal)}$", show_alert=True)
        return
    update_balance(uid, bal - idata["buy"])
    assets[item_id] = {"level": 1, "last_collect": int(time.time())}
    save_user_data()
    await callback.answer(f"✅ {idata['name']} куплено!", show_alert=True)
    entry   = assets[item_id]
    balance = get_balance(uid)
    try:
        await callback.message.edit_text(
            item_text(item_id, entry), parse_mode="HTML",
            reply_markup=item_kb(item_id, entry, balance)
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("ast_collect:"))
async def cb_ast_collect(callback: CallbackQuery):
    from utils import get_balance, update_balance
    uid     = callback.from_user.id
    item_id = callback.data.split(":")[1]
    idata   = get_item(item_id)
    if not idata:
        await callback.answer("Актив не найден.", show_alert=True)
        return
    assets = get_assets(uid)
    entry  = assets.get(item_id)
    if not entry:
        await callback.answer("Актив не куплен.", show_alert=True)
        return
    earned = pending_income(entry, idata["income"], entry["level"])
    if earned <= 0:
        await callback.answer("Нечего собирать — подождите немного.", show_alert=True)
        return
    update_balance(uid, get_balance(uid) + earned)
    entry["last_collect"] = int(time.time())
    save_user_data()
    await callback.answer(f"💰 Получено {fmt(earned)}$!", show_alert=True)
    balance = get_balance(uid)
    try:
        await callback.message.edit_text(
            item_text(item_id, entry), parse_mode="HTML",
            reply_markup=item_kb(item_id, entry, balance)
        )
    except Exception:
        pass


@router.callback_query(F.data == "ast_collect_all")
async def cb_ast_collect_all(callback: CallbackQuery):
    from utils import get_balance, update_balance
    uid    = callback.from_user.id
    assets = get_assets(uid)
    total  = 0
    for cat in CATEGORIES.values():
        for iid, idata in cat["items"].items():
            entry = assets.get(iid)
            if entry:
                earned = pending_income(entry, idata["income"], entry["level"])
                if earned > 0:
                    total += earned
                    entry["last_collect"] = int(time.time())
    if total <= 0:
        await callback.answer("Нечего собирать — подождите немного.", show_alert=True)
        return
    update_balance(uid, get_balance(uid) + total)
    save_user_data()
    await callback.answer(f"💰 Собрано {fmt(total)}$ со всех активов!", show_alert=True)
    try:
        await callback.message.edit_text(
            assets_main_text(uid), parse_mode="HTML", reply_markup=assets_main_kb()
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("ast_upg:"))
async def cb_ast_upg(callback: CallbackQuery):
    from utils import get_balance, update_balance
    uid     = callback.from_user.id
    item_id = callback.data.split(":")[1]
    idata   = get_item(item_id)
    if not idata:
        await callback.answer("Актив не найден.", show_alert=True)
        return
    assets = get_assets(uid)
    entry  = assets.get(item_id)
    if not entry:
        await callback.answer("Актив не куплен.", show_alert=True)
        return
    lvl = entry["level"]
    if lvl >= MAX_LEVEL:
        await callback.answer("Максимальный уровень!", show_alert=True)
        return
    cost = upgrade_cost(idata["buy"], lvl)
    bal  = get_balance(uid)
    if bal < cost:
        await callback.answer(f"❌ Нужно {fmt(cost)}$, у вас {fmt(bal)}$", show_alert=True)
        return
    earned = pending_income(entry, idata["income"], lvl)
    if earned > 0:
        update_balance(uid, bal - cost + earned)
        entry["last_collect"] = int(time.time())
    else:
        update_balance(uid, bal - cost)
    entry["level"] = lvl + 1
    save_user_data()
    await callback.answer(f"✅ {idata['name']} улучшен до ур.{lvl+1}!", show_alert=True)
    balance = get_balance(uid)
    try:
        await callback.message.edit_text(
            item_text(item_id, entry), parse_mode="HTML",
            reply_markup=item_kb(item_id, entry, balance)
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("ast_sell:"))
async def cb_ast_sell(callback: CallbackQuery):
    from utils import get_balance, update_balance
    uid     = callback.from_user.id
    item_id = callback.data.split(":")[1]
    idata   = get_item(item_id)
    if not idata:
        await callback.answer("Актив не найден.", show_alert=True)
        return
    assets = get_assets(uid)
    entry  = assets.get(item_id)
    if not entry:
        await callback.answer("Актив не куплен.", show_alert=True)
        return
    lvl    = entry["level"]
    earned = pending_income(entry, idata["income"], lvl)
    refund = idata["buy"] // 2 + sum(upgrade_cost(idata["buy"], l) for l in range(1, lvl)) // 2
    update_balance(uid, get_balance(uid) + refund + earned)
    del assets[item_id]
    save_user_data()
    await callback.answer(
        f"💸 {idata['name']} продан. Получено {fmt(refund + earned)}$ (возврат + накопленный доход)",
        show_alert=True
    )
    cat_id = _find_cat(item_id)
    try:
        await callback.message.edit_text(
            cat_text(cat_id, uid), parse_mode="HTML",
            reply_markup=cat_kb(cat_id, assets)
        )
    except Exception:
        pass


@router.callback_query(F.data == "ast_noop")
async def cb_ast_noop(callback: CallbackQuery):
    await callback.answer("❌ Недостаточно средств.", show_alert=True)
