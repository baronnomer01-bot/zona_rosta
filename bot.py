import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

import telebot
from groq import Groq
from telebot import types

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-70b-versatile"
RUTUBE_URL = "https://rutube.ru/channel/66854675/"

if not TELEGRAM_TOKEN:
    raise RuntimeError("Не задана переменная окружения TELEGRAM_TOKEN")

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

user_profiles: Dict[int, Dict[str, str]] = {}
user_steps: Dict[int, str] = {}

GOALS = {
    "Похудение": {"factor": 0.85, "protein": 2.0, "fat": 0.8},
    "Поддержание": {"factor": 1.0, "protein": 1.7, "fat": 0.9},
    "Набор массы": {"factor": 1.15, "protein": 1.8, "fat": 1.0},
}

QUESTIONS = {
    "gender": "💪 Стартуем профессионально. Укажите пол:",
    "weight": "📈 Принято. Теперь укажите вес в кг:",
    "height": "🔥 Отлично. Укажите рост в см:",
    "age": "💪 Двигаемся дальше. Укажите возраст:",
    "goal": "🥗 Финальный шаг анкеты. Выберите цель:",
}

NEXT_STEP = {
    "gender": "weight",
    "weight": "height",
    "height": "age",
    "age": "goal",
}


@dataclass
class NutritionResult:
    calories: int
    protein: int
    fat: int
    carbs: int


def main_menu() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎥 Техника")
    markup.row("💬 Связь с наставником")
    markup.row("🔄 Обновить анкету")
    return markup


def gender_keyboard() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("М", "Ж")
    return markup


def goal_keyboard() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("Похудение", "Поддержание")
    markup.row("Набор массы")
    return markup


def rutube_keyboard() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🎥 Техника упражнений на Rutube", url=RUTUBE_URL)
    )
    return markup


def normalize_gender(value: str) -> Optional[str]:
    value = value.strip().lower()
    if value in {"м", "муж", "мужчина", "мужской"}:
        return "М"
    if value in {"ж", "жен", "женщина", "женский"}:
        return "Ж"
    return None


def parse_positive_number(value: str, minimum: int, maximum: int) -> Optional[float]:
    try:
        number = float(value.replace(",", ".").strip())
    except ValueError:
        return None
    if minimum <= number <= maximum:
        return number
    return None


def calculate_nutrition(profile: Dict[str, str]) -> NutritionResult:
    gender = profile["gender"]
    weight = float(profile["weight"])
    height = float(profile["height"])
    age = float(profile["age"])
    goal = profile["goal"]

    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if gender == "М" else -161)
    calories = bmr * 1.4 * GOALS[goal]["factor"]

    protein = weight * GOALS[goal]["protein"]
    fat = weight * GOALS[goal]["fat"]
    carbs = max((calories - protein * 4 - fat * 9) / 4, 0)

    return NutritionResult(
        calories=round(calories),
        protein=round(protein),
        fat=round(fat),
        carbs=round(carbs),
    )


def scale(value: int, calories: int) -> int:
    return max(round(value * calories / 2000), 1)


def nutrition_text(profile: Dict[str, str]) -> str:
    result = calculate_nutrition(profile)
    calories = result.calories
    goal = profile["goal"]

    return (
        f"🥗 <b>Индивидуальный план питания под цель: {goal}</b>\n\n"
        f"📈 <b>Ориентир на день:</b> {result.calories} ккал / Б {result.protein} г / Ж {result.fat} г / У {result.carbs} г\n\n"
        f"<b>Завтрак</b> 🔥\n"
        f"Овсянка сухая — {scale(60, calories)} г\n"
        f"Яйца — {scale(100, calories)} г\n"
        f"Творог 5% — {scale(120, calories)} г\n"
        f"Ягоды или фрукт — {scale(100, calories)} г\n\n"
        f"<b>Обед</b> 💪\n"
        f"Куриная грудка или индейка — {scale(170, calories)} г\n"
        f"Гречка/рис в сухом виде — {scale(75, calories)} г\n"
        f"Овощи — {scale(250, calories)} г\n"
        f"Оливковое масло — {scale(10, calories)} г\n\n"
        f"<b>Перекус</b> 🥗\n"
        f"Йогурт натуральный — {scale(180, calories)} г\n"
        f"Орехи — {scale(20, calories)} г\n"
        f"Фрукт — {scale(120, calories)} г\n\n"
        f"<b>Ужин</b> 📈\n"
        f"Рыба/постное мясо — {scale(180, calories)} г\n"
        f"Картофель/крупа в готовом виде — {scale(180, calories)} г\n"
        f"Овощи — {scale(250, calories)} г\n"
        f"Авокадо или масло — {scale(15, calories)} г\n\n"
        f"💪 Воду держите в диапазоне 30–35 мл на 1 кг веса. Дисциплина в питании — фундамент прогресса."
    )


