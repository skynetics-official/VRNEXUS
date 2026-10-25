// Общий скрипт для pc.html и switch.html: данные берутся из data-src, платформа из data-plat
document.addEventListener('DOMContentLoaded', async () => {
    const $ = id => document.getElementById(id);
    const SRC = document.body.dataset.src, PLAT = document.body.dataset.plat;
    const GL = { action: 'Экшен', sandbox: 'Песочница', shooter: 'Шутер', horror: 'Хоррор', rhythm: 'Ритм-игра', adventure: 'Приключение', sim: 'Симулятор', sport: 'Спорт', puzzle: 'Головоломка', strategy: 'Стратегия', social: 'Социальная', rpg: 'RPG', racing: 'Гонки' };
    const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    const hue = s => { let x = 0; for (const c of s) x = (x * 31 + c.charCodeAt(0)) % 360; return x; };
    const ini = t => t.replace(/[^A-Za-z0-9а-яА-ЯёЁ ]/g, '').split(' ').filter(Boolean).slice(0, 3).map(w => w[0]).join('').toUpperCase();

    let raw = [];
    try { const r = await fetch(SRC, { cache: 'no-cache' }); raw = r.ok ? await r.json() : []; } catch (e) { console.error(e); }
    const seen = new Set(), games = [];
    raw.forEach(g => {
        const k = (g.title || '').toLowerCase();
        if (!k || seen.has(k)) return;
        seen.add(k);
        const genres = g.genres || ['action'];
        games.push({ ...g, id: games.length, genres, desc: g.desc || genres.map(x => GL[x] || x).join(', ') + (g.year ? ', ' + g.year + ' год.' : '.') });
    });
    if (!games.length) { $('count').textContent = 'Не удалось загрузить ' + SRC + '. Откройте сайт по ссылке GitHub Pages.'; return; }

    const cover = (g, cls) => {
        const a = hue(g.title);
        const url = (g.app && /^\d+$/.test(g.app)) ? `https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/${g.app}/header.jpg` : (g.image || '');
        return `<div class="${cls} flex items-center justify-center" style="background:linear-gradient(135deg,hsl(${a} 40% 46%),hsl(${(a + 50) % 360} 40% 32%))">
            <span class="font-display text-3xl font-extrabold text-white/90 select-none">${ini(g.title)}</span>
            ${url ? `<img src="${url}" alt="${esc(g.title)}" loading="lazy" onerror="this.remove()">` : ''}</div>`;
    };
    const genreTags = g => g.genres.map(x => `<span class="text-xs px-2.5 py-0.5 rounded-full bg-vr-accent2/15 text-vr-accent2">${GL[x] || x}</span>`).join('');
    const badge = g => g.rating ? `<div class="absolute top-2 right-2 z-10 bg-black/60 backdrop-blur-md text-vr-accent1 font-bold px-2 py-1 rounded-lg text-sm shadow"><i class="fa-solid fa-star text-xs"></i> ${g.rating}</div>` : '';
    const card = g => `
        <div class="game-card group bg-vr-card rounded-2xl border border-white/10 flex flex-col h-full overflow-hidden" data-id="${g.id}">
            <div class="relative">${cover(g, 'game-image-box')}${badge(g)}</div>
            <div class="p-5 flex flex-col flex-grow">
                <h3 class="font-display text-lg font-extrabold mb-2 group-hover:text-vr-accent1 transition-colors line-clamp-1">${esc(g.title)}</h3>
                <div class="flex flex-wrap gap-1.5 mb-3">${genreTags(g)}</div>
                <p class="text-gray-400 text-sm mb-5 flex-grow line-clamp-3">${esc(g.desc)}</p>
                <button class="w-full bg-white/10 hover:bg-vr-accent2 hover:text-vr-dark font-bold py-2 px-4 rounded-xl transition flex items-center justify-center gap-2">Подробнее <i class="fa-solid fa-arrow-right"></i></button>
            </div>
        </div>`;

    // Модальное окно
    const modal = $('modal');
    let closeTimer = null;
    function openModal(id) {
        const g = games[id], q = encodeURIComponent(g.title);
        const SHOP = {
            pc: [{ n: 'Steam', i: 'fa-brands fa-steam', h: g.app ? `https://store.steampowered.com/app/${g.app}` : `https://store.steampowered.com/search/?term=${q}` },
                 { n: 'GOG', i: 'fa-solid fa-store', h: `https://www.gog.com/en/games?query=${q}` }],
            ps5: [{ n: 'PlayStation Store', i: 'fa-brands fa-playstation', h: `https://store.playstation.com/en-us/search/${q}` }],
            xbox: [{ n: 'Xbox Store', i: 'fa-solid fa-store', h: `https://www.xbox.com/en-US/search?q=${q}` }],
            switch: [{ n: 'Nintendo eShop', i: 'fa-solid fa-store', h: g.storeUrl || `https://www.nintendo.com/us/search/?q=${q}` }]
        };
        const stores = SHOP[PLAT] || SHOP.pc;
        $('modalBody').innerHTML = `
            ${cover(g, 'modal-image-box')}
            <div class="p-6">
                <div class="flex items-start justify-between gap-4 mb-3">
                    <h2 class="font-display text-2xl font-extrabold">${esc(g.title)}</h2>
                    ${g.rating ? `<div class="text-vr-accent1 font-bold shrink-0 text-lg"><i class="fa-solid fa-star text-xs"></i> ${g.rating}</div>` : ''}
                </div>
                <p class="text-gray-400 text-sm mb-4">Год релиза: ${g.year || '—'}</p>
                <div class="flex flex-wrap gap-1.5 mb-4">${genreTags(g)}</div>
                <p class="text-gray-200 mb-6 leading-relaxed">${esc(g.desc)}</p>
                <div class="flex flex-wrap gap-3">
                    ${stores.map(s => `<a href="${s.h}" target="_blank" rel="noopener" class="bg-vr-accent2 text-vr-dark font-bold py-2.5 px-5 rounded-xl hover:brightness-110 transition flex items-center gap-2"><i class="${s.i}"></i> ${s.n}</a>`).join('')}
                    <a href="https://www.youtube.com/results?search_query=${q}+trailer" target="_blank" rel="noopener" class="bg-white/10 font-bold py-2.5 px-6 rounded-xl hover:bg-white/20 transition flex items-center gap-2"><i class="fa-brands fa-youtube"></i> Трейлер</a>
                </div>
            </div>`;
        clearTimeout(closeTimer);
        modal.classList.remove('closing');
        modal.classList.replace('hidden', 'flex');
        document.body.style.overflow = 'hidden';
    }
    function closeModal() {
        if (modal.classList.contains('hidden') || modal.classList.contains('closing')) return;
        modal.classList.add('closing');
        closeTimer = setTimeout(() => { modal.classList.remove('closing'); modal.classList.replace('flex', 'hidden'); document.body.style.overflow = ''; }, 220);
    }

    // Фильтры, сортировка, поиск
    const used = Object.keys(GL).filter(k => games.some(g => g.genres.includes(k)));
    $('filterContainer').innerHTML = [['all', 'Все жанры'], ...used.map(k => [k, GL[k]])].map(([k, l]) =>
        `<button class="filter-btn px-4 py-1.5 rounded-full border border-white/15 text-sm font-semibold text-gray-300 transition hover:border-vr-accent2 ${k === 'all' ? 'active' : ''}" data-filter="${k}">${l}</button>`).join('');
    let genre = 'all', query = '', sort = 'rating', shown = 48, last = [];
    const PAGE = 48;
    document.querySelectorAll('.filter-btn').forEach(b => b.onclick = () => {
        document.querySelectorAll('.filter-btn').forEach(x => x.classList.remove('active'));
        b.classList.add('active'); genre = b.dataset.filter; render();
    });
    const moreBtn = document.createElement('button');
    moreBtn.className = 'hidden mx-auto mt-8 block bg-white/10 hover:bg-vr-accent2 hover:text-vr-dark font-bold py-3 px-10 rounded-full transition';
    $('gamesGrid').after(moreBtn);
    moreBtn.onclick = () => { shown += PAGE; render(true); };

    const sorters = {
        rating: (a, b) => (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0) || a.title.localeCompare(b.title),
        year: (a, b) => (b.year || 0) - (a.year || 0) || a.title.localeCompare(b.title),
        name: (a, b) => a.title.localeCompare(b.title)
    };
    function render(keep) {
        if (!keep) shown = PAGE;
        const q = query.toLowerCase();
        last = games.filter(g => (!q || g.title.toLowerCase().includes(q)) && (genre === 'all' || g.genres.includes(genre))).sort(sorters[sort]);
        $('count').textContent = `Найдено игр: ${last.length} из ${games.length}`;
        $('gamesGrid').innerHTML = last.slice(0, shown).map(card).join('');
        moreBtn.classList.toggle('hidden', last.length <= shown);
        moreBtn.textContent = `Показать ещё (${last.length - shown})`;
        $('noResults').classList.toggle('hidden', last.length > 0);
    }
    $('searchInput').oninput = e => { query = e.target.value; render(); };
    $('sortSelect').onchange = e => { sort = e.target.value; render(); };
    $('gamesGrid').onclick = e => { const c = e.target.closest('[data-id]'); if (c) openModal(+c.dataset.id); };
    $('randomBtn').onclick = e => {
        const btn = e.currentTarget, icon = btn.querySelector('i'), pool = last.length ? last : games;
        if (btn.disabled) return;
        btn.disabled = true; icon.classList.add('fa-spin');
        setTimeout(() => { icon.classList.remove('fa-spin'); btn.disabled = false; openModal(pool[Math.floor(Math.random() * pool.length)].id); }, 450);
    };
    $('modalClose').onclick = closeModal;
    modal.onclick = e => { if (e.target === modal) closeModal(); };
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
    render();
});
