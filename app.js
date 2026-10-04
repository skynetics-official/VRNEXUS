document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('gamesGrid');
    const searchInput = document.getElementById('searchInput');
    const platformFilter = document.getElementById('platformFilter');
    
    // Элементы модального окна
    const modal = document.getElementById('gameModal');
    const closeBtn = document.querySelector('.close-btn');
    
    let gamesData = []; // Сюда загрузим игры из JSON

    // Загрузка данных из games.json
    fetch('games.json')
        .then(response => response.json())
        .then(data => {
            gamesData = data;
            renderGames(gamesData);
        })
        .catch(error => {
            console.error('Ошибка загрузки данных:', error);
            grid.innerHTML = '<p>Не удалось загрузить список игр. Проверьте файл games.json</p>';
        });

    // Функция отрисовки карточек
    function renderGames(games) {
        grid.innerHTML = '';
        
        if (games.length === 0) {
            grid.innerHTML = '<p>По вашему запросу игр не найдено.</p>';
            return;
        }

        games.forEach(game => {
            const card = document.createElement('div');
            card.className = 'game-card';
            
            // Генерируем теги платформ
            const platformsHtml = game.platforms.map(p => `<span class="platform-tag">${p}</span>`).join('');

            card.innerHTML = `
                <div class="image-container">
                    <img src="${game.image}" alt="${game.title}" class="card-image" loading="lazy">
                </div>
                <div class="card-content">
                    <h3 class="card-title">${game.title}</h3>
                    <div class="platforms">${platformsHtml}</div>
                    <button class="btn" onclick="openModal('${game.id}')">Подробнее</button>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    // Фильтрация и поиск
    function filterGames() {
        const query = searchInput.value.toLowerCase();
        const platform = platformFilter.value;

        const filtered = gamesData.filter(game => {
            const matchesSearch = game.title.toLowerCase().includes(query);
            const matchesPlatform = platform === 'all' || game.platforms.includes(platform);
            return matchesSearch && matchesPlatform;
        });

        renderGames(filtered);
    }

    searchInput.addEventListener('input', filterGames);
    platformFilter.addEventListener('change', filterGames);

    // Функция открытия модального окна (сделана глобальной, чтобы работать из onClick)
    window.openModal = function(id) {
        const game = gamesData.find(g => g.id === id);
        if (!game) return;

        document.getElementById('modalImage').src = game.image;
        document.getElementById('modalTitle').textContent = game.title;
        document.getElementById('modalDescription').textContent = game.description;
        document.getElementById('modalTags').textContent = game.tags.join(' • ');

        modal.classList.add('active');
    };

    // Закрытие модального окна
    closeBtn.addEventListener('click', () => {
        modal.classList.remove('active');
    });

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
    });
});