def training_text(gender: str) -> str:
    if gender == "М":
        return (
            "🔥 <b>Индивидуальная программа ПН-СР-ПТ для мужчин</b>\n\n"
            "<b>Разминка перед каждой тренировкой — 10 минут</b> 💪\n"
            "Легкое кардио 5 минут, суставная гимнастика, 2 разминочных подхода первого упражнения.\n\n"
            "<b>Понедельник — грудь, плечи, трицепс</b> 📈\n"
            "Жим лежа — 4×8–10\n"
            "Жим гантелей под углом — 3×10\n"
            "Жим гантелей сидя — 4×8–10\n"
            "Разведения гантелей в стороны — 3×12–15\n"
            "Французский жим — 3×10–12\n"
            "Планка — 3×40–60 сек\n\n"
            "<b>Среда — спина, бицепс</b> 💪\n"
            "Подтягивания или тяга верхнего блока — 4×8–12\n"
            "Тяга штанги/гантели в наклоне — 4×8–10\n"
            "Горизонтальная тяга — 3×10–12\n"
            "Гиперэкстензия — 3×12–15\n"
            "Подъем штанги на бицепс — 3×10–12\n"
            "Скручивания — 3×15–20\n\n"
            "<b>Пятница — ноги, ягодицы, корпус</b> 🔥\n"
            "Приседания — 4×8–10\n"
            "Румынская тяга — 4×8–10\n"
            "Жим ногами — 3×10–12\n"
            "Выпады — 3×10 на каждую ногу\n"
            "Подъемы на икры — 4×12–15\n"
            "Подъем ног в висе/лежа — 3×12–15\n\n"
            "<b>Заминка после каждой тренировки — 7 минут</b> 🥗\n"
            f"Спокойная ходьба 3 минуты, растяжка грудных, спины, бедер и икр.\n\n"
            f"🎥 Техника выполнения упражнений: {RUTUBE_URL}"
        )

    return (
        "🔥 <b>Индивидуальная программа ПН-СР-ПТ для женщин</b>\n\n"
        "<b>Разминка перед каждой тренировкой — 10 минут</b> 💪\n"
        "Легкое кардио 5 минут, круговые движения суставов, активация ягодиц резинкой 2×15.\n\n"
        "<b>Понедельник — ягодицы, ноги</b> 📈\n"
        "Ягодичный мост — 4×10–12\n"
        "Приседания с гантелью — 4×10–12\n"
        "Румынская тяга — 3×10–12\n"
        "Отведение ноги назад — 3×12–15\n"
        "Выпады назад — 3×10 на каждую ногу\n"
        "Планка — 3×30–45 сек\n\n"
        "<b>Среда — спина, плечи, руки</b> 💪\n"
        "Тяга верхнего блока — 4×10–12\n"
        "Горизонтальная тяга — 3×10–12\n"
        "Жим гантелей сидя — 3×10\n"
        "Разведения гантелей в стороны — 3×12–15\n"
        "Сгибание рук с гантелями — 3×12\n"
        "Разгибание рук на трицепс — 3×12\n\n"
        "<b>Пятница — все тело и корпус</b> 🔥\n"
        "Жим ногами — 4×10–12\n"
        "Тяга гантелей в наклоне — 3×10–12\n"
        "Шаги на платформу — 3×10 на каждую ногу\n"
        "Сгибание ног лежа — 3×12\n"
        "Махи ягодичные — 3×15\n"
        "Скручивания — 3×15–20\n\n"
        "<b>Заминка после каждой тренировки — 7 минут</b> 🥗\n"
        f"Спокойная ходьба 3 минуты, мягкая растяжка ягодиц, бедер, спины и плеч.\n\n"
        f"🎥 Техника выполнения упражнений: {RUTUBE_URL}"
    )


