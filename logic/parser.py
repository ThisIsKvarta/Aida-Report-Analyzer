# logic/parser.py
import configparser
import os
import re
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from utils.constants import CRITICAL_SMART_ATTRIBUTES, HEADERS_MAIN, HEADERS_NETWORK

logger = logging.getLogger(__name__)

def find_value_by_label(search_area, label_text):
    if not search_area: return None
    try:
        candidates = search_area.find_all(lambda tag: tag.name == 'td' and label_text in tag.get_text() and not tag.find('td'))
        if not candidates: return None
        label_td = candidates[-1]
        value_td = label_td.find_next_sibling('td')
        if not value_td: value_td = label_td.find_next('td')
        if value_td:
            link = value_td.find('a')
            return link.get_text(strip=True) if link else value_td.get_text(strip=True)
        return None
    except Exception as e:
        logger.error(f"Ошибка в find_value_by_label для '{label_text}': {e}", exc_info=True)
        return None

def parse_smart_data(soup, config):
    smart_section = soup.find('a', {'name': 'smart'})
    if not smart_section: return "Не найден", []
    all_problems = []; has_bad_status=False; has_ok_status=False
    temp_warn = config.getint('SMART', 'temp_warning_celsius', fallback=45)
    power_on_warn = config.getint('SMART', 'power_on_warning_hours', fallback=30000)
    power_cycle_warn = config.getint('SMART', 'power_cycle_warning_count', fallback=10000)
    read_error_warn = config.getint('SMART', 'read_error_warning_rate', fallback=1000000)

    drive_tables = smart_section.find_next_siblings('table')
    for table in drive_tables:
        header = table.find('td', class_='dt')
        if not header: continue
        drive_name = header.get_text(strip=True).strip('[] ').split(' ')[0]
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 3:
                attr_id = cells[2].get_text(strip=True); attr_desc = cells[3].get_text(strip=True); raw_data_str = cells[-2].get_text(strip=True)
                try:
                    raw_data_val = int(raw_data_str, 16) if 'x' in raw_data_str else int(raw_data_str)
                    if attr_id in CRITICAL_SMART_ATTRIBUTES and raw_data_val > 0: has_bad_status = True; all_problems.append(f"{drive_name}: {attr_desc} ({attr_id}) > 0")
                    elif attr_id == 'C2' and raw_data_val > temp_warn: has_ok_status = True; all_problems.append(f"{drive_name}: Высокая t° ({raw_data_val}°C)")
                    elif attr_id == '09' and raw_data_val > power_on_warn: has_ok_status = True; all_problems.append(f"{drive_name}: Большой налет часов")
                    elif attr_id == '0C' and raw_data_val > power_cycle_warn: has_ok_status = True; all_problems.append(f"{drive_name}: Много вкл/выкл")
                    elif attr_id == '01' and raw_data_val > read_error_warn: has_ok_status = True; all_problems.append(f"{drive_name}: Много ошибок чтения")
                except (ValueError, IndexError): continue
    if has_bad_status: return "BAD", all_problems
    if has_ok_status: return "OK", all_problems
    return "GOOD", []

# ЗАМЕНИТЬ ПОЛНОСТЬЮ ФУНКЦИЮ analyze_system в файле logic/parser.py

