import asyncio
import logging
import os
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw
from aiogram import Bot, Dispatcher
from aiogram.types import BufferedInputFile
import xml.etree.ElementTree as ET

BOT_TOKEN = "8797652661:AAGHA6BZCf5mNVdxT-5CahP8XmJQ8OKlWFo"
CHANNEL_ID = os.getenv("CHANNEL_ID", "@futboltestjanal")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
CHECK_INTERVAL = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
sent_events = set()

# ✅ FAQAT MASHHUR LIGALAR
ALLOWED_LEAGUES = {
    39: "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League",
    140: "🇪🇸 La Liga",
    78: "🇩🇪 Bundesliga",
    135: "🇮🇹 Serie A",
    61: "🇫🇷 Ligue 1",
    2: "🏆 Champions League",
    3: "🏆 Europa League",
    848: "🏆 Conference League",
    1: "🌍 Jahon Chempionati",
    4: "🌍 EURO",
    307: "🇸🇦 Saudi Pro League",
    960: "🇺🇿 O'zbekiston terma jamoasi",
}

async def download_bytes(url, session):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status == 200:
                return await r.read()
    except:
        pass
    return None

async def make_banner(home, away, home_logo_url, away_logo_url, league, score_home=None, score_away=None, session=None):
    try:
        W, H = 800, 420
        img = Image.new("RGB", (W, H), color=(10, 15, 30))
        draw = ImageDraw.Draw(img)

        for y in range(H):
            r = int(10 + (y/H)*15)
            g = int(15 + (y/H)*25)
            b = int(30 + (y/H)*50)
            draw.line([(0,y),(W,y)], fill=(r,g,b))

        draw.rectangle([0, H-10, W, H], fill=(34, 197, 94))
        draw.rectangle([0, H-12, W, H-10], fill=(22, 163, 74))

        if home_logo_url and session:
            data = await download_bytes(home_logo_url, session)
            if data:
                try:
                    logo = Image.open(BytesIO(data)).convert("RGBA").resize((160, 160))
                    img.paste(logo, (60, 90), logo)
                except: pass

        if away_logo_url and session:
            data = await download_bytes(away_logo_url, session)
            if data:
                try:
                    logo = Image.open(BytesIO(data)).convert("RGBA").resize((160, 160))
                    img.paste(logo, (580, 90), logo)
                except: pass

        draw.ellipse([320, 110, 480, 270], fill=(20, 30, 60), outline=(34, 197, 94), width=3)

        if score_home is not None and score_away is not None:
            draw.text((400, 175), f"{score_home}:{score_away}", fill=(255,255,255), anchor="mm")
            draw.text((400, 220), "YAKUNIY", fill=(134, 239, 172), anchor="mm")
        else:
            draw.text((400, 190), "VS", fill=(255,255,255), anchor="mm")

        draw.text((140, 275), (home[:14] if len(home)>14 else home), fill=(220,220,220), anchor="mm")
        draw.text((660, 275), (away[:14] if len(away)>14 else away), fill=(220,220,220), anchor="mm")

        draw.rectangle([100, 310, 700, 355], fill=(15, 50, 30))
        draw.text((400, 332), league[:40], fill=(134, 239, 172), anchor="mm")

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()
    except Exception as e:
        log.error(f"Banner xato: {e}")
        return None

def analyze_goal(event):
    detail = event.get('detail', '').lower()
    assist = event.get('assist', {}).get('name', '')
    
    if 'penalty' in detail:
        desc = "⚽ PENALTI GOL!"
        analysis = "Jarima nuqtasidan sovuqqonlik bilan!"
    elif 'own goal' in detail:
        desc = "😱 O'Z GOLI!"
        analysis = "Afsuski, o'z darvozasiga urdi!"
    elif 'free kick' in detail:
        desc = "🎯 ERKIN ZARBA — GOL!"
        analysis = "To'g'ridan-to'g'ri erkin zarbadan to'rni larzaga keltirdi!"
    elif 'header' in detail:
        desc = "✈️ BOSH BILAN GOL!"
        analysis = "Ajoyib uzatmani bosh bilan to'rga jo'natdi!"
    else:
        desc = "⚽ GOL!"
        analysis = "Ajoyib individual harakat natijasida!"
    
    assist_text = f"\n🎯 Assist: {assist}" if assist else ""
    return desc, analysis, assist_text

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

