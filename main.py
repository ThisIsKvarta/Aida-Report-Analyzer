# ЗАМЕНИТЬ ПОЛНОСТЬЮ ФАЙЛ main.py

import sys
import os
import logging
import configparser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication

# --- НОВЫЕ ИМПОРТЫ ---
from ui.main_window import MainWindow
from logic.database_handler import initialize_db
from ui.styling import get_graphite_theme
from utils.logger_setup import setup_global_logging # Наш новый логгер

# Старая функция setup_logging() больше не нужна, удаляем ее

if __name__ == "__main__":
    # --- ИЗМЕНЕНИЕ: Настройка логирования теперь - самый первый шаг! ---
    # Это гарантирует, что мы поймаем ошибки даже при инициализации.
    setup_global_logging()

    # Проверка и создание config.ini (остается без изменений)
    if not os.path.exists('config.ini'):
        config = configparser.ConfigParser()
        config['Settings'] = {
            'reports_directory': 'reports',
            'output_filename': 'system_analysis.xlsx',
            'log_filename': 'parser.log'
        }
        config['Analysis'] = {
            'bios_age_limit_years': '5', 
            'ram_critical_gb': '3.8', 
            'ram_upgrade_gb': '7.8', 
            'disk_c_critical_gb': '15.0'
        }
        config['SMART'] = {
            'hdd_power_on_warn_hours': '30000',
            'hdd_power_on_critical_hours': '50000',
            'ssd_power_on_warn_hours': '20000',
            'ssd_power_on_critical_hours': '40000',
            'ssd_data_written_warn_tb': '400',
            'ssd_data_written_critical_tb': '600',
            'ssd_available_spare_warn_percent': '10',
            'ssd_available_spare_critical_percent': '3',
            'hdd_crc_error_warn_count': '5',
            'temp_warning_celsius': '45', 
            'power_on_warning_hours': '30000', 
            'power_cycle_warning_count': '10000', 
            'read_error_warning_rate': '1000000'
        }
        with open('config.ini', 'w', encoding='utf-8') as configfile: 
            config.write(configfile)

    app = QApplication(sys.argv)
    
    app.setStyleSheet(get_graphite_theme())
    
    initialize_db()
    
    window = MainWindow()
    window.show()
    
    logging.getLogger("main_logger").info("Приложение успешно запущено.")
    sys.exit(app.exec())