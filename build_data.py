#!/usr/bin/env python3
"""VR NEXUS: дополняет games.json данными из Steam (и по желанию RAWG).

Один файл games.json - и список игр, и результат. Скрипт:
  - добавляет в него новые VR-игры из Steam (топ по отзывам);
  - заполняет ПУСТЫЕ поля у каждой игры: Steam ID (картинка), описание, жанры, год, рейтинг;
  - никогда не перезаписывает то, что уже заполнено (ваши правки в безопасности).
Свою игру добавьте в games.json вручную: {"title": "...", "platforms": ["quest"]}

Запуск: python build_data.py   (нужен интернет; --limit N, --no-discover, --refresh)
"""
import argparse, glob, html, json, os, re, sys, time
import urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
STEAM = os.environ.get('STEAM_BASE', 'https://store.steampowered.com')
RAWG = os.environ.get('RAWG_BASE', 'https://api.rawg.io/api')
RAWG_KEY = os.environ.get('RAWG_KEY', '')
DELAY = float(os.environ.get('DELAY', '1.2'))  # пауза между запросами к Steam, сек
CACHE_PATH = os.path.join(ROOT, '.cache.json')
GAMES_PATH = os.path.join(ROOT, 'games.json')

GL = {'action': 'Экшен', 'sandbox': 'Песочница', 'shooter': 'Шутер', 'horror': 'Хоррор', 'rhythm': 'Ритм-игра',
      'adventure': 'Приключение', 'sim': 'Симулятор', 'sport': 'Спорт', 'puzzle': 'Головоломка',
      'strategy': 'Стратегия', 'social': 'Социальная', 'rpg': 'RPG', 'racing': 'Гонки'}
STEAM_GENRES = {'1': 'action', '25': 'adventure', '3': 'rpg', '28': 'sim', '2': 'strategy', '9': 'racing',
                '18': 'sport', '29': 'rpg'}


def log(*a):
    print(*a, flush=True)


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 VRNEXUS-builder',
                                                       'Accept-Language': 'ru,en;q=0.8'})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            if e.code == 429:
                log('  Steam просит подождать (429), пауза 40 с...')
                time.sleep(40)
            elif e.code in (403, 404):
                return None
            else:
                time.sleep(3 * (i + 1))
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def jfetch(url):
    t = fetch(url)
    try:
        return json.loads(t) if t else None
    except ValueError:
        return None


def norm(t):
    return re.sub(r'[^a-z0-9а-яё]+', '', t.lower())


def norm_loose(t):
    n = norm(t)
    return re.sub(r'vr$', '', n)


