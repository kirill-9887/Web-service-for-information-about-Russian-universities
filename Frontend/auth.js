// Функция для обновления кнопок авторизации на всех страницах
function updateAuthUI() {
    const loginBtn = document.getElementById('loginBtn');
    const registerBtn = document.getElementById('registerBtn');
    const profileBtn = document.getElementById('profileBtn');
    const logoutBtn = document.getElementById('logoutBtn');

    if ("${auth_username}") {
        if (loginBtn) loginBtn.style.display = 'none';
        if (registerBtn) registerBtn.style.display = 'none';
        if (profileBtn) {
            profileBtn.style.display = 'inline';
            profileBtn.textContent = `Профиль ("${auth_username}")`;
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
    const new_password = document.getElementById('regPassword').value.trim();
    const repeated_password = document.getElementById('regRepeatedPassword').value.trim();
    const name = document.getElementById('regName').value.trim();
    const surname = document.getElementById('regSurname').value.trim();
    const patronymic = document.getElementById('regPatronymic').value.trim();

    if (!username || !new_password) {
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
            "new_password": new_password,
            "repeated_password": repeated_password,
            "name": name,
            "surname": surname,
            "patronymic": patronymic,
        })
    })
    .then(response => response.json())
    .then(response => {
        if (response.detail) {
            alert(`${'${response.detail}'}`);
        } else {
            closeModal('registerModal');
            location.reload();
        }
    });
}

// Функция для создания нового пользователя (для админ-панели)
function createUser() {
    const username = document.getElementById('createUsername').value.trim();
    const name = document.getElementById('createName').value.trim();
    const surname = document.getElementById('createSurname').value.trim();
    const patronymic = document.getElementById('createPatronymic').value.trim();
    const access_level = document.getElementById('createRole').value;

    if (!username || !name || !surname || !access_level) {
        alert('Заполните все обязательные поля: username, имя, фамилия, пароль и уровень доступа');
        return;
    }

    fetch('/users/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            "username": username,
            "name": name,
            "surname": surname,
            "patronymic": patronymic,
            "access_level": access_level
        })
    })
    .then(response => response.json())
    .then(response => {
        if (response.detail) {
            alert(`${'${response.detail}'}`);
        } else {
            document.getElementById('authURL').value = response.url;
            document.getElementById('authURLModal').style.display = 'flex';
            // Очистка формы
            document.getElementById('createUsername').value = '';
            document.getElementById('createName').value = '';
            document.getElementById('createSurname').value = '';
            document.getElementById('createPatronymic').value = '';
            document.getElementById('createRole').value = '';
        }
    });
}

// Функция для копирования пароля
function copyAuthURL() {
    const authURLField = document.getElementById('authURL');
    authURLField.select();
    document.execCommand('copy');
    alert('Ссылка скопирована в буфер обмена');
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
            alert(`${'${response.detail}'}`);
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
    alert(`Редактировать пользователя: ${'${username}'}`);
    // Здесь можно добавить fetch-запрос для получения данных пользователя
}

// Функция для удаления пользователя
function deleteUser(username) {
    if (confirm(`Удалить пользователя ${'${username}'}?`)) {
        fetch(`/users/delete/${'${username}'}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(response => {
            if (response.detail) {
                alert(`${'${response.detail}'}`);
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
    } else if (modalId === 'authURLModal') {
        document.getElementById('authURL').value = '';
        location.reload();
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

function applyRole(username, accessLevel) {
    fetch('/set_rights', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            "username": username,
            "new_access_level": parseInt(accessLevel, 10),
        })
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401) {
                alert('Необходима авторизация');
            }
            else if (response.status === 400) {
                alert('Укажите корректный username пользователя');
            }
        } else {
            alert('Роль назначена');
            location.reload();
        }
    })
}

// Инициализация UI при загрузке страницы
document.addEventListener('DOMContentLoaded', updateAuthUI);
updateAuthUI();