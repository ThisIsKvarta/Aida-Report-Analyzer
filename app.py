# app.py
import sys
import os
import logging
import configparser
from functools import partial
from PySide6.QtCore import QThread, Signal, QUrl, Qt, QSettings
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QFileDialog, QPlainTextEdit,
                             QLabel, QProgressBar, QTableWidget, QTableWidgetItem,
                             QMainWindow, QHeaderView, QSizePolicy, QMessageBox, QTabWidget,
                             QMenu)
from PySide6.QtGui import QDesktopServices, QIcon, QColor, QAction

from backend_logic import AidaWorker, ExcelReaderWorker, ExcelUpdateWorker, HEADERS_MAIN, HEADERS_NETWORK

def setup_logging():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    log_file = config.get('Settings', 'log_filename', fallback='parser.log')
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        filename=log_file, filemode='w', encoding='utf-8')

class LogWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лог выполнения")
        self.setGeometry(150, 150, 800, 400)
        layout = QVBoxLayout(self)
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
    
    def add_log(self, message, level):
        color = {"info": "black", "warning": "#8B4513", "error": "red", "debug": "blue"}.get(level, "black")
        self.log_area.appendHtml(f'<span style="color:{color};">{message}</span>')
        level_map = {'error': logging.ERROR, 'warning': logging.WARNING, 'info': logging.INFO}
        logging.log(level_map.get(level, logging.INFO), f"[GUI] {message}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Анализатор отчетов AIDA64")
        self.settings = QSettings("KvartaSoft", "AidaReportAnalyzer")
        self.setGeometry(100, 100, 1200, 800)
        
        self.config = configparser.ConfigParser()
        try:
            self.config.read('config.ini', encoding='utf-8')
        except Exception as e:
            print(f"Не удалось прочитать config.ini: {e}")
            
        self.thread = None
        self.worker = None
        self.log_window = LogWindow()
        self.last_file_path = ""

        self.create_widgets()
        self.setup_layout()
        self.connect_signals()
        
        self.load_settings()
        self.auto_load_data()
        
        logging.info("Приложение успешно инициализировано.")

    def create_widgets(self):
        self.folder_icon = QIcon.fromTheme("folder-open")
        self.start_icon = QIcon.fromTheme("media-playback-start")
        self.stop_icon = QIcon.fromTheme("media-playback-stop")
        self.open_icon = QIcon.fromTheme("document-open")
        self.log_icon = QIcon.fromTheme("text-x-generic")
        
        self.reports_path_edit = QLineEdit(self.config.get('Settings', 'reports_directory', fallback='reports'))
        self.select_folder_btn = QPushButton("Выбрать папку...")
        self.select_folder_btn.setIcon(self.folder_icon)
        
        self.start_btn = QPushButton("Начать анализ")
        self.start_btn.setIcon(self.start_icon); self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.setIcon(self.stop_icon); self.stop_btn.setEnabled(False)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Фильтр по активной таблице...")
        
        self.tabs = QTabWidget()
        self.main_table = self.create_new_table(HEADERS_MAIN)
        self.network_table = self.create_new_table(HEADERS_NETWORK)
        self.tabs.addTab(self.main_table, "Общая информация")
        self.tabs.addTab(self.network_table, "Сеть")
        
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False); self.progress_bar.setAlignment(Qt.AlignCenter)
        self.open_file_btn = QPushButton("Открыть отчет"); self.open_file_btn.setIcon(self.open_icon); self.open_file_btn.setEnabled(False)
        self.show_log_btn = QPushButton("Показать лог"); self.show_log_btn.setIcon(self.log_icon)

    def create_new_table(self, headers):
        table = QTableWidget()
        visible_headers = [h for h in headers if h != '_RAW_DATA']
        # <<< ВОЗВРАЩАЕМ +1 ДЛЯ СКРЫТОЙ КОЛОНКИ СОРТИРОВКИ >>>
        table.setColumnCount(len(visible_headers) + 1)
        table.setHorizontalHeaderLabels(visible_headers)
        # <<< ВОЗВРАЩАЕМ СКРЫТИЕ ПОСЛЕДНЕЙ КОЛОНКИ >>>
        table.setColumnHidden(len(visible_headers), True)
        
        table.setEditTriggers(QTableWidget.DoubleClicked)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_table_context_menu)
        table.itemChanged.connect(self.handle_item_changed)
        return table

    def setup_layout(self):
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        top_layout = QHBoxLayout(); top_layout.addWidget(QLabel("Папка с отчетами:")); top_layout.addWidget(self.reports_path_edit); top_layout.addWidget(self.select_folder_btn)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.filter_edit)
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(self.progress_bar)
        self.setStatusBar(QMainWindow.statusBar(self))
        toolbar = self.addToolBar("Controls"); toolbar.setMovable(False); toolbar.addWidget(self.start_btn); toolbar.addWidget(self.stop_btn); toolbar.addSeparator(); toolbar.addWidget(self.show_log_btn)
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred); toolbar.addWidget(spacer); toolbar.addWidget(self.open_file_btn)
    
    def connect_signals(self):
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.start_btn.clicked.connect(self.start_analysis)
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.open_file_btn.clicked.connect(self.open_report_file)
        self.show_log_btn.clicked.connect(self.log_window.show)
        self.filter_edit.textChanged.connect(self.filter_table)
        self.tabs.currentChanged.connect(self.filter_table)

    def show_table_context_menu(self, position):
        active_table = self.tabs.currentWidget()
        if not isinstance(active_table, QTableWidget): return
        
        item = active_table.itemAt(position)
        if not item: return

        row_index = item.row()
        
        menu = QMenu()
        edit_action = menu.addAction("Изменить ячейку")
        edit_action.triggered.connect(lambda: active_table.editItem(item))
        
        menu.addSeparator()

        copy_menu = menu.addMenu("Копировать")
        
        headers = [active_table.horizontalHeaderItem(i).text() for i in range(active_table.columnCount())]
        for idx, header in enumerate(headers):
            cell_item = active_table.item(row_index, idx)
            if cell_item and cell_item.text():
                action_text = f"{header}: {cell_item.text()[:30]}..." if len(cell_item.text()) > 30 else f"{header}: {cell_item.text()}"
                copy_action = QAction(action_text, self)
                # functools.partial правильно "захватывает" значение text для каждой итерации
                copy_action.triggered.connect(partial(QApplication.clipboard().setText, cell_item.text()))
                copy_menu.addAction(copy_action)
        try:
            filename_col = headers.index("Имя файла")
            filename_item = active_table.item(row_index, filename_col)
            if filename_item and filename_item.text():
                menu.addSeparator()
                open_action = menu.addAction(f"Открыть отчет {filename_item.text()}")
                open_action.triggered.connect(partial(self.open_and_select_report, filename_item.text()))
        except ValueError:
            pass
        menu.exec(active_table.viewport().mapToGlobal(position))
        
    def handle_item_changed(self, item):
        active_table = item.tableWidget()
        active_table.blockSignals(True)
        
        row = item.row(); column = item.column(); new_value = item.text()
        
        header_item = active_table.horizontalHeaderItem(column)
        if not header_item:
            active_table.blockSignals(False); return
        header_to_update = header_item.text()
        
        headers_list = [active_table.horizontalHeaderItem(i).text() for i in range(active_table.columnCount())]
        try:
            filename_col = headers_list.index("Имя файла")
            id_item = active_table.item(row, filename_col)
            if id_item and id_item.text():
                unique_id = id_item.text()
            else:
                self.log_window.add_log("Не найден 'Имя файла' для обновления.", "error"); active_table.blockSignals(False); return
        except ValueError:
            self.log_window.add_log("Колонка 'Имя файла' не найдена в текущей таблице.", "error"); active_table.blockSignals(False); return
            
        filepath = self.config.get('Settings', 'output_filename', fallback='system_analysis.xlsx')
        
        self.thread = QThread()
        self.worker = ExcelUpdateWorker(filepath, unique_id, header_to_update, new_value)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.log_message.connect(self.log_window.add_log)
        self.thread.started.connect(self.worker.run)
        self.thread.start()
        
        active_table.blockSignals(False)

    def open_and_select_report(self, filename):
        reports_dir = self.reports_path_edit.text()
        file_path = os.path.join(reports_dir, filename)
        if os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            for table in [self.main_table, self.network_table]:
                items = table.findItems(filename, Qt.MatchExactly)
                if items:
                    self.tabs.setCurrentWidget(table)
                    table.selectRow(items[0].row())
                    break
        else:
            QMessageBox.warning(self, "Ошибка", f"Файл отчета {file_path} не найден.")

    def save_settings(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("main_header_state", self.main_table.horizontalHeader().saveState())
        self.settings.setValue("network_header_state", self.network_table.horizontalHeader().saveState())
        self.settings.setValue("current_tab_index", self.tabs.currentIndex())
        self.settings.setValue("filter_text", self.filter_edit.text())

    def load_settings(self):
        if self.settings.contains("geometry"): self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.contains("main_header_state"): self.main_table.horizontalHeader().restoreState(self.settings.value("main_header_state"))
        if self.settings.contains("network_header_state"): self.network_table.horizontalHeader().restoreState(self.settings.value("network_header_state"))
        if self.settings.contains("current_tab_index"):
            index = self.settings.value("current_tab_index", type=int)
            if index < self.tabs.count(): self.tabs.setCurrentIndex(index)
        if self.settings.contains("filter_text"): self.filter_edit.setText(self.settings.value("filter_text"))

    def filter_table(self):
        filter_text = self.filter_edit.text().lower()
        active_table = self.tabs.currentWidget()
        if not isinstance(active_table, QTableWidget): return
        for row in range(active_table.rowCount()):
            row_is_visible = False
            if not filter_text: row_is_visible = True
            else:
                for col in range(active_table.columnCount()):
                    if active_table.isColumnHidden(col): continue
                    cell_item = active_table.item(row, col)
                    if cell_item and filter_text in cell_item.text().lower():
                        row_is_visible = True; break
            active_table.setRowHidden(row, not row_is_visible)

    def auto_load_data(self):
        output_filepath = self.config.get('Settings', 'output_filename', fallback='system_analysis.xlsx')
        if os.path.exists(output_filepath):
            self.start_btn.setEnabled(False); self.stop_btn.setEnabled(False); self.progress_bar.setVisible(True)
            self.thread = QThread(); self.worker = ExcelReaderWorker(output_filepath); self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run); self.worker.finished.connect(self.thread.quit); self.worker.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater); self.worker.finished.connect(self.analysis_finished)
            self.worker.log_message.connect(self.log_window.add_log); self.worker.progress_update.connect(self.update_progress); self.worker.result_ready.connect(self.add_table_row)
            self.thread.start(); self.statusBar().showMessage("Загрузка данных из Excel...")
        else: self.statusBar().showMessage("Готов к работе. Файл отчета не найден.")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с отчетами AIDA64", self.reports_path_edit.text())
        if folder: self.reports_path_edit.setText(folder)

    def start_analysis(self):
        reports_dir = self.reports_path_edit.text()
        if not os.path.isdir(reports_dir):
            QMessageBox.warning(self, "Ошибка", f"Папка '{reports_dir}' не найдена!"); return
        self.start_btn.setEnabled(False); self.stop_btn.setEnabled(True); self.open_file_btn.setEnabled(False)
        self.main_table.setRowCount(0); self.network_table.setRowCount(0)
        self.log_window.log_area.clear(); self.progress_bar.setValue(0); self.progress_bar.setVisible(True)
        self.thread = QThread(); self.worker = AidaWorker(reports_dir, self.config); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.finished.connect(self.thread.quit); self.worker.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater); self.worker.finished.connect(self.analysis_finished)
        self.worker.log_message.connect(self.log_window.add_log); self.worker.progress_update.connect(self.update_progress); self.worker.result_ready.connect(self.add_table_row)
        self.thread.start(); self.statusBar().showMessage("Анализ запущен...")

    def stop_analysis(self):
        if self.worker and hasattr(self.worker, 'is_running'):
            self.worker.is_running = False

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total); self.progress_bar.setValue(current)
        if isinstance(self.worker, AidaWorker): self.statusBar().showMessage(f"Обработка файла {current} из {total}...")
        else: self.statusBar().showMessage(f"Загрузка строки {current} из {total}...")
        
    def add_table_row(self, data_row):
        self.main_table.blockSignals(True)
        self.network_table.blockSignals(True)
        
        category = data_row.get('category', 3)
        colors = {1: QColor("#FFC7CE"), 2: QColor("#FFEB9C"), 3: QColor("#C6EFCE")}
        row_color = colors.get(category)
        
        # --- Заполнение основной таблицы ---
        row_pos_main = self.main_table.rowCount()
        self.main_table.insertRow(row_pos_main)
        visible_headers_main = [h for h in HEADERS_MAIN if h != '_RAW_DATA']
        for col_idx, header in enumerate(visible_headers_main):
            smart_status_for_logic = data_row.get('_internal_smart_status') or data_row.get('SMART Статус', 'GOOD')
            item_text = str(data_row.get(header, ''))
            item = QTableWidgetItem(item_text)
            if header == 'SMART Статус':
                if smart_status_for_logic == 'BAD':
                    font = item.font(); font.setBold(True); item.setFont(font)
                    item.setForeground(QColor("#9C0006"))
                elif smart_status_for_logic == 'OK':
                    item.setForeground(QColor("#9C6500"))
            item.setBackground(row_color)
            self.main_table.setItem(row_pos_main, col_idx, item)
        
        # <<< ВОЗВРАЩАЕМ ЗАПОЛНЕНИЕ СКРЫТОЙ КОЛОНКИ >>>
        category_item_main = QTableWidgetItem()
        category_item_main.setData(Qt.DisplayRole, category)
        self.main_table.setItem(row_pos_main, len(visible_headers_main), category_item_main)

        # --- Заполнение сетевой таблицы ---
        row_pos_net = self.network_table.rowCount()
        self.network_table.insertRow(row_pos_net)
        visible_headers_net = [h for h in HEADERS_NETWORK if h != '_RAW_DATA']
        for col_idx, header in enumerate(visible_headers_net):
            item = QTableWidgetItem(str(data_row.get(header, '')))
            item.setBackground(row_color)
            self.network_table.setItem(row_pos_net, col_idx, item)
        
        # <<< ВОЗВРАЩАЕМ ЗАПОЛНЕНИЕ СКРЫТОЙ КОЛОНКИ >>>
        category_item_net = QTableWidgetItem()
        category_item_net.setData(Qt.DisplayRole, category)
        self.network_table.setItem(row_pos_net, len(visible_headers_net), category_item_net)
        
        self.main_table.blockSignals(False)
        self.network_table.blockSignals(False)
        
    def analysis_finished(self, output_filepath):
        # Отключаем сигналы на время манипуляций
        self.main_table.blockSignals(True)
        self.network_table.blockSignals(True)

        self.progress_bar.setVisible(False)
        
        # <<< ВОЗВРАЩАЕМ ПРАВИЛЬНУЮ СОРТИРОВКУ >>>
        main_sort_col = self.main_table.columnCount() - 1
        self.main_table.sortItems(main_sort_col, Qt.AscendingOrder)
        
        net_sort_col = self.network_table.columnCount() - 1
        self.network_table.sortItems(net_sort_col, Qt.AscendingOrder)

        self.main_table.resizeColumnsToContents()
        self.network_table.resizeColumnsToContents()

        # Возвращаем сигналы
        self.main_table.blockSignals(False)
        self.network_table.blockSignals(False)
        
        self.filter_table() # Применяем фильтр после всех операций
        
        status_message = ""
        if isinstance(self.worker, AidaWorker): status_message = "Анализ успешно завершен!" if output_filepath else "Анализ завершен с ошибкой или был прерван."
        elif isinstance(self.worker, ExcelReaderWorker): status_message = "Данные из Excel успешно загружены!" if output_filepath else "Загрузка данных не удалась."
        else: status_message = "Операция завершена."
        
        self.statusBar().showMessage(status_message, 5000)
        
        if output_filepath:
            self.last_file_path = output_filepath
            self.open_file_btn.setEnabled(True)
            log_msg = f"Отчет сохранен: {output_filepath}" if isinstance(self.worker, AidaWorker) else f"Данные загружены из: {output_filepath}"
            self.log_window.add_log(log_msg, "info")
            logging.info(log_msg)
        else:
            if not isinstance(self.worker, ExcelUpdateWorker):
                logging.warning("Процесс завершен без указания файла отчета.")
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.thread = None
        self.worker = None

    def open_report_file(self):
        if self.last_file_path and os.path.exists(self.last_file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(self.last_file_path)))
            
    def closeEvent(self, event):
        self.save_settings()
        logging.info("Получен сигнал закрытия окна.")
        self.stop_analysis()
        if self.thread and self.thread.isRunning():
            logging.info("Ожидание завершения рабочего потока...")
            self.thread.quit(); self.thread.wait(); logging.info("Рабочий поток завершен.")
        self.log_window.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    setup_logging()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())