async def get_todays_schedule(session):
    if not FOOTBALL_API_KEY:
        return []
    try:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        results = []
        for league_id in ALLOWED_LEAGUES:
            url = f"https://v3.football.api-sports.io/fixtures?date={today}&league={league_id}&season=2025"
            headers = {"x-apisports-key": FOOTBALL_API_KEY}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                results.extend(data.get("response", []))
        return results
    except Exception as e:
        log.error(f"Jadval xato: {e}")
        return []

async def get_news(session):
    feeds = [
        ("https://feeds.bbci.co.uk/sport/football/rss.xml", "BBC Sport"),
        ("https://www.goal.com/feeds/en/news", "Goal.com"),
        ("https://www.uefa.com/rssfeed/news/", "UEFA"),
    ]
    items = []
    for url, source in feeds:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                text = await r.text()
            root = ET.fromstring(text)
            for item in root.findall('.//item')[:2]:
                title = item.findtext('title', '')
                desc = item.findtext('description', '')
                guid = item.findtext('guid', '')
                if guid and guid not in sent_events and title:
                    items.append({'id': guid, 'title': title, 'desc': desc[:180], 'source': source})
        except:
            continue
    return items[:3]

async def send_daily_schedule(session):
    matches = await get_todays_schedule(session)
    if not matches:
        return
    
    schedule_key = f"schedule_{__import__('datetime').datetime.now().strftime('%Y-%m-%d')}"
    if schedule_key in sent_events:
        return
    sent_events.add(schedule_key)
    
    text = "📅 BUGUNGI O'YINLAR JADVALI\n\n"
    for match in matches[:15]:
        teams = match.get('teams', {})
        fixture = match.get('fixture', {})
        league = match.get('league', {})
        home = teams.get('home', {}).get('name', '')
        away = teams.get('away', {}).get('name', '')
        time = fixture.get('date', '')[:16].replace('T', ' ')
        league_name = ALLOWED_LEAGUES.get(league.get('id'), '')
        if home and away and league_name:
            text += f"{league_name}\n⚽ {home} 🆚 {away}\n🕐 {time}\n\n"
    
    text += "👉 @futboltestjanal"
    await bot.send_message(CHANNEL_ID, text)

