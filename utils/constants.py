# utils/constants.py

HEADERS_MAIN = [
    'Название ПК', 'Имя файла', 'ОС', 'Процессор', 'Сокет',
    'Материнская плата', 'Видеоадаптер', 'Монитор', 'Принтеры', 'Объем ОЗУ',
    'Кол-во плашек ОЗУ', 'Свободно слотов ОЗУ', 'Модели плашек ОЗУ',
    'Дисковые накопители', 'SMART Статус', 'Дата BIOS', '_RAW_DATA'
    # 'Disk_C_Free_GB' <-- УДАЛЕНО
]
HEADERS_NETWORK = [
    'Название ПК', 'Имя файла', 'Локальный IP', 'MAC-адрес'
]
HEADERS_ANALYSIS = ['Имя файла', 'Название ПК', 'Ключевые проблемы', 'Рекомендация']
CRITICAL_SMART_ATTRIBUTES = {'05', 'C5', 'C6'}