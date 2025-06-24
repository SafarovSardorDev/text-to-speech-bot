import logging
import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Filter
from sql import Database
from dotenv import load_dotenv

load_dotenv()  # .env faylini o'qish

# Bazaga ulanish
db = Database(path_to_db="main.db")

# Bot sozlamalari
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, filter(None, os.getenv("ADMIN_IDS", "").split(","))))  # Bo'sh qiymatlarni filtrlash
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# Admin filtri
class AdminFilter(Filter):
    def check(self, obj):
        if isinstance(obj, types.Message):
            return obj.from_user.id in ADMIN_IDS
        elif isinstance(obj, types.CallbackQuery):
            return obj.from_user.id in ADMIN_IDS
        return False

# Admin filtrini ro'yxatga olish
dp.filters_factory.bind(AdminFilter)

# TTS API orqali matnni audio faylga aylantirish
async def tts_change(mod, text):
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    json_data = {
        "userId": "public-access",
        "platform": "landing_demo", 
        "ssml": f"<speak><p>{text}</p></speak>",
        "voice": f"{mod}",
        "narrationStyle": "regular"
    }

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=headers
        ) as session:
            async with session.post("https://play.ht/api/transcribe", json=json_data) as response:
                content_type = response.headers.get("Content-Type", "")
                
                # Audio fayl kelgan holatda
                if "audio" in content_type:
                    logging.info(f"✅ Audio fayl olindi: {content_type}")
                    return {
                        'file_content': await response.read(),
                        'content_type': content_type
                    }
                # JSON javob kelgan holatda
                elif "application/json" in content_type:
                    data = await response.json()
                    logging.info(f"✅ JSON javob olindi: {data}")
                    return data
                else:
                    logging.error(f"❌ Noma'lum content type: {content_type}")
                    # Javobni text sifatida o'qib ko'ramiz
                    text_response = await response.text()
                    logging.error(f"❌ Javob matni: {text_response[:200]}...")
                    return None
                    
    except asyncio.TimeoutError:
        logging.error("❌ TTS API timeout")
        return None
    except Exception as e:
        logging.error(f"❌ TTS API xatolik: {e}")
        return None

# URL'dan audio yuklab olish
async def download_file(url, destination):
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(destination, 'wb') as f:
                        f.write(await response.read())
                    return 'save'
                else:
                    logging.error(f"Yuklab olishda xatolik: {response.status}")
                    return None
    except asyncio.TimeoutError:
        logging.error("❌ Download timeout")
        return None
    except Exception as e:
        logging.error(f"❌ Download xatolik: {e}")
        return None

# /start buyrug'i
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    try:
        db.add_user(user_id=message.from_user.id, name=message.from_user.full_name, voice='women')
    except Exception as e:
        logging.error(f"Foydalanuvchi qo'shishda xatolik: {e}")
    
    # Admin va oddiy foydalanuvchilar uchun turli xabarlar
    if message.from_user.id in ADMIN_IDS:
        await message.answer(f"""<b>Assalomu alaykum, Admin {message.from_user.get_mention()}! 👑

Menga biror bir matn yozib yuboring va men sizga o'qib beraman 🎤

Admin buyruqlari:
/stat - Statistika
/send - Ommaviy xabar
/settings - Ovozni o'zgartirish</b>""")
    else:
        await message.answer(f"""<b>Assalomu alaykum, {message.from_user.get_mention()}!

Menga biror bir matn yozib yuboring va men sizga o'qib beraman 🎤

Ovozni o'zgartirish uchun /settings dan foydalaning.</b>""")

# /settings buyrug'i
@dp.message_handler(commands=['settings'])
async def change_voice(message: types.Message):
    try:
        db.add_user(user_id=message.from_user.id, name=message.from_user.full_name, voice='women')
    except Exception as e:
        logging.error(f"Foydalanuvchi qo'shishda xatolik: {e}")
    
    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("🧔‍♂️ Erkak ovoz", callback_data="male"),
        types.InlineKeyboardButton("👩‍🦰 Ayol ovoz", callback_data="women")
    )
    await message.answer("<b>🔊 Ovozni tanlang:</b>", reply_markup=markup)

# Inline tugmalar uchun
@dp.callback_query_handler(lambda call: call.data in ['male', 'women'])
async def change_voice_callback(call: types.CallbackQuery):
    try:
        db.update_user_voice(voice=call.data, user_id=call.from_user.id)
        txt = "🧔‍♂️ Erkak ovoz sozlandi!" if call.data == 'male' else "👩‍🦰 Ayol ovoz sozlandi!"
        await call.answer(text=txt, show_alert=True)
        await call.message.delete()
    except Exception as e:
        logging.error(f"Ovoz o'zgartirishda xatolik: {e}")
        await call.answer("❌ Xatolik yuz berdi", show_alert=True)

