# VR NEXUS

Каталог VR-игр. Данные собираются скриптом из Steam (и по желанию RAWG), руками писать игры не нужно.

## Что починено
- `app.js` искал файлы в `sources/…`, а JSON лежали в корне, поэтому игр не было вообще. Теперь сайт читает `data/games.json`.
- Добавлен `data/games-data.js`: сайт работает даже при открытии `index.html` двойным кликом (раньше `fetch` с `file://` блокировался браузером).
- Ваши `steam.json`, `quest.json`, `psvr.json` лежат в `sources/manual/` и имеют приоритет над автоданными.

## Обновить данные
```
python scripts/build_data.py            # нужен интернет, ~10-20 минут в первый раз
python scripts/build_data.py --offline  # только пересобрать из локальных файлов
```
Что делает скрипт: берёт топ VR-игр Steam по отзывам (по умолчанию 300, `--limit N`), ищет в Steam игры из `data/seeds.json`, подтягивает русское описание, жанры, год, рейтинг игроков (доля положительных отзывов ×10) и Steam ID для обложки. Результат кэшируется в `data/cache.json`.

Обложки Quest/PS VR2-эксклюзивов: получите бесплатный ключ на rawg.io/apidocs и запустите
`RAWG_KEY=ваш_ключ python scripts/build_data.py` (в Windows: `set RAWG_KEY=ваш_ключ`).

## Автообновление на GitHub
Файл `.github/workflows/update-data.yml` раз в неделю сам запускает сборку и коммитит данные. Ключ RAWG добавьте в Settings → Secrets → `RAWG_KEY` (необязательно). Для GitHub Pages включите Pages на ветке main.

## Свои игры
Добавляйте в `sources/manual/*.json` объекты вида `{"title": "...", "year": 2024, "genres": ["action"], "platforms": ["quest"], "image": "https://..."}`, потом запустите скрипт.
