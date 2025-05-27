// Функция для обновления кнопок авторизации на всех страницах
function updateAuthUI() {
    const loginBtn = document.getElementById('loginBtn');
    const registerBtn = document.getElementById('registerBtn');
    const profileBtn = document.getElementById('profileBtn');
    const logoutBtn = document.getElementById('logoutBtn');

    if (auth_username) {
        if (loginBtn) loginBtn.style.display = 'none';
        if (registerBtn) registerBtn.style.display = 'none';
        if (profileBtn) {
            profileBtn.style.display = 'inline';
            profileBtn.textContent = `Профиль (${auth_username})`;
        }
        if (logoutBtn) logoutBtn.style.display = 'inline';
    } else {
        if (loginBtn) loginBtn.style.display = 'inline';
        if (registerBtn) registerBtn.style.display = 'inline';
        if (profileBtn) profileBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'none';
    }
}

// Функция для регистрации
function register() {
    const username = document.getElementById('regUsername').value.trim();
    const password = document.getElementById('regPassword').value.trim();
    const name = document.getElementById('regName').value.trim();
    const surname = document.getElementById('regSurname').value.trim();
    const patronymic = document.getElementById('regPatronymic').value.trim();

    if (!username || !password) {
        alert('Введите логин и пароль');
        return;
    }

    fetch('/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            "username": username,
            "password": password,
            "name": name,
            "surname": surname,
            "patronymic": patronymic,
        })
    })
    .then(response => response.json())
    .then(response => {
        if (response.detail) {
            alert(`${response.detail}`);
        } else {
            auth_username = username;
            closeModal('registerModal');
            updateAuthUI();
        }
    });
}

// Функция для создания нового пользователя (для админ-панели)
function createUser() {
    const username = document.getElementById('createUsername').value.trim();
    const name = document.getElementById('createName').value.trim();
    const surname = document.getElementById('createSurname').value.trim();
    const patronymic = document.getElementById('createPatronymic').value.trim();
    const password = document.getElementById('createPassword').value.trim();
    const role = document.getElementById('createRole').value;

    if (!username || !name || !surname || !password || !role) {
        alert('Заполните все обязательные поля: username, имя, фамилия, пароль и уровень доступа');
        return;
    }

    fetch('/create_user', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            "username": username,
            "name": name,
            "surname": surname,
            "patronymic": patronymic,
            "password": password,
            "role": role
        })
    })
    .then(response => response.json())
    .then(response => {
        if (response.detail) {
            alert(`${response.detail}`);
        } else {
            document.getElementById('generatedPassword').value = response.password || password; // Используем сгенерированный пароль или введенный
            document.getElementById('passwordModal').style.display = 'flex';
            // Очистка формы
            document.getElementById('createUsername').value = '';
            document.getElementById('createName').value = '';
            document.getElementById('createSurname').value = '';
            document.getElementById('createPatronymic').value = '';
            document.getElementById('createPassword').value = '';
            document.getElementById('createRole').value = '';
        }
    });
}

// Функция для копирования пароля
function copyPassword() {
    const passwordField = document.getElementById('generatedPassword');
    passwordField.select();
    document.execCommand('copy');
    alert('Пароль скопирован в буфер обмена');
}

// Функция для входа
function login() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();

    if (!username || !password) {
        alert('Введите логин и пароль');
        return;
    }
    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            "username": username,
            "password": password,
        })
    })
    .then(response => response.json())
    .then(response => {
        if (response.detail) {
            alert(`${response.detail}`);
        } else {
            window.location.reload(true);
        }
    });
}

// Функция для выхода
function logout() {
    fetch('/logout', {
        method: 'POST',
    })
    .then(response => {
        if (window.location.pathname.includes('profile') ||
            window.location.pathname.includes('edit') ||
            window.location.pathname.includes('users')) {
            window.location.href = '/';
        } else {
            window.location.reload();
        }
    });
}

// Функция для редактирования пользователя
function editUser(username) {
    // Логика редактирования (например, открытие модального окна с формой)
    alert(`Редактировать пользователя: ${username}`);
    // Здесь можно добавить fetch-запрос для получения данных пользователя
}

// Функция для удаления пользователя
function deleteUser(username) {
    if (confirm(`Удалить пользователя ${username}?`)) {
        fetch(`/delete_user/${username}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(response => {
            if (response.detail) {
                alert(`${response.detail}`);
            } else {
                location.reload(); // Перезагрузка страницы после удаления
            }
        });
    }
}

// Функция для закрытия модального окна
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    
    // Очистка полей в зависимости от модального окна
    if (modalId === 'loginModal') {
        document.getElementById('loginUsername').value = '';
        document.getElementById('loginPassword').value = '';
    } else if (modalId === 'registerModal') {
        document.getElementById('regUsername').value = '';
        document.getElementById('regPassword').value = '';
        document.getElementById('regName').value = '';
        document.getElementById('regSurname').value = '';
        document.getElementById('regPatronymic').value = '';
    } else if (modalId === 'passwordModal') {
        document.getElementById('generatedPassword').value = '';
    }
}

// Функция для показа модального окна
function showLogin() {
    document.getElementById('loginModal').style.display = 'flex';
}

function showRegister() {
    document.getElementById('registerModal').style.display = 'flex';
}

// Функция для обновления роли пользователя
function updateUserRole(select) {
    // Логика обновления роли (например, сохранение в скрытом поле или отправка на сервер)
    const role = select.value;
    // Здесь можно добавить fetch для сохранения роли
}

function applyRole() {
    // Логика применения роли (например, отправка на сервер)
    alert('Роль назначена');
}

// Инициализация UI при загрузке страницы
document.addEventListener('DOMContentLoaded', updateAuthUI);
updateAuthUI();