def profile_summary(profile: Dict[str, str]) -> str:
    result = calculate_nutrition(profile)
    return (
        "🔥 <b>Анкета завершена. План построен.</b>\n\n"
        f"📈 Пол: {profile['gender']}\n"
        f"💪 Вес: {profile['weight']} кг\n"
        f"📈 Рост: {profile['height']} см\n"
        f"🔥 Возраст: {profile['age']}\n"
        f"🥗 Цель: {profile['goal']}\n\n"
        f"<b>Ваш расчет КБЖУ:</b>\n"
        f"Калории: {result.calories} ккал\n"
        f"Белки: {result.protein} г\n"
        f"Жиры: {result.fat} г\n"
        f"Углеводы: {result.carbs} г\n\n"
        f"💪 Работаем системно: ниже сразу ваша программа и питание."
    )


def result_strategy_focus(profile: Dict[str, str]) -> str:
    gender = profile["gender"]
    goal = profile["goal"]
    if gender == "М" and "Набор" in goal:
        return (
            "Главный акцент: прогрессия рабочих весов, тяжелые базовые тренировки, "
            "достаточное питание и сон 7,5–9 часов как ключевой фактор роста мышечной ткани."
        )
    if gender == "Ж" and ("Похудение" in goal or "Сушка" in goal):
        return (
            "Главный акцент: контролируемый дефицит калорий, увеличение кардио-нагрузки, "
            "ежедневная активность и сохранение силовых тренировок для удержания мышечного тонуса."
        )
    if "Набор" in goal:
        return (
            "Главный акцент: умеренный профицит калорий, силовая прогрессия, техника движений "
            "и стабильное восстановление."
        )
    if "Похудение" in goal:
        return (
            "Главный акцент: умеренный дефицит калорий, шаги, кардио, силовые тренировки "
            "и контроль восстановления."
        )
    return (
        "Главный акцент: удержание стабильного режима, качественная техника, регулярные тренировки "
        "и контроль состава тела без резких скачков нагрузки."
    )


def local_result_advice(profile: Dict[str, str]) -> str:
    result = calculate_nutrition(profile)
    return (
        "🧠🔥 <b>Совет наставника ЗОНА РОСТА</b>\n\n"
        f"{result_strategy_focus(profile)}\n\n"
        f"📈 Ваш рабочий ориентир: {result.calories} ккал, белки {result.protein} г, "
        f"жиры {result.fat} г, углеводы {result.carbs} г. "
        "Держите план 10–14 дней, отслеживайте вес, самочувствие и качество тренировок. "
        "Физиология любит стабильность: регулярная нагрузка, питание по норме и сон дают прогнозируемый результат. 💪"
    )


def ai_result_advice(profile: Dict[str, str]) -> str:
    if not groq_client:
        return local_result_advice(profile)

    result = calculate_nutrition(profile)
    prompt = (
        f"Профиль пользователя: пол {profile['gender']}, вес {profile['weight']} кг, "
        f"рост {profile['height']} см, возраст {profile['age']}, цель {profile['goal']}. "
        f"Расчет по Миффлину-Сан Жеору с коэффициентом 1.4 и коррекцией под цель: "
        f"{result.calories} ккал, белки {result.protein} г, жиры {result.fat} г, углеводы {result.carbs} г. "
        f"{result_strategy_focus(profile)} "
        "Дай индивидуальный совет после анкеты: 2 коротких абзаца и 3 четких пункта действий."
    )

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты элитный фитнес-наставник проекта ЗОНА РОСТА. "
                        "Отвечай четко, профессионально, драйвово и по физиологии. "
                        "Используй тематические смайлики 💪 🥗 🔥 📈. "
                        "Не ставь медицинские диагнозы."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.55,
            max_tokens=700,
        )
        content = completion.choices[0].message.content
        return content or local_result_advice(profile)
    except Exception:
        return local_result_advice(profile)


def ask_step(chat_id: int, step: str) -> None:
    if step == "gender":
        bot.send_message(chat_id, QUESTIONS[step], reply_markup=gender_keyboard())
    elif step == "goal":
        bot.send_message(chat_id, QUESTIONS[step], reply_markup=goal_keyboard())
    else:
        bot.send_message(chat_id, QUESTIONS[step])


