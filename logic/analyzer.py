# logic/analyzer.py

import re
from datetime import datetime
from logic.helpers import parse_size_from_string # Обрати внимание, импорт из нового места

def analyze_system(data, config):
    """
    Анализирует словарь с "сырыми" данными о ПК и возвращает категорию и список проблем.
    """
    problems = []
    
    # Сначала добавляем проблемы с дисками, если они есть и статус не GOOD
    if data.get('internal_smart_status') != 'GOOD':
        smart_problems = data.get('SMART Проблемы', [])
        if smart_problems:
            problems.append("Проблемы с дисками:")
            problems.extend([f"  - {p}" for p in smart_problems])

    # --- Анализ остальных компонентов ---
    bios_age_limit = config.getint('Analysis', 'bios_age_limit_years', fallback=5)
    ram_critical_gb = config.getfloat('Analysis', 'ram_critical_gb', fallback=3.8)
    ram_upgrade_gb = config.getfloat('Analysis', 'ram_upgrade_gb', fallback=7.8)
    os_ver, socket = data.get('ОС', ''), data.get('Сокет', '')
    gpu_driver, bios_date_str = data.get('Видеоадаптер', ''), data.get('Дата BIOS')
    has_ssd = any(k in (data.get('Дисковые накопители') or '').lower() for k in ['ssd', 'nvme', 'snv'])
    ram_gb = parse_size_from_string(data.get('Объем ОЗУ', '0 MB'), 'gb')
    
    is_critical = data.get('internal_smart_status') == 'BAD'
    is_upgrade_needed = data.get('internal_smart_status') == 'OK'

    if socket and any(s in socket for s in ['LGA775', 'AM2', 'LGA1156']):
        is_critical = True
        problems.append("Критично: Очень старая платформа")
    if ram_gb > 0 and ram_gb < ram_critical_gb:
        is_critical = True
        problems.append(f"Критично: Мало ОЗУ ({ram_gb:.1f} ГБ)")
    if 'Windows 7' in os_ver:
        is_upgrade_needed = True
        problems.append("Проблема: Устаревшая ОС Windows 7")
    if ram_critical_gb <= ram_gb < ram_upgrade_gb:
        is_upgrade_needed = True
        problems.append(f"Проблема: Недостаточно ОЗУ ({ram_gb:.1f} ГБ)")
    if not has_ssd:
        is_upgrade_needed = True
        problems.append("Проблема: Отсутствует SSD")
    if 'Microsoft Basic Display Adapter' in gpu_driver:
        is_upgrade_needed = True
        problems.append("Проблема: Не установлен видеодрайвер")
    if bios_date_str:
        try:
            bios_date = None
            if date_match := re.search(r'(\d{2}/\d{2}/\d{4})', bios_date_str):
                bios_date = datetime.strptime(date_match.group(0), '%m/%d/%Y')
            elif date_match := re.search(r'(\d{2}/\d{2}/\d{2})', bios_date_str):
                bios_date = datetime.strptime(date_match.group(0), '%m/%d/%y')
            if bios_date and (datetime.now() - bios_date).days > 365 * bios_age_limit:
                is_upgrade_needed = True
                problems.append(f"Предупреждение: BIOS старше {bios_age_limit} лет")
        except (ValueError, IndexError):
            pass
            
    unique_problems = sorted(list(set(problems)))
    
    if not unique_problems:
        return 3, "Состояние хорошее"

    final_problems_str = "\n".join(unique_problems)
    
    if is_critical or "Критично" in final_problems_str:
        return 1, final_problems_str
    if is_upgrade_needed or "Проблема" in final_problems_str or "Предупреждение" in final_problems_str:
        return 2, final_problems_str
    
    return 3, "Состояние хорошее"