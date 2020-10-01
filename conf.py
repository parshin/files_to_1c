# -*- coding: utf-8 -*-
# настройки. Этот файл добавляем в git ignore

# адреса http-сервисов для доступа к 1с
addresses = {
    "upload_file_address": "http://XXX.XXX.XXX.XXX/BASE/hs/URL/",
}

# каталоги с файлами
files_dir = {
    "FOLDER": "PATH_TO_FOLDER", # Откуда будем читать файлы.
    "RECOGNIZED": "PATH_TO_RECOGNIZED", # Сюда переместим те, которые распознались и загрузились в 1С. Но их удалять надо.
    "UNRECOGNIZED": "PATH_TO_UNRECOGNIZED", # Сюда переместим нераспознанные.
}


