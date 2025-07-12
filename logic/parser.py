import os
import re
import logging
from bs4 import BeautifulSoup
from logic.helpers import parse_size_from_string

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

def parse_smart_data_full(smart_section, config):
    has_critical, has_warning = False, False
    all_drives_display_details = []
    all_drives_problem_details = []

    HDD_ATTR_MAP = {'01': 'Ошибки чтения (Raw)', '05': 'Переназначенные сектора', '09': 'Наработка (часы)', 'C5': 'Сектора-кандидаты', 'C6': 'Неисправимые сектора'}
    SSD_ATTR_MAP = {'3': 'Доступный резерв (%)', '5': 'Использованный ресурс (%)', '48': 'Всего записано (ТБ)', '128': 'Наработка (часы)', '144': 'Небезопасные отключения'}

    smart_table = smart_section.find_next('table')
    if not smart_table: return "NOT_FOUND", [], []

    current_drive_name, current_is_ssd, KEY_ATTRS_MAP, current_drive_display = None, False, {}, {}

    def process_previous_drive():
        if current_drive_name:
            all_drives_display_details.append(f"--- {current_drive_name.split('(')[0].strip()} ---")
            for name, value in current_drive_display.items():
                all_drives_display_details.append(f"{name}: {value}")

    for row in smart_table.find_all('tr'):
        header_cell = row.find('td', class_='dt')
        
        if header_cell:
            process_previous_drive()
            
            drive_name = header_cell.get_text(strip=True).strip('[]')
            if "ADATA SC750" in drive_name.upper():
                current_drive_name = None 
                continue

            current_drive_name = drive_name
            current_is_ssd = any(k in drive_name.lower() for k in ['ssd', 'nvme', 'snv'])
            KEY_ATTRS_MAP = SSD_ATTR_MAP if current_is_ssd else HDD_ATTR_MAP
            current_drive_display = {name: "N/A" for name in KEY_ATTRS_MAP.values()}
            continue

        if not current_drive_name: continue

        cells_with_text = [c.get_text(strip=True) for c in row.find_all('td') if c.get_text(strip=True)]
        if len(cells_with_text) < 4: continue

        attr_id = cells_with_text[0].strip()
        raw_data_str = cells_with_text[-2].strip()
        
        if attr_id in KEY_ATTRS_MAP:
            display_name = KEY_ATTRS_MAP[attr_id]
            display_value = raw_data_str.split(' ')[0]
            if attr_id == '48' and current_is_ssd: 
                display_value = f"{parse_size_from_string(raw_data_str, 'tb'):.2f}"
            current_drive_display[display_name] = display_value
        
        try: numeric_val = int(re.match(r'\d+', raw_data_str).group()) if re.match(r'\d+', raw_data_str) else 0
        except (ValueError, IndexError, AttributeError): continue

        if not current_is_ssd:
            if attr_id == '05' and numeric_val > 0:
                has_warning = True; all_drives_problem_details.append(f"HDD '{current_drive_name}': Переназначенные сектора: {numeric_val}")
                if numeric_val > config.getint('SMART', 'hdd_crc_error_warn_count', fallback=10): has_critical = True
            if attr_id in ['C5', 'C6'] and numeric_val > 0:
                has_critical = True; all_drives_problem_details.append(f"HDD '{current_drive_name}': Проблемные сектора: {numeric_val}")
        else:
            if attr_id == '3' and numeric_val < config.getint('SMART', 'ssd_available_spare_warn_percent'):
                has_warning = True; all_drives_problem_details.append(f"SSD '{current_drive_name}': Мало запасных блоков: {numeric_val}%")
                if numeric_val < config.getint('SMART', 'ssd_available_spare_critical_percent'): has_critical = True

    process_previous_drive()
    
    final_status = "GOOD"
    if has_warning: final_status = "OK"
    if has_critical: final_status = "BAD"
    
    return final_status, all_drives_display_details, all_drives_problem_details

