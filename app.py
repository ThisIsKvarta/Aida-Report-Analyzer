# app.py
import sys
import os
import logging # <<< ИЗМЕНЕНИЕ: импортируем logging
import configparser
from PySide6.QtCore import QThread, Signal, QUrl, Qt
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QPushButton, QLineEdit, QFileDialog, QPlainTextEdit,
                             QLabel, QProgressBar, QTableWidget, QTableWidgetItem,
                             QMainWindow, QHeaderView, QSizePolicy)
from PySide6.QtGui import QDesktopServices, QIcon, QColor

from backend_logic import AidaWorker, HEADERS_MAIN

# <<< ИЗМЕНЕНИЕ: Настраиваем полное логирование в файл в самом начале >>>
def setup_logging():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    log_file = config.get('Settings', 'log_filename', fallback='parser.log')
    
    # Конфигурируем логгер
    logging.basicConfig(
        level=logging.DEBUG,  # Устанавливаем самый подробный уровень логирования
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='w',  # 'w' - перезаписывать файл при каждом запуске, 'a' - добавлять
        encoding='utf-8' # Указываем кодировку для лог-файла
    )
    # Отключаем слишком "болтливые" логгеры от сторонних библиотек, если нужно
    # logging.getLogger('PySide6').setLevel(logging.WARNING)