def start_questionnaire(chat_id: int) -> None:
    user_profiles[chat_id] = {}
    user_steps[chat_id] = "gender"
    ask_step(chat_id, "gender")


def handle_questionnaire(message: types.Message) -> bool:
    chat_id = message.chat.id
    step = user_steps.get(chat_id)
    if not step:
        return False

    text = (message.text or "").strip()
    profile = user_profiles.setdefault(chat_id, {})

    if step == "gender":
        gender = normalize_gender(text)
        if not gender:
            bot.send_message(
                chat_id,
                "💪 Укажите пол корректно: М или Ж.",
                reply_markup=gender_keyboard(),
            )
            return True
        profile["gender"] = gender
    elif step == "weight":
        value = parse_positive_number(text, 30, 250)
        if value is None:
            bot.send_message(chat_id, "📈 Введите корректный вес от 30 до 250 кг.")
            return True
        profile["weight"] = str(value)
    elif step == "height":
        value = parse_positive_number(text, 120, 230)
        if value is None:
            bot.send_message(chat_id, "🔥 Введите корректный рост от 120 до 230 см.")
            return True
        profile["height"] = str(value)
    elif step == "age":
        value = parse_positive_number(text, 12, 100)
        if value is None:
            bot.send_message(chat_id, "💪 Введите корректный возраст от 12 до 100 лет.")
            return True
        profile["age"] = str(value)
    elif step == "goal":
        if text not in GOALS:
            bot.send_message(
                chat_id, "🥗 Выберите цель кнопкой ниже.", reply_markup=goal_keyboard()
            )
            return True
        profile["goal"] = text

    next_step = NEXT_STEP.get(step)
    if next_step:
        user_steps[chat_id] = next_step
        ask_step(chat_id, next_step)
    else:
        user_steps.pop(chat_id, None)
        bot.send_message(
            chat_id, profile_summary(profile), reply_markup=types.ReplyKeyboardRemove()
        )
        bot.send_message(chat_id, ai_result_advice(profile))
        bot.send_message(
            chat_id, training_text(profile["gender"]), reply_markup=rutube_keyboard()
        )
        bot.send_message(chat_id, nutrition_text(profile), reply_markup=main_menu())

    return True


def profile_context(chat_id: int) -> str:
    profile = user_profiles.get(chat_id)
    if not profile or not all(
        key in profile for key in ["gender", "weight", "height", "age", "goal"]
    ):
        return "Анкета пользователя пока не заполнена."
    result = calculate_nutrition(profile)
    return (
        f"Анкета пользователя: пол {profile['gender']}, вес {profile['weight']} кг, "
        f"рост {profile['height']} см, возраст {profile['age']}, цель {profile['goal']}. "
        f"Расчет КБЖУ: {result.calories} ккал, белки {result.protein} г, "
        f"жиры {result.fat} г, углеводы {result.carbs} г."
    )


def ask_groq(chat_id: int, question: str) -> str:
    if not groq_client:
        return local_mentor_answer(chat_id, question)

    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты фитнес-помощник проекта ЗОНА РОСТА. Отвечай по-русски, ясно, полезно и безопасно. "
                    "Тон: элитный фитнес-наставник — профессионально, драйвово, с тематическими смайликами 💪 🥗 🔥 📈. "
                    "Не ставь диагнозы и советуй обратиться к врачу при медицинских жалобах. "
                    f"{profile_context(chat_id)}"
                ),
            },
            {"role": "user", "content": question},
        ],
        temperature=0.6,
        max_tokens=900,
    )
    return (
        completion.choices[0].message.content
        or "Не удалось получить ответ. Попробуйте еще раз."
    )


def local_mentor_answer(chat_id: int, question: str) -> str:
    lowered = question.lower()
    profile = user_profiles.get(chat_id)
    if "техник" in lowered or "видео" in lowered or "rutube" in lowered:
        return f"🎥 Техника — это безопасность и прогресс. Разбор упражнений здесь: {RUTUBE_URL}"
    if (
        "пит" in lowered
        or "рацион" in lowered
        or "кбжу" in lowered
        or "калор" in lowered
    ):
        if profile and all(
            key in profile for key in ["gender", "weight", "height", "age", "goal"]
        ):
            return nutrition_text(profile)
        return "🥗 Сначала заполним анкету: пол, вес, рост, возраст и цель. После этого я рассчитаю КБЖУ и дам план питания."
    if "трен" in lowered or "программ" in lowered or "упраж" in lowered:
        if profile and all(
            key in profile for key in ["gender", "weight", "height", "age", "goal"]
        ):
            return training_text(profile["gender"])
        return "💪 Сначала нужна анкета. После неё я сразу выдам программу ПН-СР-ПТ под ваш пол и цель."
    return (
        "🔥 Я на связи как наставник ЗОНЫ РОСТА. "
        "Держите фокус на трех рычагах: тренировки по плану, питание по КБЖУ и восстановление. "
        "Задайте вопрос про питание, тренировки, технику или прогресс — отвечу по делу. 💪📈"
    )


