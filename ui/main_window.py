# ui/main_window.py
import os
import logging
import configparser
from functools import partial

from PySide6.QtCore import QThread, Signal, QUrl, Qt, QSettings
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QFileDialog,
                             QLabel, QProgressBar, QTableWidget, QTableWidgetItem,
                             QMainWindow, QSizePolicy, QMessageBox, QTabWidget,
                             QMenu, QFrame, QComboBox, QCheckBox)
from PySide6.QtGui import QDesktopServices, QIcon, QColor, QAction

from ui.log_window import LogWindow
from logic.workers import AidaWorker, DatabaseUpdateWorker, IPUpdateWorker
from logic.database_handler import fetch_all_data_from_db
from utils.constants import HEADERS_MAIN, HEADERS_NETWORK
from ui.details_window import DetailsWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Анализатор отчетов AIDA64")
        self.settings = QSettings("KvartaSoft", "AidaReportAnalyzer")
        self.setGeometry(100, 100, 1200, 800)
        
        self.config = configparser.ConfigParser()
        self.config.read('config.ini', encoding='utf-8')
            
        self.thread = None
        self.worker = None
        self.log_window = LogWindow()
        self.last_file_path = ""
        
        self.all_data = {}
        self.details_windows = {}

        self.create_widgets()
        self.setup_layout()
        self.connect_signals()
        
        self.load_settings()
        self.auto_load_data()
        
        logging.info("Приложение успешно инициализировано.")

    def create_widgets(self):
        # ... (код без изменений) ...
        self.folder_icon = QIcon.fromTheme("folder-open")
        self.start_icon = QIcon.fromTheme("media-playback-start")
        self.stop_icon = QIcon.fromTheme("media-playback-stop")
        self.open_icon = QIcon.fromTheme("document-open")
        self.log_icon = QIcon.fromTheme("text-x-generic")
        self.update_ip_icon = QIcon.fromTheme("network-transmit-receive")
        self.update_ip_btn = QPushButton("Обновить IP")
        self.update_ip_btn.setIcon(self.update_ip_icon)
        self.reports_path_edit = QLineEdit(self.config.get('Settings', 'reports_directory', fallback='reports'))
        self.select_folder_btn = QPushButton("Выбрать папку...")
        self.select_folder_btn.setIcon(self.folder_icon)
        self.start_btn = QPushButton("Начать анализ")
        self.start_btn.setIcon(self.start_icon); self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.setIcon(self.stop_icon); self.stop_btn.setEnabled(False)
        self.filter_panel = QFrame(); self.filter_panel.setObjectName("filterPanel"); self.filter_panel.setStyleSheet("#filterPanel { border: 1px solid #ccc; border-radius: 4px; }")
        filter_layout = QHBoxLayout(self.filter_panel); filter_layout.setContentsMargins(5, 5, 5, 5)
        self.filter_column_combo = QComboBox(); self.filter_column_combo.addItem("Поиск по всем полям")
        self.filter_edit = QLineEdit(); self.filter_edit.setPlaceholderText("Введите текст для поиска...")
        self.check_critical = QCheckBox("Крит. проблемы"); self.check_upgrade = QCheckBox("Нужен апгрейд"); self.check_no_ssd = QCheckBox("Без SSD"); self.check_win7 = QCheckBox("Windows 7")
        self.reset_filters_btn = QPushButton("Сбросить фильтры")
        filter_layout.addWidget(QLabel("Искать в:")); filter_layout.addWidget(self.filter_column_combo, 1); filter_layout.addWidget(self.filter_edit, 2); filter_layout.addStretch(1)
        filter_layout.addWidget(self.check_critical); filter_layout.addWidget(self.check_upgrade); filter_layout.addWidget(self.check_no_ssd); filter_layout.addWidget(self.check_win7)
        separator = QFrame(); separator.setFrameShape(QFrame.Shape.VLine); separator.setFrameShadow(QFrame.Shadow.Sunken)
        filter_layout.addWidget(separator); filter_layout.addWidget(self.reset_filters_btn)
        self.tabs = QTabWidget()
        self.main_table = self.create_new_table(HEADERS_MAIN); self.network_table = self.create_new_table(HEADERS_NETWORK)
        self.tabs.addTab(self.main_table, "Общая информация"); self.tabs.addTab(self.network_table, "Сеть")
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False); self.progress_bar.setAlignment(Qt.AlignCenter)
        self.open_file_btn = QPushButton("Открыть Excel"); self.open_file_btn.setIcon(self.open_icon); self.open_file_btn.setEnabled(False)
        self.show_log_btn = QPushButton("Показать лог"); self.show_log_btn.setIcon(self.log_icon)

    def create_new_table(self, headers):
        # ... (код без изменений) ...
        table = QTableWidget()
        visible_headers = [h for h in headers if h != '_RAW_DATA']
        table.setColumnCount(1 + len(visible_headers) + 1)
        table.setHorizontalHeaderItem(0, QTableWidgetItem("Ст"))
        for i, header_text in enumerate(visible_headers, 1): table.setHorizontalHeaderItem(i, QTableWidgetItem(header_text))
        table.setHorizontalHeaderItem(table.columnCount() - 1, QTableWidgetItem("")); table.setColumnHidden(table.columnCount() - 1, True)
        table.setSortingEnabled(True); table.sortByColumn(table.columnCount() - 1, Qt.AscendingOrder)
        table.setColumnWidth(0, 30); table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows); table.setAlternatingRowColors(True); table.setContextMenuPolicy(Qt.CustomContextMenu)
        return table

    def setup_layout(self):
        # ... (код без изменений) ...
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        top_layout = QHBoxLayout(); top_layout.addWidget(QLabel("Папка с отчетами:")); top_layout.addWidget(self.reports_path_edit); top_layout.addWidget(self.select_folder_btn)
        main_layout.addLayout(top_layout); main_layout.addWidget(self.filter_panel); main_layout.addWidget(self.tabs); main_layout.addWidget(self.progress_bar)
        self.setStatusBar(QMainWindow.statusBar(self))
        toolbar = self.addToolBar("Controls"); toolbar.setMovable(False)
        toolbar.addWidget(self.start_btn); toolbar.addWidget(self.stop_btn); toolbar.addSeparator()
        toolbar.addWidget(self.update_ip_btn); toolbar.addSeparator()
        toolbar.addWidget(self.show_log_btn)
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer); toolbar.addWidget(self.open_file_btn)
    
    def connect_signals(self):
        # ... (код без изменений) ...
        self.select_folder_btn.clicked.connect(self.select_folder); self.start_btn.clicked.connect(self.start_analysis)
        self.stop_btn.clicked.connect(self.stop_analysis); self.update_ip_btn.clicked.connect(self.start_ip_update)
        self.open_file_btn.clicked.connect(self.open_excel_file); self.show_log_btn.clicked.connect(self.log_window.show)
        self.tabs.currentChanged.connect(self.on_tab_changed); self.filter_edit.textChanged.connect(self.filter_table)
        self.filter_column_combo.currentIndexChanged.connect(self.filter_table)
        self.check_critical.stateChanged.connect(self.filter_table); self.check_upgrade.stateChanged.connect(self.filter_table)
        self.check_no_ssd.stateChanged.connect(self.filter_table); self.check_win7.stateChanged.connect(self.filter_table)
        self.reset_filters_btn.clicked.connect(self.reset_filters)
        for table in [self.main_table, self.network_table]:
            table.cellDoubleClicked.connect(self.show_details_by_click)
            table.customContextMenuRequested.connect(self.show_table_context_menu); table.itemChanged.connect(self.handle_item_changed)
    
    def start_ip_update(self):
        # ... (код без изменений) ...
        logging.info("Запрошено обновление IP-адресов.")
        self.start_btn.setEnabled(False); self.update_ip_btn.setEnabled(False)
        self.thread = QThread(); self.worker = IPUpdateWorker(); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.log_message.connect(self.log_window.add_log)
        self.worker.finished.connect(self.ip_update_finished); self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.statusBar().showMessage("Запущено сканирование сети для обновления IP...")

    def ip_update_finished(self):
        # --- ИЗМЕНЕНО: УДАЛЕНА ПРЕЖДЕВРЕМЕННАЯ ОЧИСТКА ---
        logging.info("Процесс обновления IP-адресов завершен.")
        self.statusBar().showMessage("Обновление IP-адресов завершено. Обновляю таблицу...", 5000)
        self.auto_load_data()
        self.start_btn.setEnabled(True)
        self.update_ip_btn.setEnabled(True)
        # Строки self.thread = None и self.worker = None УДАЛЕНЫ.

    def auto_load_data(self):
        # ... (код без изменений) ...
        self.statusBar().showMessage("Загрузка данных из базы...")
        valid_data = [row for row in fetch_all_data_from_db() if row.get("Имя файла")]
        self.all_data.clear()
        for row_data in valid_data: self.all_data[row_data["Имя файла"]] = row_data
        for table in [self.main_table, self.network_table]:
            table.blockSignals(True); table.setSortingEnabled(False); table.setRowCount(len(valid_data))
        try:
            sorted_data = sorted(valid_data, key=lambda x: str(x.get('Имя файла', '')))
            for row_idx, data_row in enumerate(sorted_data):
                self._populate_table_row(self.main_table, row_idx, data_row); self._populate_table_row(self.network_table, row_idx, data_row)
        finally:
            for table in [self.main_table, self.network_table]:
                table.setSortingEnabled(True); table.blockSignals(False); table.sortItems(table.columnCount() - 1, Qt.AscendingOrder)
        self.update_filter_combo(); self.filter_table()
        if valid_data: self.statusBar().showMessage(f"Загружено {len(valid_data)} записей из базы.", 5000)
        else: self.statusBar().showMessage("База данных пуста или не содержит валидных записей.", 5000)
        output_file = self.config.get('Settings', 'output_filename', fallback='system_analysis.xlsx')
        if os.path.exists(output_file): self.open_file_btn.setEnabled(True); self.last_file_path = output_file

    def add_table_row(self, data_row):
        # ... (код без изменений) ...
        filename = data_row.get("Имя файла")
        if not filename: return
        self.all_data[filename] = data_row
        for table in [self.main_table, self.network_table]:
            table.blockSignals(True)
            try:
                row_pos = table.rowCount(); table.insertRow(row_pos); self._populate_table_row(table, row_pos, data_row)
            finally: table.blockSignals(False)

    def _populate_table_row(self, table, row_idx, data_row):
        # ... (код без изменений) ...
        category = data_row.get('category', 3)
        colors = {1: QColor("#FFC7CE"), 2: QColor("#FFEB9C"), 3: QColor("#C6EFCE")}; row_color = colors.get(category)
        style = QApplication.style()
        icons = {1: style.standardIcon(style.StandardPixmap.SP_MessageBoxCritical), 2: style.standardIcon(style.StandardPixmap.SP_MessageBoxWarning), 3: style.standardIcon(style.StandardPixmap.SP_MessageBoxInformation)}; status_icon = icons.get(category)
        for col_idx in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(col_idx); header_text = header_item.text() if header_item else ""
            item = QTableWidgetItem()
            if col_idx == 0:
                if status_icon: item.setIcon(status_icon); item.setTextAlignment(Qt.AlignCenter)
            elif col_idx == table.columnCount() - 1: item.setData(Qt.DisplayRole, category)
            else: item.setText(str(data_row.get(header_text, '')))
            if row_color: item.setBackground(row_color)
            table.setItem(row_idx, col_idx, item)

    def handle_item_changed(self, item):
        # ... (код без изменений) ...
        active_table = item.tableWidget(); row, column = item.row(), item.column()
        filename = self.get_filename_from_row(active_table, row)
        if not filename: return
        header_item = active_table.horizontalHeaderItem(column)
        if not header_item: return
        header_to_update, new_value = header_item.text(), item.text()
        old_value = self.all_data.get(filename, {}).get(header_to_update, '')
        if str(old_value) == new_value: return
        self.thread = QThread(); self.worker = DatabaseUpdateWorker(self.config, filename, header_to_update, new_value)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.thread.quit); self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater); self.worker.log_message.connect(self.log_window.add_log)
        self.thread.started.connect(self.worker.run); self.thread.start()
        if filename in self.all_data: self.all_data[filename][header_to_update] = new_value

    def start_analysis(self):
        # ... (код без изменений) ...
        reports_dir = self.reports_path_edit.text()
        if not os.path.isdir(reports_dir): QMessageBox.warning(self, "Ошибка", f"Папка '{reports_dir}' не найдена!"); return
        for w in [self.tabs, self.filter_panel, self.start_btn, self.open_file_btn, self.update_ip_btn]: w.setEnabled(False)
        self.stop_btn.setEnabled(True); self.all_data.clear()
        for w in list(self.details_windows.values()): w.close()
        for table in [self.main_table, self.network_table]: table.setRowCount(0)
        self.log_window.log_area.clear(); self.progress_bar.setValue(0); self.progress_bar.setVisible(True)
        self.thread = QThread(); self.worker = AidaWorker(reports_dir, self.config); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.log_message.connect(self.log_window.add_log)
        self.worker.progress_update.connect(self.update_progress); self.worker.result_ready.connect(self.add_table_row)
        self.worker.status_update.connect(self.update_status_bar); self.worker.finished.connect(self.analysis_finished)
        self.worker.finished.connect(self.thread.quit); self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater); self.thread.start()
        self.statusBar().showMessage("Анализ запущен...")

    def stop_analysis(self):
        # ... (код без изменений) ...
        if self.worker and hasattr(self.worker, 'is_running'):
            self.worker.is_running = False; self.stop_btn.setEnabled(False); self.statusBar().showMessage("Остановка анализа...")

    def analysis_finished(self, output_filepath):
        # ... (код без изменений) ...
        self.progress_bar.setVisible(False)
        for w in [self.tabs, self.filter_panel, self.start_btn, self.update_ip_btn]: w.setEnabled(True)
        self.stop_btn.setEnabled(False)
        for table in [self.main_table, self.network_table]: table.sortItems(table.columnCount() - 1, Qt.AscendingOrder)
        self.update_filter_combo(); self.filter_table()
        status_message = "Анализ успешно завершен!" if output_filepath else "Анализ завершен с ошибкой или был прерван."
        self.statusBar().showMessage(status_message, 5000)
        if output_filepath and os.path.exists(output_filepath): self.last_file_path = output_filepath; self.open_file_btn.setEnabled(True)
        if self.thread is not None: self.thread.quit(); self.thread.wait()
        self.thread = None; self.worker = None

    def update_status_bar(self, message, set_indeterminate):
        # ... (код без изменений) ...
        self.statusBar().showMessage(message); self.progress_bar.setRange(0, 0 if set_indeterminate else 100)
        
    def update_progress(self, current, total):
        # ... (код без изменений) ...
        self.progress_bar.setMaximum(total); self.progress_bar.setValue(current); self.statusBar().showMessage(f"Обработка файла {current} из {total}...")
        
    def get_filename_from_row(self, table, row):
        # ... (код без изменений) ...
        filename_col_index = -1
        for i in range(table.columnCount()):
            if table.horizontalHeaderItem(i) and table.horizontalHeaderItem(i).text() == "Имя файла": filename_col_index = i; break
        if filename_col_index != -1:
            item = table.item(row, filename_col_index); return item.text() if item else None
        return None
        
    def show_details_by_click(self, row, column):
        # ... (код без изменений) ...
        table = self.sender(); filename = self.get_filename_from_row(table, row)
        if filename in self.all_data: self.show_details_window(filename)

    def show_details_window(self, filename):
        # ... (код без изменений) ...
        if filename in self.details_windows: self.details_windows[filename].activateWindow(); self.details_windows[filename].raise_(); return
        if filename in self.all_data:
            details_win = DetailsWindow(self.all_data[filename], self.on_details_window_close, self)
            self.details_windows[filename] = details_win; details_win.show()

    def on_details_window_close(self, filename):
        # ... (код без изменений) ...
        if filename in self.details_windows: del self.details_windows[filename]

    def show_table_context_menu(self, position):
        # ... (код без изменений) ...
        active_table = self.tabs.currentWidget()
        if not isinstance(active_table, QTableWidget): return
        row_index = active_table.rowAt(position.y());
        if row_index < 0: return
        filename = self.get_filename_from_row(active_table, row_index)
        menu = QMenu()
        if filename: details_action = menu.addAction("Показать детали..."); details_action.triggered.connect(lambda: self.show_details_window(filename)); menu.addSeparator()
        edit_action = menu.addAction("Изменить ячейку")
        clicked_item = active_table.itemAt(position)
        if clicked_item:
            original_flags = clicked_item.flags(); clicked_item.setFlags(original_flags | Qt.ItemIsEditable)
            edit_action.triggered.connect(lambda ch, item=clicked_item: active_table.editItem(item)); menu.addSeparator()
        copy_menu = menu.addMenu("Копировать")
        for idx in range(1, active_table.columnCount() - 1):
            header_item = active_table.horizontalHeaderItem(idx); cell_item = active_table.item(row_index, idx)
            if header_item and cell_item and cell_item.text():
                action_text = f"{header_item.text()}: {cell_item.text()[:30]}{'...' if len(cell_item.text()) > 30 else ''}"
                copy_action = QAction(action_text, self); copy_action.triggered.connect(partial(QApplication.clipboard().setText, cell_item.text())); copy_menu.addAction(copy_action)
        if filename:
            menu.addSeparator(); open_report_action = menu.addAction(f"Открыть отчет {filename}"); open_report_action.triggered.connect(partial(self.open_and_select_report, filename))
        menu.exec(active_table.viewport().mapToGlobal(position))
        if clicked_item: clicked_item.setFlags(original_flags)
        
    def filter_table(self):
        # ... (код без изменений) ...
        active_table = self.tabs.currentWidget()
        if not isinstance(active_table, QTableWidget): return
        search_text, search_column_name = self.filter_edit.text().lower(), self.filter_column_combo.currentText()
        search_column_index = -1
        if search_column_name != "Поиск по всем полям":
            for i in range(active_table.columnCount()):
                if active_table.horizontalHeaderItem(i).text() == search_column_name: search_column_index = i; break
        for row in range(active_table.rowCount()):
            filename = self.get_filename_from_row(active_table, row)
            if not filename or filename not in self.all_data: active_table.setRowHidden(row, True); continue
            data, is_visible = self.all_data[filename], True
            if self.check_critical.isChecked() and data.get('category') != 1: is_visible = False
            if is_visible and self.check_upgrade.isChecked() and data.get('category') != 2: is_visible = False
            if is_visible and self.check_win7.isChecked() and "windows 7" not in str(data.get('ОС', '')).lower(): is_visible = False
            if is_visible and self.check_no_ssd.isChecked() and any(k in str(data.get('Дисковые накопители', '')).lower() for k in ['ssd', 'nvme', 'snv']): is_visible = False
            if is_visible and search_text:
                text_match = False
                if search_column_index != -1:
                    item = active_table.item(row, search_column_index)
                    if item and search_text in item.text().lower(): text_match = True
                else:
                    for col in range(active_table.columnCount()):
                        if active_table.isColumnHidden(col): continue
                        item = active_table.item(row, col)
                        if item and search_text in item.text().lower(): text_match = True; break
                if not text_match: is_visible = False
            active_table.setRowHidden(row, not is_visible)

    def on_tab_changed(self, index): self.update_filter_combo(); self.filter_table()

    def update_filter_combo(self):
        # ... (код без изменений) ...
        self.filter_column_combo.blockSignals(True); current_text = self.filter_column_combo.currentText()
        self.filter_column_combo.clear(); self.filter_column_combo.addItem("Поиск по всем полям")
        active_table = self.tabs.currentWidget()
        if isinstance(active_table, QTableWidget):
            visible_headers = [active_table.horizontalHeaderItem(i).text() for i in range(1, active_table.columnCount() - 1) if active_table.horizontalHeaderItem(i) and not active_table.isColumnHidden(i)]
            self.filter_column_combo.addItems(sorted(visible_headers))
        index = self.filter_column_combo.findText(current_text)
        if index != -1: self.filter_column_combo.setCurrentIndex(index)
        self.filter_column_combo.blockSignals(False)

    def reset_filters(self):
        # ... (код без изменений) ...
        for w in [self.filter_edit, self.filter_column_combo, self.check_critical, self.check_upgrade, self.check_no_ssd, self.check_win7]: w.blockSignals(True)
        self.filter_edit.clear(); self.filter_column_combo.setCurrentIndex(0)
        self.check_critical.setChecked(False); self.check_upgrade.setChecked(False); self.check_no_ssd.setChecked(False); self.check_win7.setChecked(False)
        for w in [self.filter_edit, self.filter_column_combo, self.check_critical, self.check_upgrade, self.check_no_ssd, self.check_win7]: w.blockSignals(False)
        self.filter_table()

    def select_folder(self):
        # ... (код без изменений) ...
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с отчетами AIDA64", self.reports_path_edit.text())
        if folder: self.reports_path_edit.setText(folder)

    def open_excel_file(self):
        # ... (код без изменений) ...
        if self.last_file_path and os.path.exists(self.last_file_path): QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(self.last_file_path)))
        else: QMessageBox.warning(self, "Файл не найден", f"Не удалось найти файл отчета: {self.last_file_path}")
    
    def open_and_select_report(self, filename):
        # ... (код без изменений) ...
        file_path = os.path.join(self.reports_path_edit.text(), filename)
        if os.path.exists(file_path): QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        else: QMessageBox.warning(self, "Ошибка", f"Файл отчета {file_path} не найден.")
            
    def save_settings(self):
        # ... (код без изменений) ...
        self.settings.setValue("geometry", self.saveGeometry()); self.settings.setValue("main_header_state", self.main_table.horizontalHeader().saveState())
        self.settings.setValue("network_header_state", self.network_table.horizontalHeader().saveState()); self.settings.setValue("current_tab_index", self.tabs.currentIndex())
        self.settings.setValue("filter_text", self.filter_edit.text())

    def load_settings(self):
        # ... (код без изменений) ...
        if self.settings.contains("geometry"): self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.contains("main_header_state"): self.main_table.horizontalHeader().restoreState(self.settings.value("main_header_state"))
        if self.settings.contains("network_header_state"): self.network_table.horizontalHeader().restoreState(self.settings.value("network_header_state"))
        index = self.settings.value("current_tab_index", type=int)
        if self.settings.contains("current_tab_index") and index < self.tabs.count(): self.tabs.setCurrentIndex(index)
        if self.settings.contains("filter_text"): self.filter_edit.setText(self.settings.value("filter_text"))

    def closeEvent(self, event):
        # ... (код без изменений) ...
        self.save_settings(); logging.info("Получен сигнал закрытия окна.")
        self.stop_analysis()
        if self.thread and self.thread.isRunning():
            logging.info("Ожидание завершения рабочего потока..."); self.thread.quit(); self.thread.wait()
        for window in list(self.details_windows.values()): window.close()
        self.log_window.close(); event.accept()