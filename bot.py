import asyncio
import logging
import os
import random
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import URLInputFile
import aiohttp

BOT_TOKEN = "8797652661:AAGHA6BZCf5mNVdxT-5CahP8XmJQ8OKlWFo"
CHANNEL_ID = "@futboltestjanal"
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
CHECK_INTERVAL = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
sent_events = set()

GOAL_TEMPLATES = [
    "⚽ GOL! {minute}' | {player} ({team}) to'rni larzaga keltirdi! 🔥\n\n#{team_tag} #{league_tag} #Futbol #Gol",
    "🚨 GOLLL! {minute}-daqiqa! {player} gol urdi! 💥\n\n#{team_tag} #{league_tag} #UzbekFutbol",
    "⚽ {minute}' — {player} ({team}) — GOL! Ajoyib zarba! 🎯\n\nKanal: @futboltestjanal\n#{team_tag} #{league_tag}",
]
TRANSFER_TEMPLATES = [
    "🔄 TRANSFER!\n\n🏃 O'yinchi: {player}\n📤 Ketdi: {from_club}\n📥 Keldi: {to_club}\n💰 Narx: {fee}\n\n#Transfer #Futbol",
]
MATCH_START_TEMPLATES = [
    "🏟️ MATCH BOSHLANDI!\n\n⚽ {home} 🆚 {away}\n🏆 {league}\n\nLive kuzating! 👁️\n#{home_tag} #{away_tag}",
]
MATCH_END_TEMPLATES = [
    "🏁 MATCH YAKUNLANDI!\n\n{home} {home_score} — {away_score} {away}\n🏆 {league}\n\n@futboltestjanal\n#{home_tag} #{away_tag}",
]

def make_tag(name):
    return name.replace(" ", "").replace("-", "").replace(".", "")

async def send_post(text):
    try:
        await bot.send_message(CHANNEL_ID, text)
        log.info(f"Post yuborildi: {text[:50]}...")
    except Exception as e:
        log.error(f"Xato: {e}")

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
        home_score = goals.get('home', 0)
        away_score = goals.get('away', 0)
        status = fixture.get('status', {}).get('short', '')
        league_name = league.get('name', 'Futbol')

        start_key = f"start_{match_id}"
        if status == '1H' and start_key not in sent_events:
            sent_events.add(start_key)
            tpl = random.choice(MATCH_START_TEMPLATES)
            await send_post(tpl.format(home=home, away=away, league=league_name,
                home_tag=make_tag(home), away_tag=make_tag(away)))
            await asyncio.sleep(2)

        for event in events:
            if event.get('type') == 'Goal':
                player = event.get('player', {}).get('name', 'Noma\'lum')
                team = event.get('team', {}).get('name', home)
                minute = event.get('time', {}).get('elapsed', 0)
                extra = event.get('time', {}).get('extra', 0)
                key = f"goal_{match_id}_{player}_{minute}"
                if key not in sent_events:
                    sent_events.add(key)
                    min_str = f"{minute}+{extra}" if extra else str(minute)
                    tpl = random.choice(GOAL_TEMPLATES)
                    msg = tpl.format(player=player, team=team, minute=min_str,
                        team_tag=make_tag(team), league_tag=make_tag(league_name))
                    msg += f"\n\n📊 Hisob: {home} {home_score}—{away_score} {away}"
                    await send_post(msg)
                    await asyncio.sleep(2)

        end_key = f"end_{match_id}"
        if status in ['FT', 'AET', 'PEN'] and end_key not in sent_events:
            sent_events.add(end_key)
            tpl = random.choice(MATCH_END_TEMPLATES)
            await send_post(tpl.format(home=home, away=away, home_score=home_score,
                away_score=away_score, league=league_name,
                home_tag=make_tag(home), away_tag=make_tag(away)))
            await asyncio.sleep(2)

demo_done = False
async def demo():
    global demo_done
    if demo_done:
        return
    demo_done = True
    await asyncio.sleep(3)
    await send_post("✅ FUTBOL BOT ISHGA TUSHDI!\n\n🤖 @futboltestjanal kanalining AI agentiman!\n\n⚽ Gollar\n🔄 Transferlar\n📰 Yangiliklar\n📊 Natijalar\n\nObuna bo'ling! 🚀")
    await asyncio.sleep(4)
    tpl = random.choice(GOAL_TEMPLATES)
    await send_post(tpl.format(player="Kylian Mbappé", team="Real Madrid", minute="73",
        team_tag="RealMadrid", league_tag="LaLiga") + "\n\n📊 Hisob: Real Madrid 2—1 Barcelona")
    await asyncio.sleep(4)
    tpl = random.choice(TRANSFER_TEMPLATES)
    await send_post(tpl.format(player="Erling Haaland", from_club="Man City", to_club="Real Madrid", fee="€200M"))

async def main_loop():
    log.info("Bot ishga tushdi!")
    async with aiohttp.ClientSession() as session:
        if not FOOTBALL_API_KEY:
            await demo()
        news_counter = 0
        while True:
            try:
                if FOOTBALL_API_KEY:
                    await monitor(session)
                    news_counter += 1
                    if news_counter >= 10:
                        items = await get_news(session)
                        for item in items[:2]:
                            sent_events.add(item['id'])
                            await send_post(f"📰 {item['title']}\n\n{item['desc']}\n\n#Futbol #Yangilik")
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