def load_json(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


# ---------- Steam ----------
def steam_discover(limit):
    """Список appid VR-игр: страница поиска Steam по тегу VR, сортировка по отзывам."""
    ids, start = [], 0
    while (not limit or len(ids) < limit) and start < 25000:
        url = (f'{STEAM}/search/results/?query=&start={start}&count=50&sort_by=Reviews_DESC'
               f'&tags=21978&category1=998&cc=us&l=english&json=1&infinite=1')
        body = fetch(url)
        if not body:
            break
        try:
            body = json.loads(body).get('results_html', '')
        except ValueError:
            pass
        found = re.findall(r'data-ds-appid="(\d+)"', body)
        new = [i for i in found if i not in ids]
        if not new:
            break
        ids += new
        start += 50
        time.sleep(DELAY)
    return ids[:limit] if limit else ids


def steam_find(title, cache):
    k = 'search:' + norm(title)
    if k in cache:
        return cache[k]
    data = jfetch(f'{STEAM}/api/storesearch/?term={urllib.parse.quote(title)}&l=english&cc=us')
    app = 0
    items = [i for i in (data or {}).get('items', []) if i.get('type', 'app') == 'app']
    for pred in (lambda n: norm(n) == norm(title), lambda n: norm_loose(n) == norm_loose(title)):
        hit = next((i for i in items if pred(i.get('name', ''))), None)
        if hit:
            app = hit['id']
            break
    cache[k] = app
    time.sleep(DELAY)
    return app


def names_match(a, b):
    x, y = norm_loose(a), norm_loose(b)
    return bool(x and y) and (x == y or (len(min(x, y, key=len)) >= 4 and (x in y or y in x)))


def strip_html(s):
    return html.unescape(re.sub(r'<[^>]+>', ' ', s or '')).strip()


def steam_details(app, cache):
    k = 'app:' + str(app)
    if k in cache:
        return cache[k]
    raw = jfetch(f'{STEAM}/api/appdetails?appids={app}&l=russian&cc=us')
    d = ((raw or {}).get(str(app)) or {})
    out = None
    if d.get('success') and d.get('data', {}).get('type') == 'game':
        x = d['data']
        m = re.search(r'(19|20)\d{2}', (x.get('release_date') or {}).get('date', ''))
        genres = []
        for g in x.get('genres', []):
            v = STEAM_GENRES.get(str(g.get('id')))
            if v and v not in genres:
                genres.append(v)
        out = {'name': x.get('name', ''), 'desc': strip_html(x.get('short_description')),
               'year': int(m.group(0)) if m else None, 'genres': genres,
               'meta': (x.get('metacritic') or {}).get('score')}
    cache[k] = out
    time.sleep(DELAY)
    return out


def steam_rating(app, cache):
    k = 'rev:' + str(app)
    if k in cache:
        return cache[k]
    d = jfetch(f'{STEAM}/appreviews/{app}?json=1&language=all&purchase_type=all&num_per_page=0') or {}
    s = d.get('query_summary') or {}
    pos, neg = s.get('total_positive', 0), s.get('total_negative', 0)
    r = round(pos / (pos + neg) * 10, 1) if pos + neg >= 50 else None
    cache[k] = r
    time.sleep(DELAY)
    return r


# ---------- RAWG (необязательно) ----------
def rawg_vr_platforms(cache):
    if 'rawg:platforms' in cache:
        return cache['rawg:platforms']
    d = jfetch(f'{RAWG}/platforms?key={RAWG_KEY}&page_size=100') or {}
    res = {}
    for p in d.get('results', []):
        n = p.get('name', '')
        if 'VR2' in n:
            res[str(p['id'])] = 'psvr2'
        elif 'Quest' in n or 'Oculus' in n:
            res[str(p['id'])] = 'quest'
    cache['rawg:platforms'] = res
    return res


def rawg_pack(g):
    plats = set()
    for p in g.get('platforms') or []:
        n = (p.get('platform') or {}).get('name', '')
        if 'VR2' in n:
            plats.add('psvr2')
        elif 'Quest' in n or 'Oculus' in n:
            plats.add('quest')
    m = re.search(r'(19|20)\d{2}', g.get('released') or '')
    return {'name': g.get('name', ''), 'image': g.get('background_image') or '',
            'rating': round(g['rating'] * 2, 1) if g.get('rating') else None,
            'year': int(m.group(0)) if m else None, 'platforms': sorted(plats)}


def rawg_find(title, cache):
    k = 'rawgs:' + norm(title)
    if k not in cache:
        q = urllib.parse.quote(title)
        d = jfetch(f'{RAWG}/games?key={RAWG_KEY}&search={q}&search_precise=true&page_size=5') or {}
        hit = next((g for g in d.get('results', []) if norm_loose(g.get('name', '')) == norm_loose(title)), None)
        cache[k] = rawg_pack(hit) if hit else None
        time.sleep(0.3)
    return cache[k]


def rawg_discover(pages, cache):
    out = []
    for pid, plat in rawg_vr_platforms(cache).items():
        for page in range(1, pages + 1):
            d = jfetch(f'{RAWG}/games?key={RAWG_KEY}&platforms={pid}&ordering=-rating&page_size=40&page={page}') or {}
            if not d.get('results'):
                break
            for g in d.get('results', []):
                e = rawg_pack(g)
                e['platforms'] = sorted(set(e['platforms']) | {plat})
                out.append(e)
            time.sleep(0.3)
    return out


# ---------- сборка ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=300, help='сколько VR-игр брать из Steam (по отзывам), 0 = все')
    ap.add_argument('--max-minutes', type=int, default=0, help='остановить Steam-часть через N минут (продолжится при следующем запуске)')
    ap.add_argument('--no-discover', action='store_true', help='только дополнить уже известные игры')
    ap.add_argument('--refresh', action='store_true', help='игнорировать кэш')
    ap.add_argument('--rawg-pages', type=int, default=5)
    a = ap.parse_args()

    cache = {} if a.refresh else load_json(CACHE_PATH, {})
    deadline = time.time() + a.max_minutes * 60 if a.max_minutes else None

    def out_of_time():
        return bool(deadline and time.time() > deadline)

    games = {}  # norm(title) -> entry

    def add(e):
        k = norm_loose(e['title'])
        cur = games.get(k)
        if not cur:
            games[k] = e
            return e
        for f, v in e.items():  # дополняем только пустое
            if f == 'platforms':
                cur[f] = sorted(set(cur.get(f, [])) | set(v))
            elif not cur.get(f):
                cur[f] = v
        return cur

    for e in load_json(GAMES_PATH, []):
        add(e)
    log(f'В games.json: {len(games)} игр')

    steam_ids = []
    if not a.no_discover:
        log('Steam: ищу VR-игры (' + (f'топ {a.limit} по отзывам' if a.limit else 'все') + ')...')
        steam_ids = steam_discover(a.limit)
        log(f'  найдено {len(steam_ids)}')
    by_app = {str(e['app']): e for e in games.values() if e.get('app')}
    for e in list(games.values()):  # игры без Steam ID: ищем по названию
        if out_of_time():
            break
        if not e.get('app'):
            app = steam_find(e['title'], cache)
            if app:
                e['app'] = str(app)
                by_app[str(app)] = e
    for app in steam_ids:  # новые игры из топа Steam
        if out_of_time():
            log('Время вышло: остальное доберётся при следующем запуске')
            break
        if str(app) not in by_app:
            d = steam_details(app, cache)
            if d and d['name']:
                by_app[str(app)] = add({'title': d['name'], 'platforms': ['steam'], 'app': str(app)})

    n = len(by_app)
    for i, (app, e) in enumerate(list(by_app.items()), 1):
        if out_of_time():
            log('Время вышло: остальное доберётся при следующем запуске')
            break
        if i % 25 == 0:
            log(f'  Steam: {i}/{n}')
        d = steam_details(app, cache)
        if not d or not names_match(d['name'], e['title']):
            # неверный Steam ID (картинка чужой игры): ищем по названию заново
            log(f'  ! ID {app} не совпадает с "{e["title"]}", ищу заново')
            e.pop('app', None)
            new = steam_find(e['title'], cache)
            d = steam_details(new, cache) if new and str(new) != app else None
            if not d or not names_match(d['name'], e['title']):
                continue
            app = str(new)
            e['app'] = app
        if 'steam' not in e.get('platforms', []):
            e.setdefault('platforms', []).append('steam')
        if d['desc'] and not e.get('desc'):
            e['desc'] = d['desc']
        if d['year'] and not e.get('year'):
            e['year'] = d['year']
        if d['genres'] and not e.get('genres'):
            e['genres'] = d['genres']
        if not e.get('rating'):
            r = steam_rating(app, cache) or (round(d['meta'] / 10, 1) if d.get('meta') else None)
            if r:
                e['rating'] = str(r)

    if RAWG_KEY:  # обложки Quest / PS VR2 (ключ бесплатный: rawg.io/apidocs)
        log('RAWG: обложки и платформы...')
        for e in list(games.values()):
            if not e.get('app') and not e.get('image'):
                r = rawg_find(e['title'], cache)
                if r:
                    e['image'] = r['image'] or ''
                    if r['rating'] and not e.get('rating'):
                        e['rating'] = str(r['rating'])
                    e['platforms'] = sorted(set(e.get('platforms', [])) | set(r['platforms']))
        for r in rawg_discover(a.rawg_pages, cache):
            if r['name']:
                add({'title': r['name'], 'year': r['year'], 'platforms': r['platforms'], 'image': r['image'],
                     'rating': str(r['rating']) if r['rating'] else ''})
    else:
        log('RAWG_KEY не задан: у Quest/PS-эксклюзивов обложек не будет')

    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    out = []
    for e in games.values():
        e['genres'] = e.get('genres') or ['action']
        e['platforms'] = e.get('platforms') or ['steam']
        out.append({k: v for k, v in e.items() if v not in ('', None, 0)})
    out.sort(key=lambda g: (-float(g.get('rating') or 0), g['title'].lower()))
    with open(GAMES_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f'Готово: {len(out)} игр, с картинкой: {sum(1 for g in out if g.get("app") or g.get("image"))}')


if __name__ == '__main__':
    main()
