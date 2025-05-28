// Функция для переключения темы
function toggleTheme() {
    const body = document.body;
    body.classList.toggle('dark');
    // Сохраняем состояние темы в localStorage
    localStorage.setItem('theme', body.classList.contains('dark') ? 'dark' : 'light');
}

// Функция для применения темы при загрузке страницы
function applyTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark');
    }
}

// Применяем тему при загрузке страницы
document.addEventListener('DOMContentLoaded', applyTheme);