# main.py
import sys
import os
import logging
import configparser
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from logic.database_handler import initialize_db

def setup_logging():
    # Эта функция может остаться здесь или переехать в utils, пока оставим тут.
    if not os.path.exists('config.ini'):
        # Создаем базовый конфиг, если его нет
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
            'temp_warning_celsius': '45',
            'power_on_warning_hours': '30000',
            'power_cycle_warning_count': '10000',
            'read_error_warning_rate': '1000000'
        }
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)

    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    log_file = config.get('Settings', 'log_filename', fallback='parser.log')
    
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        filename=log_file, 
                        filemode='w', 
                        encoding='utf-8')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    setup_logging()
    
    # --- НОВАЯ СТРОКА: Инициализируем БД перед стартом ---
    initialize_db()
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())