# /stat (faqat adminlar uchun)
@dp.message_handler(commands=['stat'], user_id=ADMIN_IDS)
async def stat_handler(message: types.Message):
    try:
        stat = db.stat()
        male_count = db.execute("SELECT COUNT(*) FROM Users WHERE voice = 'male'", fetchone=True)
        female_count = db.execute("SELECT COUNT(*) FROM Users WHERE voice = 'women'", fetchone=True)
        
        await message.answer(f"""📊 <b>Bot statistikasi:</b>

👥 Jami foydalanuvchilar: <code>{stat[0]}</code>
🧔‍♂️ Erkak ovoz: <code>{male_count[0] if male_count else 0}</code>
👩‍🦰 Ayol ovoz: <code>{female_count[0] if female_count else 0}</code>

🔧 Admin ID'lar: <code>{', '.join(map(str, ADMIN_IDS))}</code>""")
    except Exception as e:
        logging.error(f"Statistika olishda xatolik: {e}")
        await message.answer("❌ Statistikani olishda xatolik")

# /send (faqat adminlar uchun)
@dp.message_handler(commands=['send'], user_id=ADMIN_IDS)
async def broadcast(message: types.Message):
    if len(message.text.split()) < 2:
        await message.answer("❌ Xabar matnini kiriting:\n<code>/send Xabar matni</code>")
        return
    
    broadcast_text = message.text[6:]  # "/send " ni olib tashlash
    users = db.select_all_users()
    success_count = 0
    failed_count = 0
    
    msg = await message.answer("📤 Xabar yuborilmoqda...")
    
    for user in users:
        try:
            # HTML entities dan himoyalanish
            safe_text = broadcast_text.replace('<', '&lt;').replace('>', '&gt;')
            await bot.send_message(
                chat_id=user[1],
                text=safe_text,
                parse_mode=None  # HTML parsing o'chirish
            )
            success_count += 1
            await asyncio.sleep(0.05)  # Spam himoyasi
        except Exception as e:
            failed_count += 1
            logging.error(f"Foydalanuvchi {user[1]}ga xabar yuborishda xatolik: {e}")
    
    await msg.edit_text(f"""✅ <b>Xabar yuborish yakunlandi!</b>

📊 Muvaffaqiyatli: <code>{success_count}</code>
❌ Muvaffaqiyatsiz: <code>{failed_count}</code>
👥 Jami: <code>{len(users)}</code>""")

# Admin bo'lmagan foydalanuvchilar admin buyruqlarini ishlatganda
@dp.message_handler(commands=['stat', 'send'])
async def admin_commands_non_admin(message: types.Message):
    await message.answer("❌ Bu buyruq faqat adminlar uchun mo'ljallangan!")

# Matn uzunligini tekshirish
def is_text_valid(text):
    if len(text.strip()) == 0:
        return False, "❌ Bo'sh matn"
    if len(text) > 1000:
        return False, "❌ Matn juda uzun (maksimal 1000 ta belgi)"
    return True, ""

