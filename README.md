# NVR Merger 

Сервис для создания склеек видео различных форматов

## Принцип работы

При запуске сервис подключается к очереди RabbitMQ. Он начинает слушать канал очереди 'on_merge'. По этому каналу в него поступает информация, необходимая для склейки. Когда сообщение прочитывается, создается класс `Merger`, который нужен для выполнения дальнейшей работы. В нём происходит идентификация видео, требуемых для склейки, их загрузка. После загрузки необходимых видео начинается работа по монтажу итогового видео: обрезание, конкатенация, склеевание. После монтажа происходит загрузка итогового видео на облачное хранилище. Все оставшиеся в файловой системе видео удаляются. Затем сервис добавляет в исходное сообщение поле со ссылкой на видео в облачном хранилище и посылает это сообщение в очередь 'on_publish'. Дальнейшая обраотка просиходит в модуле https://git.miem.hse.ru/nvr/publisher


## Структура 

* **main.py** - главный класс приложения, в нём реализовано взаимодействие с очередями. Этот класс в отдельном треде вызывает функцию, которая начнет главный процесс

* ***Cообщение для склейки*** должно содержать следующие поля: `organization_id, room_name, start_point, end_point, video_purpose, merge_type, publishing, email`  

* **merge.py** - содержит функции создания склейки из входных данных
(дата склейки, времена начала и конца, название комнаты etc.). Обработка
видеозаписей осуществляется при помощи инструмента FFmpeg.

* **calendarAPI.py** - содержит функции для взаимодействия с Google Calendar API.

* **driveAPI.py** - содержит функции для взаимодействия с Google Drive API.

* **requirements.txt** - список Python-библиотек, необходимых для работы 
приложения. Получается при помощи команды `pip freeze > requirements.txt`. 
Библиотеки устанавливаются в окружение при помощи команды 
`pip install -r requirements.txt`. 

* **Dockerfile** - файл конфигурации для Docker-образа приложения. 
Для сборки используется базовый образ `python:3`.

* **run_docker.sh** - shell-скрипт для запуска приложения на сервере. 
Останавливает и удаляет все предыдущие запущенные образы приложения, 
собирает новый образ и запускает используя файл окружения `.env`, который 
необходимо создать и разместить в директории приложения.

Также в корневой директории проекта должна находится папка creds, содержащая два файла creds.json и tokenDrive.pickle. Эти два файла должны обеспечивать работу с GoogleAPI
* **.env** - структура файла выглядит следующим образом
```
RABBITMQ_PASSWORD=
RABBITMQ_NAME=
RABBITMQ_HOST=
RABBITMQ_PORT=
NVR_API_KEY=
TOKEN_PATH=
CREDS_PATH=
LOGURU_LEVEL=
```

## Развертывание на сервере

```bash
git clone https://git.miem.hse.ru/nvr/merger.git
#добавление файлов .env, creds/creds.json, creds/tokenDrive.pickle
sudo ./run_docker.sh
```

## Авторы

[Сергей Войлов](https://github.com/whyslove),
[Даниил Мирталибов](https://github.com/Mint2702)