def require_profile(chat_id: int) -> Optional[Dict[str, str]]:
    profile = user_profiles.get(chat_id)
    if not profile or not all(
        key in profile for key in ["gender", "weight", "height", "age", "goal"]
    ):
        bot.send_message(
            chat_id,
            "💪 Сначала заполните анкету — после этого я выдам точный план.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        start_questionnaire(chat_id)
        return None
    return profile


def prepare_telegram_connection() -> None:
    try:
        try:
            bot.delete_webhook(drop_pending_updates=True)
        except TypeError:
            bot.remove_webhook()
        bot.get_me()
    except Exception as error:
        raise RuntimeError(f"Не удалось подключиться к Telegram: {error}") from error
    print("Бот запущен и готов к работе", flush=True)


def run_bot_forever() -> None:
    while True:
        try:
            bot.infinity_polling(
                skip_pending=False, timeout=30, long_polling_timeout=30
            )
        except Exception as error:
            print(f"Ожидание переподключения к Telegram: {error}", flush=True)
            time.sleep(10)


@bot.message_handler(commands=["start", "help"])
def send_welcome(message: types.Message) -> None:
    bot.send_message(
        message.chat.id,
        "🔥 Добро пожаловать в ЗОНУ РОСТА.\n\n"
        "Я проведу вас как элитный фитнес-наставник: сначала собираем анкету, затем сразу выдаю КБЖУ, программу ПН-СР-ПТ и питание. 💪🥗📈",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    start_questionnaire(message.chat.id)


@bot.message_handler(commands=["profile"])
def profile_command(message: types.Message) -> None:
    start_questionnaire(message.chat.id)


@bot.message_handler(commands=["training"])
def training_command(message: types.Message) -> None:
    profile = require_profile(message.chat.id)
    if profile:
        bot.send_message(
            message.chat.id, training_text(profile["gender"]), reply_markup=main_menu()
        )


@bot.message_handler(commands=["nutrition"])
def nutrition_command(message: types.Message) -> None:
    profile = require_profile(message.chat.id)
    if profile:
        bot.send_message(
            message.chat.id, nutrition_text(profile), reply_markup=main_menu()
        )


@bot.message_handler(commands=["rutube"])
def rutube_command(message: types.Message) -> None:
    bot.send_message(
        message.chat.id,
        f"🎥 Техника выполнения упражнений: {RUTUBE_URL}",
        reply_markup=rutube_keyboard(),
    )


@bot.message_handler(content_types=["text"])
def handle_text(message: types.Message) -> None:
    chat_id = message.chat.id
    text = (message.text or "").strip()

    if handle_questionnaire(message):
        return

    if text in {"Анкета", "🔄 Обновить анкету"}:
        start_questionnaire(chat_id)
        return

    if text in {"Rutube", "🎥 Техника"}:
        bot.send_message(
            chat_id,
            f"🎥 Техника выполнения упражнений: {RUTUBE_URL}",
            reply_markup=rutube_keyboard(),
        )
        return

    if text in {"Задать вопрос", "💬 Связь с наставником"}:
        bot.send_message(
            chat_id,
            "💬 Напишите вопрос одним сообщением. Я отвечу как наставник: четко, по делу и с фокусом на результат. 🔥",
            reply_markup=main_menu(),
        )
        return

    try:
        bot.send_chat_action(chat_id, "typing")
        answer = ask_groq(chat_id, text)
    except Exception:
        answer = local_mentor_answer(chat_id, text)
    bot.send_message(chat_id, answer, reply_markup=main_menu())


if __name__ == "__main__":
    prepare_telegram_connection()
    run_bot_forever()
