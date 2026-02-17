import os
import json
import logging
from flask import Flask
from threading import Thread
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from datetime import datetime
import traceback

# --- تنظیمات لاگینگ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- وب سرور (برای Health Check) ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "✅ VPN Bot is Running!", 200

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- توکن و آیدی ادمین (مستقیم در کد) ---
TOKEN = '8305364438:AAGAT39wGQey9tzxMVafEiRRXz1eGNvpfhY'
ADMIN_ID = 7935344235

# --- مسیر دیتابیس ---
DB_FILE = 'data.json'

# --- پلن‌های پیش‌فرض ---
DEFAULT_PLANS = {
    "🚀 قوی": [
        {"id": 1, "name": "⚡️ پلن قوی 20GB", "price": 80, "volume": "20GB", "days": 30, "users": 1},
        {"id": 2, "name": "🔥 پلن قوی 50GB", "price": 140, "volume": "50GB", "days": 30, "users": 1}
    ],
    "💎 ارزان": [
        {"id": 3, "name": "💎 پلن اقتصادی 10GB", "price": 45, "volume": "10GB", "days": 30, "users": 1},
        {"id": 4, "name": "💎 پلن اقتصادی 20GB", "price": 75, "volume": "20GB", "days": 30, "users": 1}
    ],
    "🎯 به صرفه": [
        {"id": 5, "name": "🎯 پلن ویژه 30GB", "price": 110, "volume": "30GB", "days": 30, "users": 1},
        {"id": 6, "name": "🎯 پلن ویژه 60GB", "price": 190, "volume": "60GB", "days": 30, "users": 1}
    ],
    "👥 چند کاربره": [
        {"id": 7, "name": "👥 2 کاربره 40GB", "price": 150, "volume": "40GB", "days": 30, "users": 2},
        {"id": 8, "name": "👥 3 کاربره 60GB", "price": 210, "volume": "60GB", "days": 30, "users": 3}
    ]
}