class LogWindow(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Лог выполнения"); self.setGeometry(150, 150, 800, 400)
        layout = QVBoxLayout(self); self.log_area = QPlainTextEdit(); self.log_area.setReadOnly(True); layout.addWidget(self.log_area)
    def add_log(self, message, level):
        color = {"info": "black", "warning": "#8B4513", "error": "red", "debug": "blue"}.get(level, "black")
        self.log_area.appendHtml(f'<span style="color:{color};">{message}</span>')
        # Дублируем сообщения из GUI-лога в файловый лог
        if level == 'error':
            logging.error(f"[GUI] {message}")
        elif level == 'warning':
            logging.warning(f"[GUI] {message}")
        else:
            logging.info(f"[GUI] {message}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Анализатор отчетов AIDA64"); self.setGeometry(100, 100, 1200, 800)
        self.config = configparser.ConfigParser();
        try: self.config.read('config.ini', encoding='utf-8')
        except Exception as e: print(f"Не удалось прочитать config.ini: {e}")
        self.thread = None; self.worker = None; self.log_window = LogWindow(); self.last_file_path = ""
        self.create_widgets(); self.setup_layout(); self.connect_signals()
        logging.info("Приложение успешно инициализировано.")

    def create_widgets(self):
        self.folder_icon = QIcon.fromTheme("folder-open"); self.start_icon = QIcon.fromTheme("media-playback-start"); self.stop_icon = QIcon.fromTheme("media-playback-stop"); self.open_icon = QIcon.fromTheme("document-open"); self.log_icon = QIcon.fromTheme("text-x-generic")
        self.reports_path_edit = QLineEdit(self.config.get('Settings', 'reports_directory', fallback='reports'))
        self.select_folder_btn = QPushButton("Выбрать папку..."); self.select_folder_btn.setIcon(self.folder_icon)
        self.start_btn = QPushButton("Начать анализ"); self.start_btn.setIcon(self.start_icon); self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.stop_btn = QPushButton("Остановить"); self.stop_btn.setIcon(self.stop_icon); self.stop_btn.setEnabled(False)
        self.results_table = QTableWidget(); self.results_table.setColumnCount(len(HEADERS_MAIN)); self.results_table.setHorizontalHeaderLabels(HEADERS_MAIN); self.results_table.setEditTriggers(QTableWidget.NoEditTriggers); self.results_table.setAlternatingRowColors(True); 
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False); self.progress_bar.setAlignment(Qt.AlignCenter)
        self.open_file_btn = QPushButton("Открыть отчет"); self.open_file_btn.setIcon(self.open_icon); self.open_file_btn.setEnabled(False)
        self.show_log_btn = QPushButton("Показать лог"); self.show_log_btn.setIcon(self.log_icon)
        
    def setup_layout(self):
        main_widget = QWidget(); self.setCentralWidget(main_widget); main_layout = QVBoxLayout(main_widget); top_layout = QHBoxLayout(); top_layout.addWidget(QLabel("Папка с отчетами:")); top_layout.addWidget(self.reports_path_edit); top_layout.addWidget(self.select_folder_btn)
        main_layout.addLayout(top_layout); main_layout.addWidget(self.results_table); main_layout.addWidget(self.progress_bar)
        self.setStatusBar(QMainWindow.statusBar(self)); self.statusBar().showMessage("Готов к работе")
        toolbar = self.addToolBar("Controls"); toolbar.setMovable(False); toolbar.addWidget(self.start_btn); toolbar.addWidget(self.stop_btn); toolbar.addSeparator(); toolbar.addWidget(self.show_log_btn)
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred); toolbar.addWidget(spacer); toolbar.addWidget(self.open_file_btn)

    def connect_signals(self):
        self.select_folder_btn.clicked.connect(self.select_folder); self.start_btn.clicked.connect(self.start_analysis); self.stop_btn.clicked.connect(self.stop_analysis); self.open_file_btn.clicked.connect(self.open_report_file); self.show_log_btn.clicked.connect(self.log_window.show)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с отчетами AIDA64", self.reports_path_edit.text())
        if folder: self.reports_path_edit.setText(folder); logging.info(f"Выбрана новая папка с отчетами: {folder}")

    def start_analysis(self):
        reports_dir = self.reports_path_edit.text()
        logging.info(f"Запрос на запуск анализа для папки: '{reports_dir}'")
        if not os.path.isdir(reports_dir):
            self.statusBar().showMessage("Ошибка: Указанная папка не существует!", 5000)
            logging.error(f"Папка '{reports_dir}' не существует. Анализ прерван.")
            return
        
        self.start_btn.setEnabled(False); self.stop_btn.setEnabled(True); self.open_file_btn.setEnabled(False); self.results_table.setRowCount(0); self.log_window.log_area.clear(); self.progress_bar.setValue(0); self.progress_bar.setVisible(True)
        self.thread = QThread(); self.worker = AidaWorker(reports_dir, self.config); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.finished.connect(self.thread.quit); self.worker.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater); self.worker.finished.connect(self.analysis_finished)
        self.worker.log_message.connect(self.log_window.add_log); self.worker.progress_update.connect(self.update_progress); self.worker.result_ready.connect(self.add_table_row)
        self.thread.start(); self.statusBar().showMessage("Анализ запущен...")
        logging.info("Рабочий поток для анализа запущен.")

    def stop_analysis(self):
        if self.worker:
            self.worker.is_running = False
            self.log_window.add_log("-> Отправка сигнала остановки...", "warning")
            self.stop_btn.setEnabled(False)

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total); self.progress_bar.setValue(current); self.statusBar().showMessage(f"Обработка файла {current} из {total}...")
        
    def add_table_row(self, data_row):
        row_position = self.results_table.rowCount()
        self.results_table.insertRow(row_position)
        
        category = data_row.get('category', 3)
        colors = {1: QColor("#FFC7CE"), 2: QColor("#FFEB9C"), 3: QColor("#C6EFCE")}
        row_color = colors.get(category)

        for col_idx, header in enumerate(HEADERS_MAIN):
            if header == 'SMART Статус':
                smart_problems = data_row.get('SMART Проблемы', [])
                item_text = "; ".join(smart_problems) if smart_problems else data_row.get('SMART Статус', 'OK')
            else:
                item_text = str(data_row.get(header, ''))
            item = QTableWidgetItem(item_text)
            if row_color: item.setBackground(row_color)
            self.results_table.setItem(row_position, col_idx, item)

    def analysis_finished(self, output_filepath):
        self.progress_bar.setVisible(False)
        self.results_table.resizeColumnsToContents()
        if output_filepath:
            self.statusBar().showMessage(f"Анализ успешно завершен!", 5000); self.last_file_path = output_filepath; self.open_file_btn.setEnabled(True); self.log_window.add_log(f"Отчет сохранен: {output_filepath}", "info")
            logging.info(f"Анализ завершен. Результат в файле: {output_filepath}")
        else:
            self.statusBar().showMessage("Анализ завершен с ошибкой или был прерван.", 5000)
            logging.warning("Анализ завершен без создания файла отчета (ошибка или прерывание).")
        self.start_btn.setEnabled(True); self.stop_btn.setEnabled(False); self.thread = None; self.worker = None

    def open_report_file(self):
        if self.last_file_path and os.path.exists(self.last_file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(self.last_file_path)))

    def closeEvent(self, event):
        logging.info("Получен сигнал закрытия окна.")
        self.stop_analysis()
        if self.thread and self.thread.isRunning():
            logging.info("Ожидание завершения рабочего потока...")
            self.thread.quit()
            self.thread.wait()
            logging.info("Рабочий поток завершен.")
        self.log_window.close(); event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    setup_logging() # <<< ИЗМЕНЕНИЕ: Вызываем настройку логгера
    window = MainWindow()
    window.show()
    sys.exit(app.exec())