def parse_aida_report(file_path, config, log_emitter):
    log_emitter(f"Парсинг: {os.path.basename(file_path)}", "info")
    try:
        with open(file_path, 'r', encoding='windows-1251', errors='ignore') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'lxml')
        data = {'Имя файла': os.path.basename(file_path)}
        
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
        # --- ИСПРАВЛЕНИЕ: Фильтруем диск ADATA прямо здесь ---
        disk_list = [d.find_next_sibling('td').get_text(strip=True) for d in disk_candidates if "ADATA SC750" not in d.find_next_sibling('td').get_text(strip=True).upper()]
        data['Дисковые накопители'] = "\n".join(disk_list) or 'Не найдено'
        
        # --- ВОССТАНОВЛЕННЫЙ И УЛУЧШЕННЫЙ ПАРСИНГ ОЗУ ---
        mobo_section = soup.find('a', attrs={'name': 'motherboard'}); mobo_table = mobo_section.find_next('table') if mobo_section else None
        data['Сокет'] = find_value_by_label(mobo_table, 'Разъёмы для ЦП') or ''
        
        ram_models, is_ram_found = [], False
        if ram_labels := summary_table.find_all('td', text=re.compile(r'^\s*DIMM\d:')):
            for label in ram_labels:
                if model_text := label.find_next_sibling('td').get_text(strip=True):
                    if 'empty' not in model_text.lower() and 'пусто' not in model_text.lower(): ram_models.append(model_text)
            if ram_models: is_ram_found = True

        if not is_ram_found:
            ram_headers = soup.find_all('td', class_='dt', text=re.compile(r'\[\s*(Устройства памяти|SPD)\s*/'))
            for header in ram_headers:
                parent_tr = header.find_parent('tr'); module_rows_html = []
                if not parent_tr: continue
                for sibling_tr in parent_tr.find_next_siblings('tr'):
                    if sibling_tr.find('td', class_='dt'): break
                    module_rows_html.append(str(sibling_tr))
                if not module_rows_html: continue
                module_soup = BeautifulSoup(f"<table>{''.join(module_rows_html)}</table>", 'lxml')
                module_size = find_value_by_label(module_soup, 'Размер')
                if module_size and module_size.strip():
                    manufacturer = find_value_by_label(module_soup, 'Производитель') or ''
                    speed = find_value_by_label(module_soup, 'Макс. частота') or find_value_by_label(module_soup, 'Скорость памяти') or ''
                    if 'mt/s' in speed.lower(): speed = speed.lower().replace('mt/s', 'MHz').strip()
                    display_text = f"{module_size.strip()} {manufacturer} DDR3 {speed}".strip()
                    ram_models.append(re.sub(r'\s+', ' ', display_text))
        
        final_cleaned_models = [" ".join(text.split('(')[0].strip().split()) for text in ram_models if text]
        data['Модели плашек ОЗУ'] = "\n".join(final_cleaned_models) if final_cleaned_models else 'Не найдено'
        data['Кол-во плашек ОЗУ'] = len(final_cleaned_models)

        total_physical_ram_gb = parse_size_from_string(data.get('Объем ОЗУ'))
        if total_physical_ram_gb == 0 and final_cleaned_models:
            total_physical_ram_gb = sum(parse_size_from_string(s, 'gb') for s in final_cleaned_models)
            if total_physical_ram_gb > 0: data['Объем ОЗУ'] = f"{int(total_physical_ram_gb * 1024)} МБ"

        total_ram_slots = 0
        if mobo_string := data.get('Материнская плата', ''):
            if match := re.search(r'(\d+)\s+DDR\d\s+DIMM', mobo_string, re.I): total_ram_slots = int(match.group(1))
        if total_ram_slots == 0:
            if ram_headers := soup.find_all('td', class_='dt', text=re.compile(r'\[\s*(Устройства памяти|SPD)\s*/')): total_ram_slots = len(ram_headers)
            else: total_ram_slots = 4 if 'so-dimm' not in str(ram_models).lower() else 2
        data['Свободно слотов ОЗУ'] = max(0, total_ram_slots - data['Кол-во плашек ОЗУ'])
        
        # --- ПАРСИНГ SMART ---
        if smart_section := soup.find('a', attrs={'name': 'smart'}):
            smart_status, display_details, problem_details = parse_smart_data_full(smart_section, config)
            data['internal_smart_status'] = smart_status 
            data['SMART Проблемы'] = problem_details
            final_smart_output = [smart_status]
            if display_details: final_smart_output.extend(display_details)
            data['SMART Статус'] = "\n".join(final_smart_output)
        else:
            data['internal_smart_status'] = 'NOT_FOUND'
            data['SMART Проблемы'] = []
            data['SMART Статус'] = find_value_by_label(summary_table, 'SMART-статус жёстких дисков') or "Не найден"

        if bios_section := soup.find('a', attrs={'name': 'bios'}):
            if bios_table := bios_section.find_next('table'): data['Дата BIOS'] = find_value_by_label(bios_table, 'Дата BIOS системы') or ''
        
        return data
    except Exception as e:
        logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА ПАРСИНГА {os.path.basename(file_path)}: {e}", exc_info=True)
        return None