def load_db():
    """بارگذاری دیتابیس از فایل"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("✅ Database loaded successfully")
                
                # اضافه کردن فیلدهای جدید اگر وجود نداشتند
                if "force_join" not in data:
                    data["force_join"] = {"enabled": False, "channel_id": "", "channel_link": "", "channel_username": ""}
                if "texts" not in data:
                    data["texts"] = {}
                if "invite" not in data["texts"]:
                    data["texts"]["invite"] = "🤝 لینک دعوت شما:\n{link}\n\nبه ازای هر دعوت 1 روز هدیه"
                return data
    except Exception as e:
        logger.error(f"❌ Error loading database: {e}")
    
    # دیتابیس پیش‌فرض
    logger.info("📁 Creating default database")
    return {
        "users": {},
        "brand": "تک نت وی‌پی‌ان",
        "card": {
            "number": "6277601368776066",
            "name": "محمد رضوانی"
        },
        "support": "@Support_Admin",
        "guide": "@Guide_Channel",
        "categories": DEFAULT_PLANS.copy(),
        "force_join": {"enabled": False, "channel_id": "", "channel_link": "", "channel_username": ""},
        "texts": {
            "welcome": "🔰 به {brand} خوش آمدید\n\n✅ فروش ویژه فیلترشکن\n✅ پشتیبانی 24 ساعته\n✅ نصب آسان",
            "support": "🆘 پشتیبانی: {support}",
            "guide": "📚 آموزش: {guide}",
            "test": "🎁 درخواست تست شما ثبت شد",
            "force": "🔒 برای استفاده از ربات باید در کانال زیر عضو شوید:\n{link}\n\nپس از عضویت، دکمه ✅ تایید را بزنید.",
            "invite": "🤝 لینک دعوت شما:\n{link}\n\nبه ازای هر دعوت 1 روز هدیه"
        }
    }

def save_db(data):
    """ذخیره دیتابیس در فایل"""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info("💾 Database saved")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving database: {e}")
        return False

# بارگذاری دیتابیس
db = load_db()
user_data = {}

# --- منوها ---
def main_menu(uid):
    """منوی اصلی کاربر"""
    kb = [
        ['💰 خرید', '🎁 تست'],
        ['📂 سرویس‌ها', '⏳ تمدید'],
        ['👤 پشتیبانی', '📚 آموزش'],
        ['🤝 دعوت دوستان']
    ]
    if str(uid) == str(ADMIN_ID):
        kb.append(['⚙️ مدیریت'])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def back_btn():
    """کیبورد برگشت"""
    return ReplyKeyboardMarkup([['🔙 برگشت']], resize_keyboard=True)

def admin_menu():
    """منوی مدیریت"""
    kb = [
        ['➕ پلن جدید', '➖ حذف پلن'],
        ['💳 ویرایش کارت', '📝 ویرایش متن‌ها'],
        ['👤 ویرایش پشتیبان', '📢 ویرایش کانال'],
        ['🔒 عضویت اجباری', '🏷 ویرایش برند'],
        ['📊 آمار', '📨 ارسال همگانی'],
        ['🔙 برگشت']
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# --- بررسی عضویت اجباری ---
def check_join(user_id, context):
    """بررسی عضویت کاربر در کانال"""
    if not db["force_join"]["enabled"]:
        return True
    
    channel_id = db["force_join"].get("channel_id", "")
    channel_username = db["force_join"].get("channel_username", "")
    
    if not channel_id and not channel_username:
        return True
    
    # امتحان با آیدی عددی
    if channel_id:
        try:
            member = context.bot.get_chat_member(
                chat_id=int(channel_id),
                user_id=int(user_id)
            )
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except:
            pass
    
    # امتحان با یوزرنیم
    if channel_username:
        try:
            member = context.bot.get_chat_member(
                chat_id=channel_username,
                user_id=int(user_id)
            )
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except:
            pass
    
    return False

# --- شروع ربات ---
def start(update, context):
    """هندلر دستور /start"""
    try:
        uid = str(update.effective_user.id)
        
        # ثبت کاربر جدید
        if uid not in db["users"]:
            db["users"][uid] = {
                "purchases": [],
                "tests": [],
                "test_count": 0,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            save_db(db)
        
        user_data[uid] = {}
        
        # بررسی عضویت اجباری
        if db["force_join"]["enabled"] and db["force_join"]["channel_link"]:
            if not check_join(uid, context):
                btn = InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 عضویت در کانال", url=db["force_join"]["channel_link"]),
                    InlineKeyboardButton("✅ تایید عضویت", callback_data="join_check")
                ]])
                msg = db["texts"]["force"].format(link=db["force_join"]["channel_link"])
                update.message.reply_text(msg, reply_markup=btn)
                return
        
        # خوش‌آمدگویی
        welcome = db["texts"]["welcome"].format(brand=db["brand"])
        update.message.reply_text(welcome, reply_markup=main_menu(uid))
        
    except Exception as e:
        logger.error(f"Error in start: {e}")
        update.message.reply_text("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

# --- مدیریت پیام‌ها ---
def handle_msg(update, context):
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        name = update.effective_user.first_name or "کاربر"
        step = user_data.get(uid, {}).get('step')

        # بررسی عضویت اجباری برای همه پیام‌ها
        if db["force_join"]["enabled"] and db["force_join"]["channel_link"]:
            if not check_join(uid, context) and text != '/start':
                btn = InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 عضویت در کانال", url=db["force_join"]["channel_link"]),
                    InlineKeyboardButton("✅ تایید عضویت", callback_data="join_check")
                ]])
                update.message.reply_text(
                    db["texts"]["force"].format(link=db["force_join"]["channel_link"]),
                    reply_markup=btn
                )
                return

        # برگشت به منوی اصلی
        if text == '🔙 برگشت':
            user_data[uid] = {}
            start(update, context)
            return

        # --- تست رایگان ---
        if text == '🎁 تست':
            if db["users"][uid]["test_count"] >= 1:
                update.message.reply_text("❌ شما قبلاً یک بار تست دریافت کرده‌اید و امکان دریافت تست مجدد وجود ندارد.")
                return
            
            db["users"][uid]["test_count"] += 1
            db["users"][uid]["tests"].append(datetime.now().strftime("%Y-%m-%d"))
            save_db(db)
            
            update.message.reply_text(db["texts"]["test"])
            
            # اطلاع به ادمین
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("📤 ارسال تست", callback_data=f"test_{uid}_{name}")
            ]])
            context.bot.send_message(
                ADMIN_ID,
                f"🎁 درخواست تست جدید\n👤 {name}\n🆔 {uid}",
                reply_markup=btn
            )
            return

        # --- سرویس‌های من ---
        if text == '📂 سرویس‌ها':
            purchases = db["users"][uid].get("purchases", [])
            tests = db["users"][uid].get("tests", [])
            
            msg = "📂 سرویس‌های شما:\n━━━━━━━━━━\n"
            if purchases:
                msg += "✅ خریدها:\n"
                for i, p in enumerate(purchases[-10:], 1):
                    msg += f"{i}. {p}\n"
            else:
                msg += "❌ خریدی ندارید\n"
            
            if tests:
                msg += "\n🎁 تست‌ها:\n"
                for i, t in enumerate(tests[-5:], 1):
                    msg += f"{i}. {t}\n"
            
            update.message.reply_text(msg)
            return

        # --- تمدید سرویس ---
        if text == '⏳ تمدید':
            purchases = db["users"][uid].get("purchases", [])
            if not purchases:
                update.message.reply_text("❌ شما سرویسی برای تمدید ندارید.")
                return
            
            keyboard = []
            for i, p in enumerate(purchases[-5:]):
                keyboard.append([InlineKeyboardButton(
                    f"🔄 {p[:30]}...",
                    callback_data=f"renew_{i}"
                )])
            update.message.reply_text(
                "🔁 سرویس مورد نظر برای تمدید را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # --- پشتیبانی ---
        if text == '👤 پشتیبانی':
            update.message.reply_text(db["texts"]["support"].format(support=db["support"]))
            return

        # --- آموزش ---
        if text == '📚 آموزش':
            update.message.reply_text(db["texts"]["guide"].format(guide=db["guide"]))
            return

        # --- دعوت دوستان ---
        if text == '🤝 دعوت دوستان':
            bot_username = context.bot.get_me().username
            link = f"https://t.me/{bot_username}?start={uid}"
            msg = db["texts"]["invite"].format(link=link)
            update.message.reply_text(msg)
            return

        # --- خرید اشتراک ---
        if text == '💰 خرید':
            categories = list(db["categories"].keys())
            kb = [[c] for c in categories] + [['🔙 برگشت']]
            update.message.reply_text(
                "📂 لطفاً دسته‌بندی مورد نظر را انتخاب کنید:",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
            )
            return

        # --- نمایش پلن‌های یک دسته ---
        if text in db["categories"] and not step:
            plans = db["categories"][text]
            if not plans:
                update.message.reply_text("❌ این دسته‌بندی پلنی ندارد.")
                return
            
            keyboard = []
            for p in plans:
                price_toman = p['price'] * 1000
                users_text = f"👥 {p['users']} کاربره - " if p['users'] > 1 else ""
                btn_text = f"{p['name']} - {users_text}{price_toman:,} تومان"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"buy_{p['id']}")])
            
            update.message.reply_text(
                f"📦 {text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # --- مدیریت (فقط برای ادمین) ---
        if str(uid) == str(ADMIN_ID):
            
            # منوی مدیریت
            if text == '⚙️ مدیریت':
                update.message.reply_text("🛠 پنل مدیریت:", reply_markup=admin_menu())
                return

            # --- ویرایش کارت ---
            if text == '💳 ویرایش کارت':
                keyboard = [
                    ['شماره کارت', 'نام صاحب کارت'],
                    ['🔙 برگشت']
                ]
                current = f"شماره: {db['card']['number']}\nنام: {db['card']['name']}"
                update.message.reply_text(
                    current,
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            if text == 'شماره کارت':
                user_data[uid] = {'step': 'card_num'}
                update.message.reply_text("💳 شماره کارت 16 رقمی را بفرستید:", reply_markup=back_btn())
                return

            if text == 'نام صاحب کارت':
                user_data[uid] = {'step': 'card_name'}
                update.message.reply_text("👤 نام صاحب کارت را بفرستید:", reply_markup=back_btn())
                return

            # --- ویرایش پشتیبان ---
            if text == '👤 ویرایش پشتیبان':
                user_data[uid] = {'step': 'support'}
                update.message.reply_text("👤 آیدی پشتیبان را بفرستید (مثال: @Support_Admin):", reply_markup=back_btn())
                return

            # --- ویرایش کانال آموزش ---
            if text == '📢 ویرایش کانال':
                user_data[uid] = {'step': 'guide'}
                update.message.reply_text("📢 آیدی کانال آموزش را بفرستید (مثال: @Guide_Channel):", reply_markup=back_btn())
                return

            # --- ویرایش برند ---
            if text == '🏷 ویرایش برند':
                user_data[uid] = {'step': 'brand'}
                update.message.reply_text("🏷 نام جدید برند را بفرستید:", reply_markup=back_btn())
                return

            # --- ویرایش متن‌ها ---
            if text == '📝 ویرایش متن‌ها':
                keyboard = [
                    ['خوش‌آمدگویی', 'پشتیبانی', 'آموزش'],
                    ['تست رایگان', 'عضویت اجباری', 'دعوت دوستان'],
                    ['🔙 برگشت']
                ]
                update.message.reply_text(
                    "📝 کدام متن را ویرایش کنیم؟",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            text_map = {
                'خوش‌آمدگویی': 'welcome',
                'پشتیبانی': 'support',
                'آموزش': 'guide',
                'تست رایگان': 'test',
                'عضویت اجباری': 'force',
                'دعوت دوستان': 'invite'
            }
            
            if text in text_map:
                user_data[uid] = {'step': f'edit_{text_map[text]}'}
                current_text = db["texts"][text_map[text]]
                update.message.reply_text(
                    f"📝 متن فعلی:\n{current_text}\n\nمتن جدید را بفرستید:",
                    reply_markup=back_btn()
                )
                return

            # --- عضویت اجباری ---
            if text == '🔒 عضویت اجباری':
                keyboard = [
                    ['✅ فعال', '❌ غیرفعال'],
                    ['🔗 تنظیم لینک کانال'],
                    ['🔙 برگشت']
                ]
                status = "✅ فعال" if db["force_join"]["enabled"] else "❌ غیرفعال"
                channel = db["force_join"]["channel_username"] or "تنظیم نشده"
                update.message.reply_text(
                    f"🔒 وضعیت عضویت اجباری:\nوضعیت: {status}\nکانال: {channel}",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            if text == '✅ فعال':
                if db["force_join"]["channel_link"]:
                    db["force_join"]["enabled"] = True
                    save_db(db)
                    update.message.reply_text("✅ عضویت اجباری فعال شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ ابتدا لینک کانال را تنظیم کنید")
                return

            if text == '❌ غیرفعال':
                db["force_join"]["enabled"] = False
                save_db(db)
                update.message.reply_text("✅ عضویت اجباری غیرفعال شد", reply_markup=admin_menu())
                return

            if text == '🔗 تنظیم لینک کانال':
                user_data[uid] = {'step': 'set_link'}
                update.message.reply_text(
                    "🔗 لینک کانال را بفرستید:\nمثال: https://t.me/mychannel",
                    reply_markup=back_btn()
                )
                return

            # --- آمار ربات ---
            if text == '📊 آمار':
                total_users = len(db["users"])
                total_purchases = sum(len(u.get("purchases", [])) for u in db["users"].values())
                total_tests = sum(len(u.get("tests", [])) for u in db["users"].values())
                today = datetime.now().strftime("%Y-%m-%d")
                today_users = sum(1 for u in db["users"].values() if u.get("date", "").startswith(today))
                
                stats = (
                    f"📊 آمار ربات\n"
                    f"━━━━━━━━━━\n"
                    f"👥 کل کاربران: {total_users}\n"
                    f"🆕 کاربران جدید امروز: {today_users}\n"
                    f"💰 تعداد خریدها: {total_purchases}\n"
                    f"🎁 تعداد تست‌ها: {total_tests}"
                )
                update.message.reply_text(stats)
                return

            # --- ارسال همگانی ---
            if text == '📨 ارسال همگانی':
                user_data[uid] = {'step': 'broadcast'}
                update.message.reply_text(
                    "📨 پیام همگانی را بفرستید:",
                    reply_markup=back_btn()
                )
                return

            # --- افزودن پلن جدید ---
            if text == '➕ پلن جدید':
                categories = list(db["categories"].keys())
                kb = [[c] for c in categories] + [['🔙 برگشت']]
                user_data[uid] = {'step': 'new_cat'}
                update.message.reply_text(
                    "📂 دسته‌بندی مورد نظر را انتخاب کنید:",
                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
                )
                return

            # --- حذف پلن ---
            if text == '➖ حذف پلن':
                keyboard = []
                for cat, plans in db["categories"].items():
                    for p in plans:
                        btn = InlineKeyboardButton(
                            f"❌ {cat} - {p['name']}",
                            callback_data=f"del_{p['id']}"
                        )
                        keyboard.append([btn])
                
                if keyboard:
                    update.message.reply_text(
                        "🗑 پلن مورد نظر برای حذف را انتخاب کنید:",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    update.message.reply_text("❌ هیچ پلنی برای حذف وجود ندارد.")
                return

            # --- مراحل ویرایش ---
            if step == 'card_num':
                if text.isdigit() and len(text) == 16:
                    db["card"]["number"] = text
                    save_db(db)
      