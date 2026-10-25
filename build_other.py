#!/usr/bin/env python3
"""VR NEXUS: пополняет pc.json (Steam), а также switch/ps5/xbox.json (RAWG, нужен RAWG_KEY).
Использует функции из build_data.py. Заполняет только ПУСТЫЕ поля, ваши правки не трогает.
Запуск: python build_other.py [--pc-limit 600] [--switch-pages 10] [--max-minutes 40]"""
import argparse, json, re, time
import build_data as b

RAWG_GENRES = {'action': 'action', 'adventure': 'adventure', 'role-playing-games-rpg': 'rpg', 'shooter': 'shooter',
               'puzzle': 'puzzle', 'racing': 'racing', 'sports': 'sport', 'strategy': 'strategy', 'simulation': 'sim',
               'platformer': 'action', 'fighting': 'action', 'arcade': 'action', 'massively-multiplayer': 'social'}


def load(path):
    out = {}
    for e in b.load_json(b.ROOT + '/' + path, []):
        out[b.norm_loose(e['title'])] = e
    return out


def save(path, d):
    rows = []
    for e in d.values():
        e['genres'] = e.get('genres') or ['action']
        rows.append({k: v for k, v in e.items() if v not in ('', None, 0)})
    rows.sort(key=lambda g: (-float(g.get('rating') or 0), g['title'].lower()))
    with open(b.ROOT + '/' + path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    b.log(f'{path}: {len(rows)} игр')


def pc_discover(limit):
    ids, start = [], 0
    while len(ids) < limit and start < 25000:  # без тега VR: обычные игры, по числу отзывов
        body = b.fetch(f'{b.STEAM}/search/results/?query=&start={start}&count=50&sort_by=Reviews_DESC'
                       f'&category1=998&cc=us&l=english&json=1&infinite=1')
        if not body:
            break
        try:
            body = json.loads(body).get('results_html', '')
        except ValueError:
            pass
        new = [i for i in re.findall(r'data-ds-appid="(\d+)"', body) if i not in ids]
        if not new:
            break
        ids += new
        start += 50
        time.sleep(b.DELAY)
    return ids[:limit]


def do_pc(a, cache, over):
    games = load('pc.json')
    by_app = {str(e['app']): e for e in games.values() if e.get('app')}
    for app in pc_discover(a.pc_limit):
        if over():
            break
        if app not in by_app:
            d = b.steam_details(app, cache)
            if d and d['name'] and b.norm_loose(d['name']) not in games:
                e = games[b.norm_loose(d['name'])] = {'title': d['name'], 'platforms': ['pc'], 'app': app}
                by_app[app] = e
    for app, e in list(by_app.items()):
        if over():
            break
        d = b.steam_details(app, cache)
        if not d or not b.names_match(d['name'], e['title']):
            b.log(f'  ! ID {app} не совпадает с "{e["title"]}", пропускаю')
            continue
        e['desc'] = e.get('desc') or d['desc']
        e['year'] = e.get('year') or d['year']
        e['genres'] = e.get('genres') or d['genres']
        if not e.get('rating'):
            r = b.steam_rating(app, cache) or (round(d['meta'] / 10, 1) if d.get('meta') else None)
            e['rating'] = str(r) if r else ''
    save('pc.json', games)


def do_rawg(a, cache, over, key, pid):
    games = load(key + '.json')
    if not b.RAWG_KEY:
        b.log(f'RAWG_KEY не задан: {key}.json остаётся как есть (без обложек и новых игр)')
        return save(key + '.json', games)
    def pack(g):
        m = re.search(r'(19|20)\d{2}', g.get('released') or '')
        gen = []
        for x in g.get('genres') or []:
            v = RAWG_GENRES.get(x.get('slug'))
            if v and v not in gen:
                gen.append(v)
        return {'title': g.get('name', ''), 'image': g.get('background_image') or '', 'genres': gen,
                'rating': str(round(g['rating'] * 2, 1)) if g.get('rating') else '', 'year': int(m.group(0)) if m else None,
                'platforms': [key]}
    def merge(p):
        k = b.norm_loose(p['title'])
        cur = games.setdefault(k, p) if p['title'] else None
        if cur is not p and cur:
            for f, v in p.items():
                if f != 'platforms' and not cur.get(f):
                    cur[f] = v
    for page in range(1, a.switch_pages + 1):  # ID платформ в RAWG: Switch 7, PS5 187, Xbox Series 186
        if over():
            break
        d = b.jfetch(f'{b.RAWG}/games?key={b.RAWG_KEY}&platforms={pid}&ordering=-rating&page_size=40&page={page}') or {}
        if not d.get('results'):
            break
        for g in d['results']:
            merge(pack(g))
        time.sleep(0.3)
    for e in games.values():  # обложки для игр из стартового списка
        if over():
            break
        if not e.get('image'):
            k = f'rawgs:{key}:' + b.norm(e['title'])
            if k not in cache:
                q = b.urllib.parse.quote(e['title'])
                d = b.jfetch(f'{b.RAWG}/games?key={b.RAWG_KEY}&search={q}&platforms={pid}&search_precise=true&page_size=5') or {}
                hit = next((g for g in d.get('results', []) if b.norm_loose(g.get('name', '')) == b.norm_loose(e['title'])), None)
                cache[k] = pack(hit) if hit else None
                time.sleep(0.3)
            r = cache[k]
            if r:
                for f in ('image', 'rating', 'year'):
                    e[f] = e.get(f) or r[f]
    save(key + '.json', games)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pc-limit', type=int, default=600)
    ap.add_argument('--switch-pages', type=int, default=8)
    ap.add_argument('--max-minutes', type=int, default=0)
    ap.add_argument('--only', choices=['pc', 'switch', 'ps5', 'xbox'])
    a = ap.parse_args()
    cache = b.load_json(b.CACHE_PATH, {})
    end = time.time() + a.max_minutes * 60 if a.max_minutes else None
    over = lambda: bool(end and time.time() > end)
    try:
        if a.only != 'switch':
            do_pc(a, cache, over)
        for key, pid in (('switch', 7), ('ps5', 187), ('xbox', 186)):
            if a.only in (None, key):
                do_rawg(a, cache, over, key, pid)
    finally:
        with open(b.CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)


if __name__ == '__main__':
    main()
