# ЗАМЕНИТЬ ВСЕ СОДЕРЖИМОЕ ФАЙЛА logic/workers.py

import os
import logging
from PySide6.QtCore import QObject, Signal

from logic.parser import analyze_system, parse_aida_report
from logic.excel_handler import write_to_excel
from logic.database_handler import save_data_to_db, fetch_all_data_from_db, update_single_field_in_db
from utils.helpers import natural_sort_key

logger = logging.getLogger(__name__)

class AidaWorker(QObject):
    log_message = Signal(str, str)
    progress_update = Signal(int, int)
    status_update = Signal(str, bool)
    result_ready = Signal(dict)
    finished = Signal(str) # Передает путь к файлу или пустую строку при ошибке

    def __init__(self, reports_dir, config):
        super().__init__()
        self.reports_dir = reports_dir
        self.config = config
        self.is_running = True

    def run(self):
        try:
            output_file = self.config.get('Settings', 'output_filename', fallback='system_analysis.xlsx')
            report_files = [f for f in os.listdir(self.reports_dir) if f.lower().endswith(('.htm', '.html'))]
            
            if not report_files:
                self.log_message.emit("В указанной папке не найдено файлов отчетов .htm/.html.", "warning")
                self.finished.emit("")
                return

            self.log_message.emit(f"Найдено отчетов: {len(report_files)}", "info")
            all_reports_data = []
            total_files = len(report_files)
            
            for i, filename in enumerate(report_files):
                if not self.is_running:
                    break
                self.progress_update.emit(i + 1, total_files)
                file_path = os.path.join(self.reports_dir, filename)
                
                parsed_data = parse_aida_report(file_path, self.config, self.log_message.emit)
                if parsed_data:
                    # 1. Сохраняем "чистый" статус ('BAD', 'OK', 'GOOD') для анализа.
                    parsed_data['internal_smart_status'] = parsed_data['SMART Статус']
                    
                    # 2. Проводим анализ на основе этого "чистого" статуса и других данных.
                    category, problems_text = analyze_system(parsed_data, self.config)
                    parsed_data['category'] = category
                    parsed_data['problems'] = problems_text
                    
                    # 3. Для удобного отображения в UI, если есть проблемы SMART,
                    #    перезаписываем поле 'SMART Статус' на детальное описание.
                    if parsed_data.get('SMART Проблемы'):
                        parsed_data['SMART Статус'] = "; ".join(parsed_data['SMART Проблемы'])
                    
                    # 4. Отправляем полностью готовые данные в UI для "живого" отображения.
                    self.result_ready.emit(parsed_data)
                    all_reports_data.append(parsed_data)
            
            if not self.is_running:
                self.log_message.emit("Процесс анализа был прерван пользователем.", "warning")
                self.finished.emit("")
                return

            # --- Медленные операции после анализа ---
            self.status_update.emit("Сохранение данных в базу...", True)
            save_data_to_db(all_reports_data)
            
            self.status_update.emit("Экспорт в Excel...", True)
            all_data_from_db = fetch_all_data_from_db()
            # Сортируем данные для Excel "естественным" образом
            all_data_from_db.sort(key=lambda item: natural_sort_key(item.get('Имя файла')))
            write_to_excel(all_data_from_db, output_file, self.log_message.emit)
            
            self.finished.emit(output_file)

        except Exception as e:
            self.log_message.emit(f"КРИТИЧЕСКАЯ ОШИБКА в потоке анализа: {e}", "error")
            logger.error(f"Критическая ошибка в потоке AidaWorker: {e}", exc_info=True)
            self.finished.emit("")


class DatabaseUpdateWorker(QObject):
    """Обновляет одно поле в БД и запускает полный реэкспорт в Excel."""
    log_message = Signal(str, str)
    finished = Signal()

    def __init__(self, config, unique_id, header_to_update, new_value):
        super().__init__()
        self.config = config
        self.unique_id = unique_id
        self.header = header_to_update
        self.new_value = new_value

    def run(self):
        try:
            success = update_single_field_in_db(self.unique_id, self.header, self.new_value)
            if success:
                self.log_message.emit(f"Ячейка '{self.header}' для '{self.unique_id}' обновлена в БД.", "info")
                
                # Запускаем полный реэкспорт в Excel, чтобы изменения отразились в файле
                output_file = self.config.get('Settings', 'output_filename', fallback='system_analysis.xlsx')
                all_data = fetch_all_data_from_db()
                all_data.sort(key=lambda item: natural_sort_key(item.get('Имя файла', '')))
                write_to_excel(all_data, output_file, self.log_message.emit)
                self.log_message.emit("Файл Excel обновлен.", "info")
            else:
                 self.log_message.emit(f"Не удалось обновить ячейку '{self.header}' для '{self.unique_id}'.", "error")

        except Exception as e:
            self.log_message.emit(f"Ошибка при обновлении БД: {e}", "error")
            logger.error(f"Ошибка обновления БД: {e}", exc_info=True)
        finally:
            self.finished.emit()

class FullExcelExportWorker(QObject):
    """Просто берет все данные из БД и экспортирует их в Excel."""
    log_message = Signal(str, str)
    finished = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            self.log_message.emit("Экспорт всех данных в Excel запущен...", "info")
            output_file = self.config.get('Settings', 'output_filename', fallback='system_analysis.xlsx')
            all_data = fetch_all_data_from_db()
            all_data.sort(key=lambda item: natural_sort_key(item.get('Имя файла', '')))
            write_to_excel(all_data, output_file, self.log_message.emit)
            self.finished.emit(output_file)
        except Exception as e:
            self.log_message.emit(f"Ошибка при экспорте в Excel: {e}", "error")
            logger.error(f"Ошибка при экспорте в Excel: {e}", exc_info=True)
            self.finished.emit("")