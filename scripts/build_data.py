#!/usr/bin/env python3
"""VR NEXUS: собирает data/games.json и data/games-data.js из источников.

Источники (по приоритету полей):
  1. sources/manual/*.json  - ваши ручные записи (не перезаписываются)
  2. data/seeds.json        - стартовый список названий
  3. Steam                  - поиск VR-игр по тегу + описания, жанры, год, рейтинг, обложки
  4. RAWG (по желанию)      - обложки и платформы Quest / PS VR2 (нужен бесплатный ключ RAWG_KEY)

Запуск:  python scripts/build_data.py            (нужен интернет)
         python scripts/build_data.py --offline  (только склейка локальных файлов)
"""
import argparse, glob, html, json, os, re, sys, time
import urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEAM = os.environ.get('STEAM_BASE', 'https://store.steampowered.com')
RAWG = os.environ.get('RAWG_BASE', 'https://api.rawg.io/api')
RAWG_KEY = os.environ.get('RAWG_KEY', '')
DELAY = float(os.environ.get('DELAY', '1.2'))  # пауза между запросами к Steam, сек
CACHE_PATH = os.path.join(ROOT, 'data', 'cache.json')

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
    while len(ids) < limit:
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
    return ids[:limit]


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
            for g in d.get('results', []):
                e = rawg_pack(g)
                e['platforms'] = sorted(set(e['platforms']) | {plat})
                out.append(e)
            time.sleep(0.3)
    return out


# ---------- сборка ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true', help='не ходить в интернет')
    ap.add_argument('--limit', type=int, default=300, help='сколько VR-игр брать из Steam (по отзывам)')
    ap.add_argument('--no-discover', action='store_true', help='только дополнить уже известные игры')
    ap.add_argument('--refresh', action='store_true', help='игнорировать кэш')
    ap.add_argument('--rawg-pages', type=int, default=5)
    a = ap.parse_args()

    cache = {} if a.refresh else load_json(CACHE_PATH, {})
    games = {}  # norm(title) -> entry

    def add(e, manual=False):
        key = norm_loose(e['title'])
        cur = games.get(key)
        if not cur:
            games[key] = dict(e, _manual=manual)
            return games[key]
        for f, v in e.items():  # более приоритетный источник добавляется раньше, дополняем пустое
            if f == 'platforms':
                cur[f] = sorted(set(cur.get(f, [])) | set(v))
            elif not cur.get(f):
                cur[f] = v
        return cur

    for p in sorted(glob.glob(os.path.join(ROOT, 'sources', 'manual', '*.json'))):
        for e in load_json(p, []):
            add(e, manual=True)
    for e in load_json(os.path.join(ROOT, 'data', 'seeds.json'), []):
        add(e)
    log(f'Локально: {len(games)} игр')

    if not a.offline:
        steam_ids = []
        if not a.no_discover:
            log(f'Steam: ищу VR-игры (топ {a.limit} по отзывам)...')
            steam_ids = steam_discover(a.limit)
            log(f'  найдено {len(steam_ids)}')
        by_app = {str(e.get('app')): e for e in games.values() if e.get('app')}
        # 1) известные игры без app: ищем в Steam по названию
        for e in list(games.values()):
            if not e.get('app'):
                app = steam_find(e['title'], cache)
                if app:
                    e['app'] = str(app)
                    by_app[str(app)] = e
        # 2) новые игры из обзора Steam
        for app in steam_ids:
            if str(app) not in by_app:
                d = steam_details(app, cache)
                if d and d['name']:
                    by_app[str(app)] = add({'title': d['name'], 'platforms': ['steam'], 'app': str(app)})
        # 3) детали и рейтинг
        n = len(by_app)
        for i, (app, e) in enumerate(list(by_app.items()), 1):
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
            if d['desc'] and (not e.get('desc') or not e['_manual']):
                e['desc'] = d['desc']
            if d['year'] and (not e.get('year') or not e['_manual']):
                e['year'] = d['year']
            if d['genres'] and not e.get('_seed_genres') and not e.get('genres'):
                e['genres'] = d['genres']
            if not e['_manual'] or not e.get('rating'):
                r = steam_rating(app, cache) or (round(d['meta'] / 10, 1) if d.get('meta') else None)
                if r:
                    e['rating'] = str(r)
        # 4) RAWG: обложки и Quest / PS VR2
        if RAWG_KEY:
            log('RAWG: обложки и платформы...')
            for e in list(games.values()):
                if not e.get('app'):
                    r = rawg_find(e['title'], cache)
                    if r:
                        if r['image']:
                            e['image'] = e.get('image') or r['image']
                        if r['rating'] and not e.get('rating'):
                            e['rating'] = str(r['rating'])
                        e['platforms'] = sorted(set(e.get('platforms', [])) | set(r['platforms']))
            for r in rawg_discover(a.rawg_pages, cache):
                if r['name']:
                    add({'title': r['name'], 'year': r['year'], 'platforms': r['platforms'], 'image': r['image'],
                         'rating': str(r['rating']) if r['rating'] else ''})
        else:
            log('RAWG_KEY не задан: обложки Quest/PS-эксклюзивов пропускаю (ключ бесплатный на rawg.io/apidocs)')
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)

    out = []
    for e in games.values():
        e.pop('_manual', None)
        e.pop('_seed_genres', None)
        e['genres'] = e.get('genres') or ['action']
        e['platforms'] = e.get('platforms') or ['steam']
        e['year'] = e.get('year') or 0
        if not e.get('desc'):
            e['desc'] = f"{', '.join(GL.get(g, g) for g in e['genres'])}" + (f", {e['year']} год." if e['year'] else '.')
        out.append({k: v for k, v in e.items() if v not in ('', None)})
    out.sort(key=lambda g: (-float(g.get('rating') or 0), g['title'].lower()))

    data_dir = os.path.join(ROOT, 'data')
    with open(os.path.join(data_dir, 'games.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(os.path.join(data_dir, 'games-data.js'), 'w', encoding='utf-8') as f:
        f.write('window.GAMES_DATA = ' + json.dumps(out, ensure_ascii=False) + ';\n')
    log(f'Готово: {len(out)} игр, из них с Steam ID: {sum(1 for g in out if g.get("app"))}, '
        f'с картинкой: {sum(1 for g in out if g.get("app") or g.get("image"))}')


if __name__ == '__main__':
    main()