# Oddiy matn yuborilganda
@dp.message_handler(content_types=['text'])
async def handle_text(message: types.Message):
    # Matnni tekshirish
    is_valid, error_msg = is_text_valid(message.text)
    if not is_valid:
        await message.reply(error_msg)
        return
    
    # Foydalanuvchi ma'lumotlarini olish
    try:
        user_data = db.is_user(user_id=message.from_user.id)
        if user_data and len(user_data) > 0:
            voice = user_data[0][3]  # voice ustuni
            logging.info(f"🎤 Foydalanuvchi ovozi: {voice}")
        else:
            voice = 'women'
            # Yangi foydalanuvchini qo'shish
            db.add_user(user_id=message.from_user.id, name=message.from_user.full_name, voice='women')
            logging.info(f"➕ Yangi foydalanuvchi qo'shildi: {message.from_user.id}")
    except Exception as e:
        logging.error(f"Foydalanuvchi ma'lumotlarini olishda xatolik: {e}")
        voice = 'women'
    
    msg = await message.reply("🔄 Audio tayyorlanmoqda...")
    
    try:
        voice_model = "uz-UZ-SardorNeural" if voice == 'male' else "uz-UZ-MadinaNeural"
        res = await tts_change(mod=voice_model, text=message.text)
        
        if not res:
            await msg.edit_text("❌ Audio yaratishda xatolik yuz berdi")
            return
        
        file_path = f"audio_{message.message_id}_{message.from_user.id}.ogg"
        
        # Agar to'g'ridan-to'g'ri audio fayl kelgan bo'lsa
        if 'file_content' in res:
            try:
                with open(file_path, 'wb') as f:
                    f.write(res['file_content'])
                
                with open(file_path, "rb") as voice_file:
                    bot_info = await bot.get_me()
                    await bot.send_voice(
                        chat_id=message.from_user.id,
                        voice=voice_file,
                        caption=f"🎵 <i>{message.text}</i>\n\n🤖 @{bot_info.username}",
                        reply_to_message_id=message.message_id
                    )
                await msg.delete()
            except Exception as e:
                logging.error(f"To'g'ridan-to'g'ri audio yuborishda xatolik: {e}")
                await msg.edit_text("❌ Audio yuborishda xatolik")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        # Agar URL kelgan bo'lsa (JSON javob)
        elif 'file' in res and isinstance(res['file'], str):
            if await download_file(res['file'], file_path) == 'save':
                try:
                    with open(file_path, "rb") as voice_file:
                        bot_info = await bot.get_me()
                        await bot.send_voice(
                            chat_id=message.from_user.id,
                            voice=voice_file,
                            caption=f"🎵 <i>{message.text}</i>\n\n🤖 @{bot_info.username}",
                            reply_to_message_id=message.message_id
                        )
                    await msg.delete()
                except Exception as e:
                    logging.error(f"URL orqali audio yuborishda xatolik: {e}")
                    await msg.edit_text("❌ Audio yuborishda xatolik")
                finally:
                    if os.path.exists(file_path):
                        os.remove(file_path)
            else:
                await msg.edit_text("❌ Audio faylini yuklab olishda xatolik")
        else:
            await msg.edit_text("❌ Noma'lum javob formati")
            
    except Exception as e:
        logging.error(f"Handle text da umumiy xatolik: {e}")
        await msg.edit_text("❌ Xatolik yuz berdi, qaytadan urinib ko'ring")

# Bot komandalarini sozlash (adminlar uchun)
async def set_admin_commands():
    admin_commands = [
        types.BotCommand("start", "♻️ Botni qayta ishga tushurish"),
        types.BotCommand("settings", "🔊 Ovozni o'zgartirish"),
        types.BotCommand("stat", "📊 Bot statistikasi"),
        types.BotCommand("send", "📤 Ommaviy xabar yuborish"),
    ]
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=types.BotCommandScopeChat(chat_id=admin_id))
            logging.info(f"✅ Admin buyruqlari sozlandi: {admin_id}")
        except Exception as e:
            logging.error(f"❌ Admin {admin_id} uchun buyruqlar sozlanmadi: {e}")

# Bot komandalarini sozlash (oddiy foydalanuvchilar uchun)
async def set_user_commands():
    user_commands = [
        types.BotCommand("start", "♻️ Botni qayta ishga tushurish"),
        types.BotCommand("settings", "🔊 Ovozni o'zgartirish"),
    ]
    
    # Barcha foydalanuvchilar uchun default buyruqlar
    await bot.set_my_commands(user_commands, scope=types.BotCommandScopeDefault())
    logging.info("✅ Foydalanuvchi buyruqlari sozlandi")

# Bot ishga tushganda
async def on_startup(dp):
    await set_user_commands()  # Avval oddiy foydalanuvchilar uchun
    await set_admin_commands()  # Keyin adminlar uchun
    
    logging.info("🚀 Bot ishga tushdi!")
    logging.info(f"👑 Adminlar: {ADMIN_IDS}")
    
    # Adminlarga bot ishga tushgani haqida xabar
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🚀 <b>Bot muvaffaqiyatli ishga tushdi!</b>")
        except Exception as e:
            logging.error(f"Admin {admin_id}ga xabar yuborishda xatolik: {e}")

# Bot to'xtaganda
async def on_shutdown(dp):
    logging.info("🛑 Bot to'xtatildi!")
    
    # Adminlarga bot to'xtagani haqida xabar
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🛑 <b>Bot to'xtatildi!</b>")
        except Exception as e:
            logging.error(f"Admin {admin_id}ga xabar yuborishda xatolik: {e}")

if __name__ == '__main__':
    # Admin ID'larini tekshirish
    if not ADMIN_IDS:
        logging.warning("⚠️ ADMIN_IDS bo'sh! .env faylida ADMIN_IDS ni to'g'ri sozlang")
        logging.warning("⚠️ Misol: ADMIN_IDS=123456789,987654321")
    else:
        logging.info(f"👑 Adminlar ro'yxati: {ADMIN_IDS}")
    
    try:
        db.create_table_users()
        logging.info("📊 Ma'lumotlar bazasi tayyorlandi")
    except Exception as e:
        logging.error(f"Ma'lumotlar bazasini yaratishda xatolik: {e}")
    
    executor.start_polling(
        dp, 
        skip_updates=True, 
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )