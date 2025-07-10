# debug_parser.py
import re
from bs4 import BeautifulSoup

# --- Вспомогательная функция, скопированная из проекта ---
def find_value_by_label(search_area, label_text):
    if not search_area: return None
    try:
        candidates = search_area.find_all(lambda tag: tag.name == 'td' and label_text in tag.get_text(strip=True) and not tag.find('td'))
        if not candidates: return None
        label_td = candidates[-1]
        value_td = label_td.find_next_sibling('td')
        if not value_td: value_td = label_td.find_next('td')
        if value_td:
            link = value_td.find('a')
            return link.get_text(strip=True) if link else value_td.get_text(strip=True)
        return None
    except Exception as e:
        print(f"!!! Ошибка в find_value_by_label для '{label_text}': {e}")
        return None

# --- Имя проблемного файла ---
# Убедитесь, что этот файл лежит в папке 'reports'
problem_file = 'reports/Асташенко.htm' 

# --- Основная логика отладки ---
print(f"--- НАЧИНАЮ ОТЛАДКУ ФАЙЛА: {problem_file} ---")

try:
    with open(problem_file, 'r', encoding='windows-1251', errors='ignore') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    print("\n[ЭТАП 1] Поиск заголовков детальных секций ОЗУ...")
    
    # Используем ТОЧНО ТАКОЕ ЖЕ регулярное выражение, как в основной программе
    ram_headers = soup.find_all('td', class_='dt', text=re.compile(r'\[\s*(Устройства памяти|SPD)\s*/'))
    
    if not ram_headers:
        print("!!! КРИТИЧЕСКАЯ ОШИБКА: Не найдено НИ ОДНОГО заголовка ОЗУ. Проверьте регулярное выражение.")
    else:
        print(f"УСПЕХ! Найдено заголовков: {len(ram_headers)}")

    print("\n[ЭТАП 2] Перебор найденных заголовков и попытка извлечь данные...")
    
    found_any_data = False
    for i, header in enumerate(ram_headers, 1):
        print(f"\n--- Обработка заголовка #{i} ---")
        print(f"Текст заголовка: {header.get_text(strip=True)}")
        
        info_table = header.find_next('table')
        
        if not info_table:
            print("!!! ОШИБКА: Не найдена таблица (<table>) после этого заголовка.")
            continue
            
        print("Таблица после заголовка найдена. Пытаюсь извлечь 'Размер'...")
        
        module_size = find_value_by_label(info_table, 'Размер')
        
        if module_size and module_size.strip():
            print(f"УСПЕХ! Найден размер: {module_size.strip()}")
            found_any_data = True
        else:
            print("!!! ОШИБКА: Не удалось найти значение для поля 'Размер' в этой таблице.")
            print("--- HTML-код этой таблицы для анализа: ---")
            print(info_table.prettify())
            print("----------------------------------------")

    print("\n[ЭТАП 3] Финальный результат")
    if found_any_data:
        print("ОТЛАДКА ЗАВЕРШЕНА: Данные были найдены, но, возможно, не попали в финальный список.")
    else:
        print("ОТЛАДКА ЗАВЕРШЕНА: Данные не были извлечены. Проверьте ошибки на ЭТАПЕ 2.")

except FileNotFoundError:
    print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: Файл '{problem_file}' не найден. Убедитесь, что он существует.")
except Exception as e:
    print(f"!!! ПРОИЗОШЛА НЕПРЕДВИДЕННАЯ ОШИБКА: {e}")