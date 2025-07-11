# ui/details_window.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QGroupBox, QLabel,
                               QLineEdit, QTextEdit)
from PySide6.QtCore import Qt

class DetailsWindow(QWidget):
    # --- ИЗМЕНЕНО: Добавляем stylesheet в конструктор ---
    def __init__(self, data, on_close_callback, stylesheet, parent=None):
        super().__init__(parent)
        self.data = data
        self.on_close_callback = on_close_callback
        
        # --- Применяем стиль ---
        self.setStyleSheet(stylesheet)
        self.setObjectName("detailsWindow") # ID для стилизации

        pc_name = self.data.get('Название ПК', 'N/A')
        self.setWindowTitle(f"Карточка компьютера: {pc_name}")
        self.setGeometry(150, 150, 550, 700) # Увеличим высоту
        self.setWindowFlags(self.windowFlags() | Qt.Window)

        self.main_layout = QVBoxLayout(self)
        self.setup_ui()

    def create_readonly_lineedit(self, text):
        line_edit = QLineEdit(str(text) if text is not None else "")
        line_edit.setReadOnly(True)
        # Убираем инлайновые стили, все будет в QSS
        return line_edit
    
    def create_readonly_textedit(self, text):
        text_edit = QTextEdit(str(text) if text is not None else "")
        text_edit.setReadOnly(True)
        # Убираем инлайновые стили
        text_edit.document().setTextWidth(text_edit.viewport().width())
        height = text_edit.document().size().height()
        text_edit.setFixedHeight(int(height) + 15)
        return text_edit

    def setup_ui(self):
        # ... (здесь код не меняется, но теперь он будет выглядеть по-новому) ...
        general_group = QGroupBox("Общая информация")
        general_layout = QFormLayout(general_group)
        general_layout.addRow("Имя файла:", self.create_readonly_lineedit(self.data.get('Имя файла')))
        general_layout.addRow("Название ПК:", self.create_readonly_lineedit(self.data.get('Название ПК')))
        general_layout.addRow("Операционная система:", self.create_readonly_textedit(self.data.get('ОС')))
        general_layout.addRow("Дата BIOS:", self.create_readonly_lineedit(self.data.get('Дата BIOS')))
        self.main_layout.addWidget(general_group)
        
        cpu_ram_group = QGroupBox("Процессор и память")
        cpu_ram_layout = QFormLayout(cpu_ram_group)
        cpu_ram_layout.addRow("Процессор:", self.create_readonly_textedit(self.data.get('Процессор')))
        cpu_ram_layout.addRow("Сокет:", self.create_readonly_lineedit(self.data.get('Сокет')))
        cpu_ram_layout.addRow("Материнская плата:", self.create_readonly_textedit(self.data.get('Материнская плата')))
        cpu_ram_layout.addRow("Объем ОЗУ:", self.create_readonly_lineedit(self.data.get('Объем ОЗУ')))
        cpu_ram_layout.addRow("Модели плашек:", self.create_readonly_textedit(self.data.get('Модели плашек ОЗУ')))
        self.main_layout.addWidget(cpu_ram_group)
        
        disk_group = QGroupBox("Накопители и SMART")
        disk_layout = QFormLayout(disk_group)
        disk_layout.addRow("Дисковые накопители:", self.create_readonly_textedit(self.data.get('Дисковые накопители')))
        smart_display_text = self.data.get('SMART Статус', self.data.get('internal_smart_status', 'GOOD'))
        smart_status_label = QLabel(smart_display_text)
        status_color = {"BAD": "#e57373", "OK": "#fff176", "GOOD": "#81c784"}
        smart_status_label.setStyleSheet(f"color: {status_color.get(self.data.get('internal_smart_status', 'GOOD'), 'white')}; font-weight: bold;")
        smart_status_label.setWordWrap(True)
        disk_layout.addRow("SMART Статус:", smart_status_label)
        self.main_layout.addWidget(disk_group)
        
        issues_group = QGroupBox("Проблемы и рекомендации")
        issues_layout = QFormLayout(issues_group)
        category_map = {1: "Категория 1: Полная замена", 2: "Категория 2: Частичный апгрейд", 3: "Категория 3: В порядке"}
        category_label = QLabel(category_map.get(self.data.get('category', 3), "Неизвестно"))
        category_color = {1: "#5c2c2c", 2: "#5c532c", 3: "#2c5c2c"}
        category_label.setStyleSheet(f"background-color: {category_color.get(self.data.get('category', 3), '#3c3f41')}; padding: 4px; font-weight: bold; border-radius: 4px;")
        issues_layout.addRow("Категория:", category_label)
        issues_layout.addRow("Ключевые проблемы:", self.create_readonly_textedit(self.data.get('problems')))
        self.main_layout.addWidget(issues_group)

        self.main_layout.addStretch()

    def closeEvent(self, event):
        if self.on_close_callback: self.on_close_callback(self.data.get('Имя файла'))
        super().closeEvent(event)