def analyze_system(data, config):
    problems = []
    
    # Получаем "чистый" SMART-статус, который всегда есть в данных после парсинга
    smart_status = data.get('internal_smart_status', "GOOD")
    smart_problems = data.get('SMART Проблемы', [])

    # Категория 1: Критические проблемы, требующие немедленной замены
    if smart_status == "BAD":
        # Это самая серьезная проблема, она определяет категорию 1
        problems.extend(smart_problems or ["Критическая ошибка диска"])
        return 1, "; ".join(sorted(list(set(problems))))
        
    # Если SMART не 'BAD', но есть предупреждения, добавляем их в список
    if smart_status == "OK" and smart_problems:
        problems.extend(smart_problems)
    
    # --- Сбор данных для дальнейшего анализа ---
    try:
        bios_age_limit = config.getint('Analysis', 'bios_age_limit_years', fallback=5)
        ram_critical_gb = config.getfloat('Analysis', 'ram_critical_gb', fallback=3.8)
        ram_upgrade_gb = config.getfloat('Analysis', 'ram_upgrade_gb', fallback=7.8)
    except (ValueError, configparser.Error) as e:
        logger.error(f"Ошибка чтения конфига для анализа: {e}. Использую значения по-умолчанию.")
        bios_age_limit, ram_critical_gb, ram_upgrade_gb = 5, 3.8, 7.8
    
    os_ver = data.get('ОС', '')
    cpu = data.get('Процессор', '')
    socket = data.get('Сокет', '')
    ram_gb_str = re.search(r'(\d+)\s*МБ', data.get('Объем ОЗУ') or '')
    ram_gb = int(ram_gb_str.group(1)) / 1024 if ram_gb_str else 0
    gpu_driver = data.get('Видеоадаптер', '')
    bios_date_str = data.get('Дата BIOS')
    has_ssd = any(k in (data.get('Дисковые накопители') or '').lower() for k in ['ssd', 'nvme', 'snv'])

    # --- Определение флагов для категоризации ---
    is_critical_issue = False  # Флаг для проблем, ведущих к категории 1
    is_upgrade_needed = False # Флаг для проблем, ведущих к категории 2

    # Проверки, которые могут привести к КАТЕГОРИИ 1 (полная замена)
    if socket and 'LGA775' in socket:
        is_critical_issue = True
        problems.append("Очень старый сокет (LGA775)")
    if ram_gb > 0 and ram_gb < ram_critical_gb:
        is_critical_issue = True
        problems.append(f"Критически мало ОЗУ ({ram_gb:.1f} ГБ)")

    # Проверки, которые ведут к КАТЕГОРИИ 2 (апгрейд)
    # Эти проверки выполняются, даже если уже есть критические проблемы, чтобы собрать полный список
    if 'Windows 7' in os_ver:
        is_upgrade_needed = True
        problems.append("Устаревшая ОС Windows 7")
    if ram_critical_gb <= ram_gb < ram_upgrade_gb:
        is_upgrade_needed = True
        problems.append(f"Недостаточно ОЗУ ({ram_gb:.1f} ГБ)")
    if not has_ssd:
        is_upgrade_needed = True
        problems.append("Отсутствует SSD")
    if 'Microsoft Basic Display Adapter' in gpu_driver:
        is_upgrade_needed = True
        problems.append("Не установлен видеодрайвер")
    if bios_date_str:
        try:
            # Ищем дату в формате XX/XX/XXXX или XX/XX/XX
            date_match = re.search(r'(\d{2}/\d{2}/\d{2,4})', bios_date_str)
            if date_match:
                date_str_extracted = date_match.group(1)
                # Определяем формат даты (американский M/D/Y или европейский D/M/Y)
                parts = date_str_extracted.split('/')
                year_part = parts[2]
                day_part, month_part = (int(parts[1]), int(parts[0]))
                
                bios_date_format = '%m/%d/%Y' if month_part <= 12 and day_part <= 31 else '%d/%m/%Y'
                if len(year_part) == 2:
                    bios_date_format = bios_date_format.replace('Y', 'y')
                    
                bios_date = datetime.strptime(date_str_extracted, bios_date_format)
                if (datetime.now() - bios_date).days > 365 * bios_age_limit:
                    is_upgrade_needed = True
                    problems.append(f"BIOS старше {bios_age_limit} лет")
        except (ValueError, IndexError):
            logger.warning(f"Не удалось распознать дату BIOS: '{bios_date_str}'")
            pass

    # --- Принятие финального решения ---
    unique_problems = sorted(list(set(problems)))
    
    if is_critical_issue:
        return 1, "; ".join(unique_problems)
    
    # Если уже есть проблемы от SMART (OK), это уже категория 2
    if is_upgrade_needed or smart_status == "OK":
        return 2, "; ".join(unique_problems)
    
    # Если проблем не найдено
    return 3, "Состояние хорошее"

