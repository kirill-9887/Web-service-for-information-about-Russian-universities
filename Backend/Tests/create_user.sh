#!/bin/bash

echo "TEST Создание пользователя от имени администратора - OK"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname2", "name": "Ivan", "surname": "Ivanov", "patronymic": "Ivanovich", "access_level": 2}' http://localhost:8000/users/create
echo
