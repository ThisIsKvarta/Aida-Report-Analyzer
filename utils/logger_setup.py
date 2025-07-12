# utils/logger_setup.py
import logging
import sys
from logging.handlers import RotatingFileHandler

LOG_FILENAME = 'parser.log'

def handle_exception(exc_type, exc_value, exc_traceback):
    """Перехватывает и логирует все неперехваченные исключения."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger("main_logger")
    logger.critical("--- НЕПЕРЕХВАЧЕННОЕ ИСКЛЮЧЕНИЕ ---", exc_info=(exc_type, exc_value, exc_traceback))
    logger.critical("--- ПРОГРАММА АВАРИЙНО ЗАВЕРШЕНА ---")

def setup_global_logging():
    """Настраивает глобальное логирование для всего приложения."""
    # Устанавливаем наш обработчик для всех "тихих" падений
    sys.excepthook = handle_exception

    # Настраиваем формат сообщений
    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] [%(threadName)s] %(name)s: %(message)s (%(filename)s:%(lineno)d)'
    )
    
    # Получаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # Логируем ВСЁ

    # Обработчик для записи в файл с ротацией (например, макс. 5МБ, 3 старых копии)
    file_handler = RotatingFileHandler(LOG_FILENAME, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Обработчик для вывода в консоль (опционально, удобно для отладки)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO) # В консоль выводим только инфо и выше

    # Добавляем обработчики к корневому логгеру
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger("main_logger").info("Глобальный логгер успешно настроен.")