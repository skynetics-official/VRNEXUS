document.addEventListener('DOMContentLoaded', async () => {
    const PK = { steam: 'steam', quest: 'quest', psvr2: 'psvr2' };
    const GK = { action: 'action', sandbox: 'sandbox', shooter: 'shooter', horror: 'horror', rhythm: 'rhythm', adventure: 'adventure', sim: 'sim', sport: 'sport', puzzle: 'puzzle', strategy: 'strategy', social: 'social', rpg: 'rpg', racing: 'racing' };
    const GL = { action: 'Экшен', sandbox: 'Песочница', shooter: 'Шутер', horror: 'Хоррор', rhythm: 'Ритм-игра', adventure: 'Приключение', sim: 'Симулятор', sport: 'Спорт', puzzle: 'Головоломка', strategy: 'Стратегия', social: 'Социальная', rpg: 'RPG', racing: 'Гонки' };
    const PL = { steam: ['fa-steam', 'SteamVR'], quest: ['fa-meta', 'Quest'], psvr2: ['fa-playstation', 'PS VR2'] };

    let games = [];

    // Данные собираются скриптом scripts/build_data.py в data/games.json и data/games-data.js.
    // games-data.js подключён в index.html, поэтому сайт работает даже при открытии файла двойным кликом.
    let rawGames = Array.isArray(window.GAMES_DATA) ? window.GAMES_DATA : null;
    if (!rawGames) {
        try {
            const res = await fetch('data/games.json');
            rawGames = res.ok ? await res.json() : [];
        } catch (err) {
            console.error('Не удалось загрузить data/games.json:', err);
            rawGames = [];
        }
    }

    // Убираем дубликаты по названию
    const seen = new Set();
    rawGames.forEach(g => {
        const key = (g.title || '').toLowerCase();
        if (!key || seen.has(key)) return;
        seen.add(key);
        games.push({
            id: games.length,
            title: g.title,
            year: g.year || '—',
            genres: g.genres || ['action'],
            platforms: g.platforms || ['steam'],
            rating: g.rating || '',
            app: g.app || '',
            image: g.image || '',
            storeUrl: g.storeUrl || '',
            desc: g.desc || 'Описание игры отсутствует.'
        });
    });

    if (!games.length) {
        document.getElementById('count').textContent = 'Нет данных: запустите python scripts/build_data.py или откройте сайт через локальный сервер.';
        return;
    }
    initApp();

    function initApp() {
        const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
        const hue = s => { let x = 0; for(const c of s) x = (x*31 + c.charCodeAt(0))%360; return x; };
        const ini = t => t.replace(/[^A-Za-z0-9а-яА-ЯёЁ ]/g, '').split(' ').filter(Boolean).slice(0,3).map(w => w[0]).join('').toUpperCase();
        
        // Генерация обложки (если нет Steam ID — берем красивый градиент с инициалами)
        function getCoverImg(g) {
            if (g.app && /^\d+$/.test(g.app)) {
                return `https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/${g.app}/header.jpg`;
            }
            return g.image || '';
        }

        function renderCover(g, boxClass) {
            const a = hue(g.title);
            const imgUrl = getCoverImg(g);
            return `
                <div class="${boxClass} flex items-center justify-center" style="background: linear-gradient(135deg, hsl(${a} 40% 46%), hsl(${(a+50)%360} 40% 32%));">
                    <span class="font-display text-3xl font-extrabold text-white/90 select-none">${ini(g.title)}</span>
                    ${imgUrl ? `<img src="${imgUrl}" alt="${esc(g.title)}" loading="lazy" onerror="this.remove()">` : ''}
                </div>`;
        }

        const platTags = g => g.platforms.map(p => `<span class="flex items-center gap-1 text-[11px] font-semibold text-gray-200 bg-white/10 px-2 py-1 rounded-md"><i class="fa-brands ${PL[p]?.[0] || 'fa-gamepad'}"></i> ${PL[p]?.[1] || p}</span>`).join('');
        const genreTags = g => g.genres.map(x => `<span class="text-xs px-2.5 py-0.5 rounded-full bg-vr-accent2/15 text-vr-accent2">${GL[x] || x}</span>`).join('');
        const badge = g => g.rating ? `<div class="absolute top-2 right-2 z-10 bg-black/60 backdrop-blur-md text-vr-accent1 font-bold px-2 py-1 rounded-lg text-sm shadow"><i class="fa-solid fa-star text-xs"></i> ${g.rating}</div>` : '';

        function card(g) {
            return `
                <div class="game-card group bg-vr-card rounded-2xl border border-white/10 flex flex-col h-full overflow-hidden" data-id="${g.id}">
                    <div class="relative">${renderCover(g, 'game-image-box')}${badge(g)}</div>
                    <div class="p-5 flex flex-col flex-grow">
                        <h3 class="font-display text-lg font-extrabold mb-2 group-hover:text-vr-accent1 transition-colors line-clamp-1">${esc(g.title)}</h3>
                        <div class="flex flex-wrap gap-1.5 mb-3">${platTags(g)}</div>
                        <div class="flex flex-wrap gap-1.5 mb-3">${genreTags(g)}</div>
                        <p class="text-gray-400 text-sm mb-5 flex-grow line-clamp-3">${esc(g.desc)}</p>
                        <button class="w-full bg-white/10 hover:bg-vr-accent2 hover:text-vr-dark font-bold py-2 px-4 rounded-xl transition flex items-center justify-center gap-2">Подробнее <i class="fa-solid fa-arrow-right"></i></button>
                    </div>
                </div>`;
        }

        // Модальное окно
        const modal = document.getElementById('modal');
        const modalBody = document.getElementById('modalBody');

        function openModal(id) {
            const g = games[id];
            if (!g) return;
            const q = encodeURIComponent(g.title);
            
            // Определяем куда вести по кнопке покупки
            let storeLink = g.storeUrl;
            let storeName = 'Магазин';
            let storeIcon = 'fa-store';
            
            if (g.app) {
                storeLink = `https://store.steampowered.com/app/${g.app}`;
                storeName = 'Steam';
                storeIcon = 'fa-steam';
            } else if (!storeLink) {
                storeLink = `https://www.google.com/search?q=${q}+VR+game+buy`;
                storeName = 'Найти в сети';
                storeIcon = 'fa-globe';
            }

            modalBody.innerHTML = `
                ${renderCover(g, 'modal-image-box')}
                <div class="p-6">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <h2 class="font-display text-2xl font-extrabold">${esc(g.title)}</h2>
                        ${g.rating ? `<div class="text-vr-accent1 font-bold shrink-0 text-lg"><i class="fa-solid fa-star text-xs"></i> ${g.rating}</div>` : ''}
                    </div>
                    <p class="text-gray-400 text-sm mb-4">Год релиза: ${g.year}</p>
                    <div class="flex flex-wrap gap-1.5 mb-3">${platTags(g)}</div>
                    <div class="flex flex-wrap gap-1.5 mb-4">${genreTags(g)}</div>
                    <p class="text-gray-200 mb-6 leading-relaxed">${esc(g.desc)}</p>
                    <div class="flex flex-wrap gap-3">
                        <a href="${storeLink}" target="_blank" rel="noopener" class="bg-vr-accent2 text-vr-dark font-bold py-2.5 px-6 rounded-xl hover:brightness-110 transition flex items-center gap-2"><i class="fa-brands ${storeIcon}"></i> ${storeName}</a>
                        <a href="https://www.youtube.com/results?search_query=${q}+VR+trailer" target="_blank" rel="noopener" class="bg-white/10 font-bold py-2.5 px-6 rounded-xl hover:bg-white/20 transition flex items-center gap-2"><i class="fa-brands fa-youtube"></i> Трейлер</a>
                    </div>
                </div>`;
            modal.classList.replace('hidden', 'flex');
            document.body.style.overflow = 'hidden';
        }

        function closeModal() {
            modal.classList.replace('flex', 'hidden');
            document.body.style.overflow = '';
        }

        // Рендер кнопок жанров
        const usedGenres = Object.keys(GL).filter(k => games.some(g => g.genres.includes(k)));
        document.getElementById('filterContainer').innerHTML = [['all', 'Все жанры'], ...usedGenres.map(k => [k, GL[k]])].map(([k, l]) =>
            `<button class="filter-btn px-4 py-1.5 rounded-full border border-white/15 text-sm font-semibold text-gray-300 transition hover:border-vr-accent2 ${k === 'all' ? 'active' : ''}" data-filter="${k}">${l}</button>`
        ).join('');

        const filterBtns = document.querySelectorAll('.filter-btn');
        filterBtns.forEach(b => b.onclick = () => {
            filterBtns.forEach(x => x.classList.remove('active'));
            b.classList.add('active');
            currentFilter = b.dataset.filter;
            render();
        });

        let currentFilter = 'all', currentPlatform = 'all', searchQuery = '';

        function render() {
            const q = searchQuery.toLowerCase();
            const filtered = games.filter(g => {
                const matchQ = !q || g.title.toLowerCase().includes(q);
                const matchF = currentFilter === 'all' || g.genres.includes(currentFilter);
                const matchP = currentPlatform === 'all' || g.platforms.includes(currentPlatform);
                return matchQ && matchF && matchP;
            });

            document.getElementById('count').textContent = `Найдено игр: ${filtered.length} из ${games.length}`;
            document.getElementById('gamesGrid').innerHTML = filtered.map(card).join('');
            document.getElementById('noResults').classList.toggle('hidden', filtered.length > 0);
        }

        document.getElementById('searchInput').oninput = e => { searchQuery = e.target.value; render(); };
        document.getElementById('platformSelect').onchange = e => { currentPlatform = e.target.value; render(); };
        document.getElementById('gamesGrid').onclick = e => {
            const cardEl = e.target.closest('[data-id]');
            if (cardEl) openModal(+cardEl.dataset.id);
        };
        document.getElementById('randomBtn').onclick = () => {
            if (games.length > 0) openModal(Math.floor(Math.random() * games.length));
        };
        document.getElementById('modalClose').onclick = closeModal;
        modal.onclick = e => { if (e.target === modal) closeModal(); };
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

        render();
    }
});
