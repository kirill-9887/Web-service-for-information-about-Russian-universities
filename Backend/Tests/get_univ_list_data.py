from urllib.parse import quote_plus
import requests

print("TEST 1 Неправильный URL - BAD")
url = "http://localhost:8000/opendata/universities"
response = requests.get(url)
print(response.json())

print("TEST 2 Первая страница - OK")
url = "http://localhost:8000/opendata/universities?page=1"
response = requests.get(url)
print(response.json())

print("TEST 3 Вторая страница - OK")
url = "http://localhost:8000/opendata/universities?page=2"
response = requests.get(url)
print(response.json())

print("TEST 4 Фильтр по региону - OK")
url = f"http://localhost:8000/opendata/universities?page=1&region={quote_plus('г. Москва')}"
response = requests.get(url)
print(response.json())

print("TEST 5 Фильтр по названию - OK")
url = f"http://localhost:8000/opendata/universities?page=1&name={quote_plus('филиал')}"
response = requests.get(url)
print(response.json())

print("TEST 6 Фильтр по названию и региону - OK")
url = f"http://localhost:8000/opendata/universities?page=1&region={quote_plus('г. Москва')}&name={quote_plus('академия')}"
response = requests.get(url)
print(response.json())

print("TEST 7 Сортировка по региону по возрастанию - OK")
url = f"http://localhost:8000/opendata/universities?page=1&sort=region&sort=asc"
response = requests.get(url)
print(response.json())

print("TEST 8 Сортировка по названию по убыванию - OK")
url = f"http://localhost:8000/opendata/universities?page=1&sort=name&sort=desc"
response = requests.get(url)
print(response.json())

print("TEST 9 Сортировка по региону по возрастанию и после по названию по убыванию - OK")
url = f"http://localhost:8000/opendata/universities?page=1&sort=region&sort=asc&sort=name&sort=desc"
response = requests.get(url)
print(response.json())

print("TEST 10 Некорректный запрос страницы - BAD")
url = "http://localhost:8000/opendata/universities?page=-1"
response = requests.get(url)
print(response.json())

print("TEST 11 Некорректный запрос сортировки- BAD")
url = "http://localhost:8000/opendata/universities?page=1&sort=id"
response = requests.get(url)
print(response.json())