async def monitor(session):
    matches = await get_live_matches(session)
    for match in matches:
        league = match.get('league', {})
        league_id = league.get('id')

        # ✅ Faqat mashhur ligalar
        if league_id not in ALLOWED_LEAGUES:
            continue

        fixture = match.get('fixture', {})
        teams = match.get('teams', {})
        goals = match.get('goals', {})
        events = match.get('events', [])
        match_id = fixture.get('id')
        home = teams.get('home', {}).get('name', '')
        away = teams.get('away', {}).get('name', '')
        home_logo = teams.get('home', {}).get('logo')
        away_logo = teams.get('away', {}).get('logo')
        home_score = goals.get('home', 0) or 0
        away_score = goals.get('away', 0) or 0
        status = fixture.get('status', {}).get('short', '')
        league_name = ALLOWED_LEAGUES[league_id]

        # Match boshlandi
        start_key = f"start_{match_id}"
        if status == '1H' and start_key not in sent_events:
            sent_events.add(start_key)
            caption = f"🏟️ MATCH BOSHLANDI!\n\n⚽ {home} 🆚 {away}\n{league_name}\n\nLive kuzating! 👁️\n\n👉 @futboltestjanal"
            img = await make_banner(home, away, home_logo, away_logo, league_name, session=session)
            if img:
                await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(img, "match.png"), caption=caption)
            else:
                await bot.send_message(CHANNEL_ID, caption)
            await asyncio.sleep(2)

        # Gollar
        home_goals_count = 0
        away_goals_count = 0
        for event in events:
            if event.get('type') == 'Goal':
                detail = event.get('detail', '').lower()
                if 'own goal' not in detail:
                    team_id = event.get('team', {}).get('id')
                    if team_id == teams.get('home', {}).get('id'):
                        home_goals_count += 1
                    else:
                        away_goals_count += 1
                else:
                    team_id = event.get('team', {}).get('id')
                    if team_id == teams.get('home', {}).get('id'):
                        away_goals_count += 1
                    else:
                        home_goals_count += 1

                player = event.get('player', {}).get('name', '') or "O'yinchi"
                team = event.get('team', {}).get('name', home)
                minute = event.get('time', {}).get('elapsed', 0)
                extra = event.get('time', {}).get('extra', 0)
                min_str = f"{minute}+{extra}" if extra else str(minute)

                key = f"goal_{match_id}_{player}_{minute}"
                if key not in sent_events:
                    sent_events.add(key)
                    desc, analysis, assist_text = analyze_goal(event)
                    
                    caption = (
                        f"{desc} {min_str}'\n\n"
                        f"🏃 {player} ({team})\n"
                        f"{analysis}{assist_text}\n\n"
                        f"📊 Hisob: {home} {home_goals_count}—{away_goals_count} {away}\n"
                        f"{league_name}\n\n"
                        f"👉 @futboltestjanal"
                    )
                    img = await make_banner(
                        home, away, home_logo, away_logo, league_name,
                        score_home=home_goals_count, score_away=away_goals_count, session=session
                    )
                    if img:
                        await bot.send_photo(CHANNEL_ID, photo=BufferedInputFile(img, "goal.png"), caption=caption)
                    else:
                        await bot.send_message(CHANNEL_ID, caption)
                    await asyncio.sleep(2)

        # Sariq kartochka
        for event in events:
            if event.get('type') == 'Card' and event.get('detail') == 'Yellow Card':
                player = event.get('player', {}).get('name', '') or "O'yinchi"
                team = event.get('team', {}).get('name', '')
                minute = event.get('time', {}).get('elapsed', 0)
                key = f"yellow_{match_id}_{player}_{minute}"
                if key not in sent_events:
                    sent_events.add(key)
                    await bot.send_message(CHANNEL_ID,
                        f"🟨 SARIQ KARTOCHKA! {minute}'\n\n"
                        f"👤 {player} ({team})\n"
                        f"⚽ {home} {home_score}—{away_score} {away}\n\n"
                        f"👉 @futboltestjanal"
                    )
                    await asyncio.sleep(1)

        # Qizil kartochka
        for event in events:
            if event.get('type') == 'Card' and event.get('detail') == 'Red Card':
                player = event.get('player', {}).get('name', '') or "O'yinchi"
                team = event.get('team', {}).get('name', '')
                minute = event.get('time', {}).get('elapsed', 0)
                key = f"red_{match_id}_{player}_{minute}"
                if key not in sent_events:
                    sent_events.add(key)
                    await bot.send_message(CHANNEL_ID,
                        f"🟥 QIZIL KARTOCHKA! {minute}'\n\n"
                        f"👤 {player} ({team}) — MAYDONDAN CHIQARILDI!\n"
                        f"⚽ {home} {home_score}—{away_score} {away}\n\n"
                        f"👉 @futboltestjanal"
                    )
                    await asyncio.sleep(1)

        # Match tugadi
        end_key = f"end_{match_id}"
        if status in ['FT', 'AET', 'PEN'] and end_key not in sent_events:
            sent_events.add(end_key)
            if status == 'AET':
                extra_text = "🔄 Qo'shimcha vaqtdan keyin!"
            elif status == 'PEN':
                extra_text = "🎯 Penaltilar serisidan keyin!"
            else:
                extra_text = ""
            
            caption = (
                f"🏁 YAKUNIY NATIJA!\n\n"
                f"🏆 {league_name}\n"
                f"⚽ {home} {home_score} — {away_score} {away}\n"
                f"{extra_text}\n\n"
                f"👉 @futboltestjanal"
            )
            img = await make_banner(
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
        news_counter = 0
        schedule_sent = False
        
        while True:
            try:
                from datetime import datetime
                hour = datetime.now().hour

                # Ertalab 8:00 da jadval
                if hour == 8 and not schedule_sent:
                    await send_daily_schedule(session)
                    schedule_sent = True
                elif hour != 8:
                    schedule_sent = False

                # Live matchlar
                await monitor(session)

                # Har 15 daqiqada yangiliklar
                news_counter += 1
                if news_counter >= 15:
                    items = await get_news(session)
                    for item in items:
                        sent_events.add(item['id'])
                        msg = (
                            f"📰 {item['title']}\n\n"
                            f"{item['desc']}\n\n"
                            f"📡 {item['source']}\n"
                            f"👉 @futboltestjanal"
                        )
                        await bot.send_message(CHANNEL_ID, msg)
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
