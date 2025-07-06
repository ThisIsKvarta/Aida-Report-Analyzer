# debug_reader.py (v2 - Lightweight)
import os
from bs4 import BeautifulSoup

def main():
    """
    Скрипт для отладки, который извлекает ТОЛЬКО ПЕРВУЮ таблицу 
    из раздела "Суммарная информация" и сохраняет ее в текстовый файл.
    """
    print("-" * 40)
    print("--- ОБЛЕГЧЕННЫЙ ОТЛАДОЧНЫЙ СКРИПТ ---")
    print("-" * 40)

    default_input = os.path.join('reports', 'главврач.htm')
    input_html_file = input(f"Введите ПОЛНОЕ имя файла отчета (например, {default_input}): ")
    if not input_html_file:
        input_html_file = default_input

    if not os.path.exists(input_html_file):
        print(f"\nОШИБКА: Файл '{input_html_file}' не найден!")
        return

    output_txt_file = "debug_output.txt"
    print(f"Итоговый файл будет называться: {output_txt_file}")
    
    print(f"\n[1] Читаю файл: {input_html_file}")
    html_content = ""
    try:
        with open(input_html_file, 'r', encoding='windows-1251', errors='ignore') as f:
            html_content = f.read()
        encoding_used = 'windows-1251'
    except Exception:
        with open(input_html_file, 'r', encoding='latin-1', errors='ignore') as f:
            html_content = f.read()
        encoding_used = 'latin-1'

    print("\n[2] Парсинг и поиск нужной таблицы...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    summary_anchor = soup.find('a', {'name': 'summary'})
    if not summary_anchor:
        print("\nОШИБКА: Не могу найти якорь <a name=\"summary\"> в файле. Отчет поврежден или имеет другую структуру.")
        return

    # Находим ПЕРВУЮ таблицу после якоря. Это самое важное.
    summary_table = summary_anchor.find_next('table')
    
    if not summary_table:
        print("\nОШИБКА: Не могу найти таблицу после якоря <a name=\"summary\">.")
        return

    print("... Нужная таблица найдена!")
    
    print(f"\n[3] Сохранение кода таблицы в файл: {output_txt_file}")
    try:
        with open(output_txt_file, 'w', encoding='utf-8') as f:
            f.write(f"--- DEBUG OUTPUT FOR: {os.path.abspath(input_html_file)} ---\n")
            f.write(f"--- READING ENCODING USED: {encoding_used} ---\n")
            f.write(f"--- HTML CODE OF THE FIRST TABLE AFTER <a name='summary'> ---\n\n")
            f.write(summary_table.prettify())
        
        print("\nГОТОВО!")
        print(f"Файл '{output_txt_file}' успешно создан. Пожалуйста, пришлите мне его содержимое.")

    except Exception as e:
        print(f"\nКРИТИЧЕСКАЯ ОШИБКА: Не удалось записать в файл '{output_txt_file}'.")
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()