import asyncio
import logging
import os
import aiohttp
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher
from aiogram.types import BufferedInputFile, URLInputFile

BOT_TOKEN = "8797652661:AAGHA6BZCf5mNVdxT-5CahP8XmJQ8OKlWFo"
CHANNEL_ID = os.getenv("CHANNEL_ID", "@futboltestjanal")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
CHECK_INTERVAL = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
sent_events = set()

async def download_bytes(url, session):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status == 200:
                return await r.read()
    except:
        pass
    return None

async def make_match_banner(home, away, home_logo_url, away_logo_url, league, score_home=None, score_away=None, session=None):
    try:
        W, H = 800, 400
        img = Image.new("RGB", (W, H), color=(10, 15, 30))
        draw = ImageDraw.Draw(img)

        # Gradient background
        for y in range(H):
            r = int(10 + (y/H) * 20)
            g = int(15 + (y/H) * 30)
            b = int(30 + (y/H) * 60)
            draw.line([(0,y),(W,y)], fill=(r,g,b))

        # Yashil chiziq pastda
        draw.rectangle([0, H-8, W, H], fill=(34, 197, 94))

        # Uy jamoa logosi
        if home_logo_url and session:
            data = await download_bytes(home_logo_url, session)
            if data:
                try:
                    logo = Image.open(BytesIO(data)).convert("RGBA").resize((150, 150))
                    img.paste(logo, (60, 90), logo)
                except:
                    pass

        # Mehmon jamoa logosi
        if away_logo_url and session:
            data = await download_bytes(away_logo_url, session)
            if data:
                try:
                    logo = Image.open(BytesIO(data)).convert("RGBA").resize((150, 150))
                    img.paste(logo, (590, 90), logo)
                except:
                    pass

        # Markaziy doira
        draw.ellipse([310, 120, 490, 280], fill=(20, 30, 60), outline=(34, 197, 94), width=3)

        # Skor yoki VS
        if score_home is not None and score_away is not None:
            draw.text((400, 185), f"{score_home} — {score_away}", fill=(255, 255, 255), anchor="mm")
        else:
            draw.text((400, 185), "VS", fill=(255, 255, 255), anchor="mm")

        # Jamoalar nomi
        home_short = home[:13] if len(home) > 13 else home
        away_short = away[:13] if len(away) > 13 else away
        draw.text((135, 270), home_short, fill=(200, 200, 200), anchor="mm")
        draw.text((665, 270), away_short, fill=(200, 200, 200), anchor="mm")

        # Liga nomi
        league_short = league[:35] if len(league) > 35 else league
        draw.rectangle([150, 330, 650, 370], fill=(20, 83, 45))
        draw.text((400, 350), league_short, fill=(134, 239, 172), anchor="mm")

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()
    except Exception as e:
        log.error(f"Banner xato: {e}")
        return None

async def get_goal_video(home, away, session):
    try:
        # Scorebat API - bepul gol videolari
        url = "https://www.scorebat.com/video-api/v3/feed/?token="
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json()
                videos = data.get("response", [])
                for v in videos:
                    title = v.get("title", "").lower()
                    if home.lower()[:4] in title or away.lower()[:4] in title:
                        videos_list = v.get("videos", [])
                        if videos_list:
                            return videos_list[0].get("embed", "")
    except Exception as e:
        log.error(f"Scorebat xato: {e}")
    return None

async def download_and_send_video(video_url, caption, session):
    try:
        data = await download_bytes(video_url, session)
        if data and len(data) < 50 * 1024 * 1024:  # 50MB limit
            video_file = BufferedInputFile(data, filename="goal.mp4")
            await bot.send_video(CHANNEL_ID, video=video_file, caption=caption)
            return True
    except Exception as e:
        log.error(f"Video yuborishda xato: {e}")
    return False

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
        home_score = goals.get('home', 0) or 0
        away_score = goals.get('away', 0) or 0
        status = fixture.get('status', {}).get('short', '')
        league_name = league.get('name', 'Futbol')

        # Match boshlandi
        start_key = f"start_{match_id}"
        if status == '1H' and start_key not in sent_events:
            sent_events.add(start_key)
            caption = f"🏟️ MATCH BOSHLANDI!\n\n⚽ {home} 🆚 {away}\n🏆 {league_name}\n\nLive kuzating! 👁️"
            img = await make_match_banner(home, away, home_logo, away_logo, league_name, session=session)
            if img:
                await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(img, "match.png"), caption=caption)
            else:
                await bot.send_message(CHANNEL_ID, caption)
            await asyncio.sleep(2)

        # Gollar
        for event in events:
            if event.get('type') == 'Goal':
                player = event.get('player', {}).get('name', '') or "O'yinchi"
                team = event.get('team', {}).get('name', home)
                minute = event.get('time', {}).get('elapsed', 0)
                extra = event.get('time', {}).get('extra', 0)
                min_str = f"{minute}+{extra}" if extra else str(minute)

                key = f"goal_{match_id}_{player}_{minute}"
                if key not in sent_events:
                    sent_events.add(key)
                    caption = f"⚽ GOL! {min_str}'\n\n🏃 {player}\n🆚 {home} {home_score}—{away_score} {away}\n🏆 {league_name}"

                    # Avval gol videosini qidiramiz
                    video_sent = False
                    video_url = await get_goal_video(home, away, session)
                    if video_url:
                        video_sent = await download_and_send_video(video_url, caption, session)

                    # Video topilmasa chiroyli banner yuboramiz
                    if not video_sent:
                        img = await make_match_banner(
                            home, away, home_logo, away_logo, league_name,
                            score_home=home_score, score_away=away_score, session=session
                        )
                        if img:
                            await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(img, "goal.png"), caption=caption)
                        else:
                            await bot.send_message(CHANNEL_ID, caption)
                    await asyncio.sleep(2)

        # Match tugadi
        end_key = f"end_{match_id}"
        if status in ['FT', 'AET', 'PEN'] and end_key not in sent_events:
            sent_events.add(end_key)
            caption = f"🏁 YAKUNIY NATIJA!\n\n{home} {home_score} — {away_score} {away}\n🏆 {league_name}"
            img = await make_match_banner(
                home, away, home_logo, away_logo, league_name,
                score_home=home_score, score_away=away_score, session=session
            )
            if img:
                await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(img, "result.png"), caption=caption)
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
