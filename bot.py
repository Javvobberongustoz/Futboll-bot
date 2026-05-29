import asyncio
import logging
import os
import random
import aiohttp
from aiogram import Bot, Dispatcher

BOT_TOKEN = "8797652661:AAGHA6BZCf5mNVdxT-5CahP8XmJQ8OKlWFo"
CHANNEL_ID = os.getenv("CHANNEL_ID", "@futboltestjanal")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
CHECK_INTERVAL = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
sent_events = set()

GOAL_TEMPLATES = [
    "⚽ GOL! {minute}' | {player} ({team})\nto'rni larzaga keltirdi! 🔥\n\n📊 Hisob: {home} {home_score}—{away_score} {away}",
    "🚨 GOLLL! {minute}-daqiqa!\n{player} ({team}) gol urdi! 💥\n\n📊 Hisob: {home} {home_score}—{away_score} {away}",
    "⚽ {minute}' — {player} ({team})\nAjoyib zarba! 🎯\n\n📊 Hisob: {home} {home_score}—{away_score} {away}",
]

TRANSFER_TEMPLATES = [
    "🔄 TRANSFER!\n\n🏃 O'yinchi: {player}\n📤 Ketdi: {from_club}\n📥 Keldi: {to_club}\n💰 Narx: {fee}",
]

MATCH_START_TEMPLATES = [
    "🏟️ MATCH BOSHLANDI!\n\n⚽ {home} 🆚 {away}\n🏆 {league}\n\nLive kuzating! 👁️",
]

MATCH_END_TEMPLATES = [
    "🏁 MATCH YAKUNLANDI!\n\n{home} {home_score} — {away_score} {away}\n🏆 {league}",
]

async def send_post(text, photo_url=None):
    try:
        if photo_url:
            try:
                from aiogram.types import URLInputFile
                photo = URLInputFile(photo_url)
                await bot.send_photo(CHANNEL_ID, photo=photo, caption=text)
                log.info("Rasm bilan post yuborildi")
                return
            except Exception as e:
                log.error(f"Rasm yuborishda xato: {e}")
        await bot.send_message(CHANNEL_ID, text)
        log.info(f"Post yuborildi: {text[:50]}...")
    except Exception as e:
        log.error(f"Xato: {e}")

async def get_team_logo(team_id, session):
    try:
        url = f"https://v3.football.api-sports.io/teams?id={team_id}"
        headers = {"x-apisports-key": FOOTBALL_API_KEY}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
            data = await r.json()
            teams = data.get("response", [])
            if teams:
                return teams[0].get("team", {}).get("logo")
    except:
        pass
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

async def get_news(session):
    try:
        url = "https://feeds.bbci.co.uk/sport/football/rss.xml"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            text = await r.text()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(text)
        items = []
        for item in root.findall('.//item')[:3]:
            title = item.findtext('title', '')
            desc = item.findtext('description', '')
            guid = item.findtext('guid', '')
            if guid and guid not in sent_events:
                items.append({'id': guid, 'title': title, 'desc': desc[:200]})
        return items
    except:
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
        home_id = teams.get('home', {}).get('id')
        away_id = teams.get('away', {}).get('id')
        home_score = goals.get('home', 0)
        away_score = goals.get('away', 0)
        status = fixture.get('status', {}).get('short', '')
        league_name = league.get('name', 'Futbol')
        league_logo = league.get('logo')

        start_key = f"start_{match_id}"
        if status == '1H' and start_key not in sent_events:
            sent_events.add(start_key)
            tpl = random.choice(MATCH_START_TEMPLATES)
            msg = tpl.format(home=home, away=away, league=league_name)
            logo = league_logo or await get_team_logo(home_id, session)
            await send_post(msg, photo_url=logo)
            await asyncio.sleep(2)

        for event in events:
            if event.get('type') == 'Goal':
                player = event.get('player', {}).get('name', '')
                team = event.get('team', {}).get('name', home)
                team_id = event.get('team', {}).get('id', home_id)
                minute = event.get('time', {}).get('elapsed', 0)
                extra = event.get('time', {}).get('extra', 0)

                if not player or player.strip() == '':
                    player = "O'yinchi"

                key = f"goal_{match_id}_{player}_{minute}"
                if key not in sent_events:
                    sent_events.add(key)
                    min_str = f"{minute}+{extra}" if extra else str(minute)
                    tpl = random.choice(GOAL_TEMPLATES)
                    msg = tpl.format(
                        player=player, team=team, minute=min_str,
                        home=home, away=away,
                        home_score=home_score, away_score=away_score
                    )
                    logo = await get_team_logo(team_id, session)
                    await send_post(msg, photo_url=logo)
                    await asyncio.sleep(2)

        end_key = f"end_{match_id}"
        if status in ['FT', 'AET', 'PEN'] and end_key not in sent_events:
            sent_events.add(end_key)
            tpl = random.choice(MATCH_END_TEMPLATES)
            msg = tpl.format(
                home=home, away=away,
                home_score=home_score, away_score=away_score,
                league=league_name
            )
            logo = league_logo or await get_team_logo(home_id, session)
            await send_post(msg, photo_url=logo)
            await asyncio.sleep(2)

async def main_loop():
    log.info("Bot ishga tushdi!")
    async with aiohttp.ClientSession() as session:
        news_counter = 0
        while True:
            try:
                await monitor(session)
                news_counter += 1
                if news_counter >= 10:
                    items = await get_news(session)
                    for item in items[:2]:
                        sent_events.add(item['id'])
                        msg = f"📰 {item['title']}\n\n{item['desc']}"
                        await send_post(msg)
                        await asyncio.sleep(3)
                    news_counter = 0
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                log.error(f"Xato: {e}")
                await asyncio.sleep(30)

async def main():
    await asyncio.gather(dp.start_polling(bot, handle_signals=False), main_loop())

if __name__ == "__main__":
    asyncio.run(main())
