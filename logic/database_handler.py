# ЗАМЕНИТЬ ПОЛНОСТЬЮ ФАЙЛ logic/database_handler.py

import sqlite3
import logging
import os
import re
from utils.constants import HEADERS_MAIN, HEADERS_NETWORK

logger = logging.getLogger(__name__)

DB_NAME = 'system_analysis.db'
TABLE_NAME = 'computers'

def _get_master_key_list():
    """
    Создает ЕДИНЫЙ, УПОРЯДОЧЕННЫЙ и УНИКАЛЬНЫЙ список всех ключей.
    Это единый источник правды для структуры данных.
    """
    unique_original_keys = []
    # Добавляем все уникальные заголовки, сохраняя их логический порядок
    key_pool = HEADERS_MAIN + HEADERS_NETWORK + ['category', 'problems', 'internal_smart_status', 'last_updated']
    
    for key in key_pool:
        # Исключаем временное поле _RAW_DATA
        if key not in unique_original_keys and key != '_RAW_DATA':
            unique_original_keys.append(key)
    return unique_original_keys

def get_db_connection():
    """Устанавливает соединение с БД и возвращает объект соединения."""
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Не удалось подключиться к базе данных {DB_NAME}: {e}")
        return None

def sanitize_col_name(name):
    """Надежно очищает имя для использования в SQL, СОХРАНЯЯ РУССКИЕ БУКВЫ."""
    if not isinstance(name, str): name = str(name)
    # ИСПРАВЛЕНО: Добавлены а-яА-Я в разрешенные символы
    name_with_spaces = re.sub(r'[^a-zA-Z0-9_а-яА-Я]', ' ', name)
    clean_name = re.sub(r'\s+', '_', name_with_spaces).strip('_')
    return clean_name

def initialize_db():
    """Создает базу данных и таблицу с ГАРАНТИРОВАННО уникальными именами колонок."""
    if os.path.exists(DB_NAME): return

    logger.info(f"База данных {DB_NAME} не найдена. Создаю новую...")
    conn = get_db_connection()
    if not conn: return
    
    try:
        cursor = conn.cursor()
        
        original_keys = _get_master_key_list()
        
        column_definitions = []
        seen_sanitized = set()
        
        for key in original_keys:
            sanitized_name = sanitize_col_name(key)
            if not sanitized_name:
                logger.warning(f"Ключ '{key}' после очистки стал пустым. Пропускаю.")
                continue
            if sanitized_name in seen_sanitized:
                logger.warning(f"Обнаружен дубликат очищенного имени колонки: '{sanitized_name}' для ключа '{key}'. Пропускаю.")
                continue
            seen_sanitized.add(sanitized_name)

            if key == 'Имя файла':
                column_definitions.append(f'"{sanitized_name}" TEXT PRIMARY KEY')
            else:
                column_definitions.append(f'"{sanitized_name}" TEXT')

        query = f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} ({', '.join(column_definitions)})"
        
        cursor.execute(query)
        conn.commit()
        logger.info(f"Таблица '{TABLE_NAME}' успешно создана с {len(column_definitions)} колонками.")
    except sqlite3.Error as e:
        logger.error(f"Критическая ошибка при создании базы данных: {e}", exc_info=True)
        if conn: conn.close()
        if os.path.exists(DB_NAME): os.remove(DB_NAME)
    finally:
        if conn: conn.close()

def save_data_to_db(data_list):
    """Сохраняет данные в БД, используя стабильный и полный список колонок."""
    if not data_list: return
    conn = get_db_connection()
    if not conn: return
    
    try:
        cursor = conn.cursor()
        
        original_keys = _get_master_key_list()
        
        # Получаем список колонок из БД
        cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
        db_columns_info = cursor.fetchall()
        db_columns_set = {info['name'] for info in db_columns_info}

        rows_to_insert = []
        for data_row in data_list:
            values_for_row = []
            columns_for_row = []

            for key in original_keys:
                sanitized_key = sanitize_col_name(key)
                if sanitized_key in db_columns_set:
                    columns_for_row.append(f'"{sanitized_key}"')
                    value = data_row.get(key)
                    if isinstance(value, list):
                        value = "; ".join(map(str, value))
                    values_for_row.append(str(value) if value is not None else None)
            
            if values_for_row:
                placeholders = ', '.join(['?'] * len(values_for_row))
                query = f"INSERT OR REPLACE INTO {TABLE_NAME} ({', '.join(columns_for_row)}) VALUES ({placeholders})"
                cursor.execute(query, tuple(values_for_row))

        conn.commit()
        logger.info(f"Успешно сохранено/обновлено {len(data_list)} записей в БД.")
    except sqlite3.Error as e:
        logger.error(f"Ошибка при массовом сохранении в БД: {e}", exc_info=True)
    finally:
        if conn: conn.close()

def fetch_all_data_from_db():
    """Извлекает все данные из БД и возвращает их в виде словарей с оригинальными именами ключей."""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,))
        if cursor.fetchone() is None:
            logger.warning(f"Таблица '{TABLE_NAME}' не найдена в базе данных. Возвращаю пустой список.")
            return []
        
        rows = conn.execute(f"SELECT * FROM {TABLE_NAME}").fetchall()
        
        original_keys = _get_master_key_list()
        key_map = {sanitize_col_name(h): h for h in original_keys}
        
        restored_data = []
        for row in rows:
            new_row_dict = {}
            for sanitized_key in row.keys():
                original_key = key_map.get(sanitized_key, sanitized_key)
                if original_key == 'category' and row[sanitized_key] is not None:
                    try:
                        new_row_dict[original_key] = int(float(row[sanitized_key]))
                    except (ValueError, TypeError):
                        new_row_dict[original_key] = 3
                else:
                    new_row_dict[original_key] = row[sanitized_key]

            restored_data.append(new_row_dict)
        return restored_data
    except sqlite3.Error as e:
        logger.error(f"Ошибка при чтении данных из БД: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()

def update_single_field_in_db(unique_id, field_name, new_value):
    """Надежно обновляет одно поле для одной записи в БД."""
    conn = get_db_connection()
    if not conn: return False
    try:
        sanitized_field = sanitize_col_name(field_name)
        sanitized_id_field = sanitize_col_name("Имя файла")
        
        query = f'UPDATE {TABLE_NAME} SET "{sanitized_field}" = ? WHERE "{sanitized_id_field}" = ?'
        
        cursor = conn.cursor()
        cursor.execute(query, (new_value, unique_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Поле '{field_name}' для записи '{unique_id}' обновлено в БД.")
            return True
        else:
            logger.warning(f"Запись с ID '{unique_id}' не найдена для обновления поля '{field_name}'.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Ошибка при обновлении поля '{field_name}': {e}", exc_info=True)
        return False
    finally:
        if conn: conn.close()