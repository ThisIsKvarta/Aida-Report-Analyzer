# logic/parser.py
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
        logger.error(f"Ошибка в find_value_by_label для '{label_text}': {e}", exc_info=True)
        return None

def parse_aida_report(file_path, config, log_emitter):
    log_emitter(f"Обработка: {os.path.basename(file_path)}", "info")
    try:
        with open(file_path, 'r', encoding='windows-1251', errors='ignore') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'lxml')
        data = {'Имя файла': os.path.basename(file_path)}
        
        # 1. Парсинг основной сводки
        summary_section = soup.find('a', attrs={'name': 'summary'})
        summary_table = summary_section.find_next('table') if summary_section else None
        
        if not summary_table:
            logger.error(f"[{data['Имя файла']}] Не найдена основная сводная таблица.")
            return None

        data['Название ПК'] = find_value_by_label(summary_table, 'Имя компьютера') or ''
        data['ОС'] = find_value_by_label(summary_table, 'Операционная система') or ''
        data['Процессор'] = find_value_by_label(summary_table, 'Тип ЦП') or ''
        data['Материнская плата'] = find_value_by_label(summary_table, 'Системная плата') or ''
        data['Видеоадаптер'] = find_value_by_label(summary_table, 'Видеоадаптер') or ''
        data['Монитор'] = find_value_by_label(summary_table, 'Монитор') or ''
        data['Объем ОЗУ'] = find_value_by_label(summary_table, 'Системная память') or ''
        data['Локальный IP'] = find_value_by_label(summary_table, 'Первичный адрес IP') or ''
        data['MAC-адрес'] = find_value_by_label(summary_table, 'Первичный адрес MAC') or ''
        disk_candidates = summary_table.find_all('td', text=re.compile('Дисковый накопитель'))
        data['Дисковые накопители'] = "; ".join([d.find_next_sibling('td').get_text(strip=True) for d in disk_candidates]) or 'Не найдено'
        printer_candidates = summary_table.find_all('td', text=re.compile('Принтер'))
        all_printers = [p.find_next_sibling('td').get_text(strip=True) for p in printer_candidates]
        system_printers_keys = ['Fax', 'Microsoft Print to PDF', 'XPS', 'OneNote', 'AnyDesk']
        data['Принтеры'] = "; ".join([p for p in all_printers if not any(key in p for key in system_printers_keys)]) or 'Не найдено'

        # 2. УНИВЕРСАЛЬНЫЙ ПАРСИНГ ОЗУ
        ram_models = []
        # Способ А: Ищем плашки прямо в сводной таблице
        ram_labels_in_summary = summary_table.find_all('td', text=re.compile(r'^\s*DIMM\d:'))
        if ram_labels_in_summary:
            logger.info(f"[{data['Имя файла']}] Найдены модули ОЗУ в сводной таблице.")
            for label in ram_labels_in_summary:
                model_text = label.find_next_sibling('td').get_text(strip=True)
                # Просто берем текст как есть
                ram_models.append(model_text)
        
        # Способ Б: Если в сводке пусто, ищем детальные секции
        if not ram_models:
            logger.warning(f"[{data['Имя файла']}] ОЗУ в сводке не найдено. Ищу в детальных секциях...")
            ram_headers = soup.find_all('td', class_='dt', text=re.compile(r'\[\s*(Устройства памяти|SPD)\s*/'))
            logger.info(f"[{data['Имя файла']}] Найдено {len(ram_headers)} детальных заголовков ОЗУ.")
            
            for header in ram_headers:
                info_table = header.find_next('table')
                if not info_table: continue
                
                # Просто берем размер, это самое надежное
                module_size = find_value_by_label(info_table, 'Размер')
                if module_size and module_size.strip():
                    ram_models.append(f"Модуль {module_size.strip()}")

        data['Модели плашек ОЗУ'] = "; ".join(ram_models) or 'Не найдено'
        data['Кол-во плашек ОЗУ'] = len(ram_models)

        # 3. Парсинг остальной информации
        mobo_section = soup.find('a', attrs={'name': 'motherboard'}); mobo_table = mobo_section.find_next('table') if mobo_section else None
        data['Сокет'] = find_value_by_label(mobo_table, 'Разъёмы для ЦП') or ''
        
        bios_section = soup.find('a', attrs={'name': 'bios'}); bios_table = bios_section.find_next('table') if bios_section else None
        data['Дата BIOS'] = find_value_by_label(bios_table, 'Дата BIOS системы') or ''
        
        smart_section = soup.find('a', attrs={'name': 'smart'})
        if smart_section:
            data['SMART Статус'], data['SMART Проблемы'] = parse_smart_data_full(smart_section, config)
        else:
            status_in_summary = find_value_by_label(summary_table, 'SMART-статус жёстких дисков')
            data['SMART Статус'] = status_in_summary or "Не найден"
            data['SMART Проблемы'] = []

        # 4. Расчет свободных слотов ОЗУ
        total_ram_slots = 0
        if data['Кол-во плашек ОЗУ'] > 0:
            html_content_lower = html_content.lower()
            if data['Кол-во плашек ОЗУ'] >= 3:
                total_ram_slots = 4
            elif 'so-dimm' in html_content_lower:
                total_ram_slots = 2
            else:
                total_ram_slots = 2
        data['Свободно слотов ОЗУ'] = max(0, total_ram_slots - data['Кол-во плашек ОЗУ']) if total_ram_slots > 0 else 'Неизвестно'

        # 5. Заполняем пропущенные поля
        all_headers = list(set(HEADERS_MAIN + HEADERS_NETWORK))
        for key in all_headers:
            if key not in data and key != '_RAW_DATA': data[key] = 'Не найдено'
            
        return data
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА ПАРСИНГА в {os.path.basename(file_path)}: {e}", exc_info=True)
        return None
    
