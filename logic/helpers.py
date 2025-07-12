# logic/helpers.py
import re

def parse_size_from_string(text, target_unit='gb'):
    """Извлекает число и единицу измерения (ТБ, ГБ, МБ) из строки и конвертирует в нужную единицу."""
    if not text: return 0.0
    match = re.search(r'([\d\.]+)\s*(ТБ|TB|ГБ|GB|МБ|MB)', text, re.I)
    if not match: return 0.0
    
    val, unit = float(match.group(1)), match.group(2).lower()
    val_gb = 0.0
    if 'т' in unit or 't' in unit: val_gb = val * 1024
    elif 'г' in unit or 'g' in unit: val_gb = val
    elif 'м' in unit or 'm' in unit: val_gb = val / 1024
    
    if target_unit == 'tb': return val_gb / 1024.0
    return val_gb