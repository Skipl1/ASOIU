#import "../../lib/lib.typ": *

// Настройка формата нумерации
#set figure(numbering: "1")


= Введение

*Цель лабораторной работы* — формирование практических навыков по развёртыванию распределённой клиент-серверной архитектуры, включающей Клиент-сервер, сервер приложений и сервер баз данных.

*Задачи*
1. Развернуть три виртуальные машины в среде виртуализации.
2. Настроить сетевое взаимодействие между виртуальными машинами.
3. Настроить веб-сервер.
4. Настроить сервер приложений.
5. Настроить сервер баз данных.
6. Проверить сетевую связность между всеми компонентами системы.

*Вариант*
#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  stroke: 0.5pt,
  inset: 8pt,
  [№], [Предметная область], [IP / порт], [Технологический стек],
  [11], [Учёт клиентов], [
    Web: 192.168.56.20:80
    App: 192.168.56.30:8010
    DB: 192.168.56.40:5432
  ], [
    Python
    FastAPI
    PostgreSQL
  ],
)

#pagebreak()


= 1. Настройка сетевого взаимодействия ВМ

Для организации связи между виртуальными машинами использовался сетевой адаптер типа *Host-Only Adapter* в VirtualBox.
#image("/assets/{FE1EE639-0508-4ADE-965C-23C6E3FA2C34}.png")

== 1.1 Конфигурация сетевых интерфейсов

На каждой ВМ была выполнена настройка статических IP-адресов через Netplan. Конфигурационный файл `/etc/netplan/50-cloud-init.yaml` приведён к следующему виду:

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: true
    enp0s8:
      addresses: 
        - 192.168.56.20/24
```

Аналогично настроены App Server (192.168.56.30) и Database Server (192.168.56.40).

После редактирования применено:
```bash
sudo netplan apply
```

#pagebreak()


= 2. Настройка Database Server (192.168.56.40)

На данном сервере развёрнута СУБД PostgreSQL для хранения данных.

== 2.1 Установка PostgreSQL

Выполнена установка PostgreSQL и дополнительных модулей:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

== 2.2 Настройка доступа

В файле `postgresql.conf` изменён параметр прослушиваемых адресов:
```yaml
listen_addresses = '*'
```

В файле `pg_hba.conf` добавлено правило, разрешающее подключение с App Server:
```yaml
host all all 192.168.56.30/32 md5
```

== 2.3 Создание базы данных и пользователя

В консоли PostgreSQL выполнены SQL-команды:
```sql
CREATE DATABASE clients_db;
CREATE USER app_user WITH ENCRYPTED PASSWORD 'secret_pass';
GRANT ALL PRIVILEGES ON DATABASE clients_db TO app_user;
```

После настройки сервис перезапущен:
```bash
sudo systemctl restart postgresql
```

#pagebreak()


= 3. Настройка App Server (192.168.56.30)

На сервере приложений развёрнуто веб-приложение на FastAPI с подключением к базе данных.

== 3.1 Установка зависимостей

Установлены Python, venv и необходимые библиотеки:
```bash
sudo apt install python3 python3-venv python3-pip libpq-dev
pip install fastapi uvicorn psycopg2
```

== 3.2 Разработка приложения

Создано приложение `main.py` с двумя эндпоинтами:

 "`/`" — возвращает приветственное сообщение
 
 "`/db-status`" — проверяет подключение к базе данных

```python
from fastapi import FastAPI
import psycopg2

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "From App Server"}

@app.get("/db-status")
def check_db():
    try:
        conn = psycopg2.connect(
            dbname="clients_db",
            user="app_user",
            password="secret_pass",
            host="192.168.56.40",
            port="5432"
        )
        conn.close()
        return {"status": "Success", "message": "Connected to DB!"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}
```

Запуск приложения выполнен командой:
```bash
uvicorn main:app --host 0.0.0.0 --port 8010
```

#pagebreak()


= 4. Настройка Web Server (192.168.56.20)

В качестве веб-сервера использован Nginx, который перенаправляет запросы на App Server.

== 4.1 Установка Nginx

```bash
sudo apt update
sudo apt install nginx
```

== 4.2 Настройка reverse proxy

Создан конфигурационный файл `/etc/nginx/sites-available/fastapi`:

```nginx
server {
    listen 80;
    server_name 192.168.56.20;

    location / {
        proxy_pass http://192.168.56.30:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Активация конфигурации:
```bash
sudo ln -s /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo systemctl restart nginx
```

#pagebreak()


= 5. Проверка работоспособности системы

Для проверки сетевого взаимодействия выполнены запросы с основной машины:

== 5.1 Проверка основного эндпоинта

```bash
curl http://192.168.56.20/
```

*Результат:*
```json
{"Hello": "From App Server"}
```

== 5.2 Проверка подключения к базе данных

```bash
curl http://192.168.56.20/db-status
```

*Результат:*
```json
{"status": "Success", "message": "Connected to DB!"}
```

Оба запроса успешно прошли через всю цепочку: Web Server → App Server → Database Server.

#pagebreak()


= Вывод

В ходе выполнения лабораторной работы было выполнено:

1. *Настроено сетевое взаимодействие* трёх виртуальных машин с использованием статических IP-адресов (192.168.56.20–40)

2. *Развёрнут Database Server* на базе PostgreSQL с настройкой удалённого доступа и созданием базы данных `clients_db`

3. *Разработано FastAPI-приложение* на App Server с эндпоинтами для проверки работоспособности и подключения к БД

4. *Настроен Web Server* на базе Nginx в качестве reverse proxy для перенаправления запросов на App Server

5. *Подтверждена работоспособность* всей системы через curl-запросы — все компоненты успешно взаимодействуют между собой

В результате получена функциональная трёхзвенная архитектура Web–App–Database с корректной маршрутизацией запросов.