def parse_smart_data_full(smart_section, config):
    all_problems = []; has_bad_status=False; has_ok_status=False
    temp_warn = config.getint('SMART', 'temp_warning_celsius', fallback=45)
    power_on_warn = config.getint('SMART', 'power_on_warning_hours', fallback=30000)
    power_cycle_warn = config.getint('SMART', 'power_cycle_warning_count', fallback=10000)
    read_error_warn = config.getint('SMART', 'read_error_warning_rate', fallback=1000000)
    
    current_element = smart_section
    drive_tables = []
    while current_element:
        current_element = current_element.find_next()
        if not current_element: break
        if current_element.name == 'a' and current_element.has_attr('name'): break
        if current_element.name == 'table':
            if current_element.find('td', class_='dt'):
                drive_tables.append(current_element)

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
    
def analyze_system(data, config):
    data['internal_smart_status'] = data['SMART Статус']
    if data['SMART Статус'] in ['Неизвестно', 'Не найден']:
        data['internal_smart_status'] = 'GOOD'
    
    problems = []
    smart_status = data['internal_smart_status']
    if smart_status == "BAD": return 1, "; ".join(data.get('SMART Проблемы', ["Критическая ошибка диска"]))
    if smart_status == "OK": problems.extend(data.get('SMART Проблемы', []))
    
    bios_age_limit = config.getint('Analysis', 'bios_age_limit_years', fallback=5)
    ram_critical_gb = config.getfloat('Analysis', 'ram_critical_gb', fallback=3.8)
    ram_upgrade_gb = config.getfloat('Analysis', 'ram_upgrade_gb', fallback=7.8)
    os_ver = data.get('ОС', '')
    cpu = data.get('Процессор', '')
    socket = data.get('Сокет', '')
    ram_gb_str = re.search(r'(\d+)\s*МБ', data.get('Объем ОЗУ') or '')
    ram_gb = int(ram_gb_str.group(1)) / 1024 if ram_gb_str else 0
    gpu_driver = data.get('Видеоадаптер', '')
    bios_date_str = data.get('Дата BIOS')
    has_ssd = any(k in (data.get('Дисковые накопители') or '').lower() for k in ['ssd', 'nvme', 'snv'])
    
    is_critical = False
    is_upgrade_needed = len(problems) > 0
    
    if socket and 'LGA775' in socket: is_critical = True; problems.append("Очень старый сокет (LGA775)")
    if ram_gb > 0 and ram_gb < ram_critical_gb: is_critical = True; problems.append(f"Критически мало ОЗУ ({ram_gb:.1f} ГБ)")
    if 'Windows 7' in os_ver:
        is_upgrade_needed = True
        if any(p in cpu for p in ['G3','G1','E5','i3-2','i3-3','FX']): problems.append("Устаревшая ОС на слабом ЦП")
        else: problems.append("Устаревшая ОС Windows 7")
    if ram_critical_gb <= ram_gb < ram_upgrade_gb: is_upgrade_needed = True; problems.append(f"Недостаточно ОЗУ ({ram_gb:.1f} ГБ)")
    if not has_ssd: is_upgrade_needed = True; problems.append("Отсутствует SSD")
    if 'Microsoft Basic Display Adapter' in gpu_driver: is_upgrade_needed = True; problems.append("Не установлен видеодрайвер")
    if bios_date_str:
        try:
            date_match = re.search(r'(\d{2}/\d{2}/\d{2,4})', bios_date_str)
            if date_match:
                date_str_extracted = date_match.group(1)
                parts = re.split(r'[/.-]', date_str_extracted)
                if len(parts) == 3:
                    p1, p2, p3 = map(int, parts)
                    if p1 > 12: day, month, year = p1, p2, p3
                    else: month, day, year = p1, p2, p3
                    if len(str(year)) == 2: year += 2000
                    bios_date = datetime(year, month, day)
                    if (datetime.now() - bios_date).days > 365 * bios_age_limit: is_upgrade_needed = True; problems.append(f"BIOS старше {bios_age_limit} лет")
        except (ValueError, IndexError): pass
        
    unique_problems = sorted(list(set(problems)))
    if is_critical: return 1, "; ".join(unique_problems)
    if is_upgrade_needed: return 2, "; ".join(unique_problems)
    return 3, "Состояние хорошее"