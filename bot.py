import asyncio
import logging
import os
import random
import aiohttp
from PIL import Image, ImageDraw
from io import BytesIO
from aiogram import Bot, Dispatcher
from aiogram.types import BufferedInputFile

BOT_TOKEN = "8797652661:AAGHA6BZCf5mNVdxT-5CahP8XmJQ8OKlWFo"
CHANNEL_ID = os.getenv("CHANNEL_ID", "@futboltestjanal")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
CHECK_INTERVAL = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
sent_events = set()

async def download_image(url, session):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                return await r.read()
    except:
        pass
    return None

async def make_match_image(home, away, home_logo_url, away_logo_url, league, session):
    try:
        W, H = 800, 400
        img = Image.new("RGB", (W, H), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        # Yashil maydон chizig'i
        draw.rectangle([0, H-80, W, H], fill=(20, 83, 45))
        draw.rectangle([0, H-82, W, H-80], fill=(34, 197, 94))

        # Uy jamoa logosi
        if home_logo_url:
            data = await download_image(home_logo_url, session)
            if data:
                logo = Image.open(BytesIO(data)).convert("RGBA").resize((160, 160))
                img.paste(logo, (80, 100), logo)

        # Mehmon jamoa logosi
        if away_logo_url:
            data = await download_image(away_logo_url, session)
            if data:
                logo = Image.open(BytesIO(data)).convert("RGBA").resize((160, 160))
                img.paste(logo, (560, 100), logo)

        # VS yozuvi
        draw.ellipse([330, 140, 470, 260], fill=(30, 41, 59))
        draw.text((400, 200), "VS", fill=(255, 255, 255), anchor="mm")

        # Jamoalar nomi
        draw.text((160, 290), home[:12], fill=(255,255,255), anchor="mm")
        draw.text((640, 290), away[:12], fill=(255,255,255), anchor="mm")

        # Liga nomi
        draw.text((400, 350), league[:30], fill=(134, 239, 172), anchor="mm")

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()
    except Exception as e:
        log.error(f"Rasm yaratishda xato: {e}")
        return None

async def get_youtube_goal_video(home, away, session):
    try:
        query = f"{home} vs {away} goal 2025"
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(search_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
            text = await r.text()
        import re
        ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', text)
        if ids:
            return f"https://www.youtube.com/watch?v={ids[0]}"
    except Exception as e:
        log.error(f"YouTube xato: {e}")
    return None

async def get_live_matches(session):
    if not FOOTBALL_API_KEY:
        return []
    try:
        url = "https://v3.football.api-sports.io/fixtures?live=all"
        headers = {"x-apisports-key": FOOTBALL_API_KEY}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
            data = await r.json()
            return data.get("response", [])
    except Exception as e:
        log.error(f"API xato: {e}")
        return []

async def monitor(session):
    matches = await get_live_matches(session)
    for match in matches:
        fixture = match.get('fixture', {})
        teams = match.get('teams', {})
        goals = match.get('goals', {})
        events = match.get('events', [])
        league = match.get('league', {})
        match_id = fixture.get('id')
        home = teams.get('home', {}).get('name', '')
        away = teams.get('away', {}).get('name', '')
        home_logo = teams.get('home', {}).get('logo')
        away_logo = teams.get('away', {}).get('logo')
        home_score = goals.get('home', 0)
        away_score = goals.get('away', 0)
        status = fixture.get('status', {}).get('short', '')
        league_name = league.get('name', 'Futbol')

        # Match boshlandi
        start_key = f"start_{match_id}"
        if status == '1H' and start_key not in sent_events:
            sent_events.add(start_key)
            img_data = await make_match_image(home, away, home_logo, away_logo, league_name, session)
            caption = f"🏟️ MATCH BOSHLANDI!\n\n⚽ {home} 🆚 {away}\n🏆 {league_name}\n\nLive kuzating! 👁️"
            if img_data:
                photo = BufferedInputFile(img_data, filename="match.png")
                await bot.send_photo(CHANNEL_ID, photo=photo, caption=caption)
            else:
                await bot.send_message(CHANNEL_ID, caption)
            await asyncio.sleep(2)

        # Gollar
        for event in events:
            if event.get('type') == 'Goal':
                player = event.get('player', {}).get('name', 'O\'yinchi')
                team = event.get('team', {}).get('name', home)
                minute = event.get('time', {}).get('elapsed', 0)
                extra = event.get('time', {}).get('extra', 0)
                if not player or player.strip() == '':
                    player = "O'yinchi"

                key = f"goal_{match_id}_{player}_{minute}"
                if key not in sent_events:
                    sent_events.add(key)
                    min_str = f"{minute}+{extra}" if extra else str(minute)
                    caption = f"⚽ GOL! {min_str}'\n\n🏃 {player} ({team})\n\n📊 Hisob: {home} {home_score}—{away_score} {away}\n🏆 {league_name}"

                    video_url = await get_youtube_goal_video(home, away, session)
                    if video_url:
                        caption += f"\n\n🎬 Video: {video_url}"
                    await bot.send_message(CHANNEL_ID, caption)
                    await asyncio.sleep(2)

        # Match tugadi
        end_key = f"end_{match_id}"
        if status in ['FT', 'AET', 'PEN'] and end_key not in sent_events:
            sent_events.add(end_key)
            caption = f"🏁 MATCH YAKUNLANDI!\n\n{home} {home_score} — {away_score} {away}\n🏆 {league_name}"
            img_data = await make_match_image(home, away, home_logo, away_logo, league_name, session)
            if img_data:
                photo = BufferedInputFile(img_data, filename="result.png")
                await bot.send_photo(CHANNEL_ID, photo=photo, caption=caption)
            else:
                await bot.send_message(CHANNEL_ID, caption)
            await asyncio.sleep(2)

async def main_loop():
    log.info("Bot ishga tushdi!")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await monitor(session)
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                log.error(f"Xato: {e}")
                await asyncio.sleep(30)

async def main():
    await asyncio.gather(dp.start_polling(bot, handle_signals=False), main_loop())

if __name__ == "__main__":
    asyncio.run(main())