def parse_aida_report(file_path, config, log_emitter):
    log_emitter(f"Обработка: {os.path.basename(file_path)}", "info")
    try:
        with open(file_path, 'r', encoding='windows-1251', errors='ignore') as f: html_content = f.read()
        soup = BeautifulSoup(html_content, 'lxml')
        data = {'Имя файла': os.path.basename(file_path)}
        summary_section = soup.find('a', {'name': 'summary'}); summary_table = summary_section.find_next('table') if summary_section else None
        
        if summary_table:
            data['Название ПК'] = find_value_by_label(summary_table, 'Имя компьютера') or ''
            data['ОС'] = find_value_by_label(summary_table, 'Операционная система') or ''
            data['Процессор'] = find_value_by_label(summary_table, 'Тип ЦП') or ''
            data['Материнская плата'] = find_value_by_label(summary_table, 'Системная плата') or ''
            data['Видеоадаптер'] = find_value_by_label(summary_table, 'Видеоадаптер') or ''
            data['Монитор'] = find_value_by_label(summary_table, 'Монитор') or ''
            data['Объем ОЗУ'] = find_value_by_label(summary_table, 'Системная память') or ''
            data['Локальный IP'] = find_value_by_label(summary_table, 'Первичный адрес IP') or ''
            data['MAC-адрес'] = find_value_by_label(summary_table, 'Первичный адрес MAC') or ''
            ram_candidates = summary_table.find_all(lambda tag: tag.name == 'td' and re.search(r'DIMM\d', tag.get_text()) and not tag.find('td'))
            ram_models = [re.sub(r'\s+\(.*\)', '', label.find_next('td').get_text(strip=True)) for label in ram_candidates if label.find_next('td')]
            data['Модели плашек ОЗУ'] = "; ".join(filter(None, ram_models)) or 'Не найдено'
            disk_candidates = summary_table.find_all(lambda tag: tag.name == 'td' and 'Дисковый накопитель' in tag.get_text() and not tag.find('td'))
            disk_models = [label.find_next('td').get_text(strip=True) for label in disk_candidates if label.find_next('td')]
            data['Дисковые накопители'] = "; ".join(disk_models) or 'Не найдено'
            printer_candidates = summary_table.find_all(lambda tag: tag.name == 'td' and 'Принтер' in tag.get_text() and not tag.find('td'))
            all_printers = [label.find_next('td').get_text(strip=True) for label in printer_candidates if label.find_next('td')]
            system_printers_keys = ['Fax', 'Microsoft Print to PDF', 'XPS', 'OneNote', 'AnyDesk']
            physical_printers = [p for p in all_printers if not any(key in p for key in system_printers_keys)]
            data['Принтеры'] = "; ".join(physical_printers) or 'Не найдено'

        mobo_section = soup.find('a', {'name': 'motherboard'}); mobo_table = mobo_section.find_next('table') if mobo_section else summary_table
        data['Сокет'] = find_value_by_label(mobo_table, 'Разъёмы для ЦП') or ''
        bios_section = soup.find('a', {'name': 'bios'}); bios_table = bios_section.find_next('table') if bios_section else summary_table
        data['Дата BIOS'] = find_value_by_label(bios_table, 'Дата BIOS системы') or ''
        data['SMART Статус'], data['SMART Проблемы'] = parse_smart_data(soup, config)
        
        installed_sticks_count = data['Модели плашек ОЗУ'].count(';') + 1 if data.get('Модели плашек ОЗУ') and data['Модели плашек ОЗУ'] != 'Не найдено' else 0
        total_ram_slots = 0
        if installed_sticks_count > 0:
            html_content_lower = html_content.lower()
            if installed_sticks_count >= 3: total_ram_slots = 4
            elif 'so-dimm' in html_content_lower: total_ram_slots = 2
            else: 
                has_high_slots = 'dimm3' in html_content_lower or 'dimm4' in html_content_lower
                if has_high_slots: total_ram_slots = 4
                else: total_ram_slots = 2
        data['Кол-во плашек ОЗУ'] = installed_sticks_count
        data['Свободно слотов ОЗУ'] = total_ram_slots - installed_sticks_count if total_ram_slots > 0 else 'Неизвестно'

        all_headers = list(set(HEADERS_MAIN + HEADERS_NETWORK))
        for key in all_headers:
            if key not in data and key != '_RAW_DATA': data[key] = 'Не найдено'
            
        return data
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА ПАРСИНГА в {os.path.basename(file_path)}: {e}", exc_info=True)
        return None