#!/bin/bash

echo "TEST Отсутствует поле name - BAD"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "surname": "Ivanov", "patronymic": "Ivanovich", password: "pass1234"}' http://localhost:8000/register
echo

echo "TEST Поле name пустое - BAD"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "name": "", "surname": "Ivanov", "patronymic": "Ivanovich", "password": "pass1234"}' http://localhost:8000/register
echo

echo "TEST Поле name содержит символы кроме букв - BAD"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "name": "Ivan123", "surname": "Ivanov", "patronymic": "Ivanovich", "password": "pass1234"}' http://localhost:8000/register
echo

echo "TEST Нет поля password - BAD"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "name": "Ivan", "surname": "Ivanov", "patronymic": "Ivanovich"}' http://localhost:8000/register
echo

echo "TEST Пустой пароль - BAD"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "name": "Ivan", "surname": "Ivanov", "patronymic": "Ivanovich", "password": ""}' http://localhost:8000/register
echo

echo "TEST Пароль слишком короткий - BAD"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "name": "Ivan", "surname": "Ivanov", "patronymic": "Ivanovich", "password": "pass"}' http://localhost:8000/register
echo

echo "TEST Пароль содержит кириллицу - BAD"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "name": "Ivan", "surname": "Ivanov", "patronymic": "Ivanovich", "password": "passМойПароль"}' http://localhost:8000/register
echo

echo "TEST Пароль содержит пробел - BAD"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "name": "Ivan", "surname": "Ivanov", "patronymic": "Ivanovich", "password": "my pass1233"}' http://localhost:8000/register
echo

echo "TEST Корректные данные - OK"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "name": "Ivan", "surname": "Ivanov", "patronymic": "Ivanovich", "password": "Pass1234-!_"}' http://localhost:8000/register
echo

echo "TEST Повторная регистрация (повторный username) - BAD"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname", "name": "Nikolay", "surname": "Nikolayev", "patronymic": "Nikolayevich", "password": "somepassword"}' http://localhost:8000/register
echo

echo "TEST Корректные данные, пароль совпадает с паролем у nickname - OK, ожидание различных хешей"
curl -X POST -H "Content-Type: application/json" -d '{"username": "nickname_2", "name": "Nikolay", "surname": "Nikolayev", "patronymic": "Nikolayevich", "password": "Pass1234-!_"}' http://localhost:8000/register
echo
