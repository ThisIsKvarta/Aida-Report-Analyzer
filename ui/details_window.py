# ui/details_window.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QGroupBox, QLabel,
                               QLineEdit, QTextEdit) # Добавлен QTextEdit
from PySide6.QtCore import Qt

class DetailsWindow(QWidget):
    def __init__(self, data, on_close_callback, parent=None):
        super().__init__(parent)
        self.data = data
        self.on_close_callback = on_close_callback

        pc_name = self.data.get('Название ПК', 'N/A')
        self.setWindowTitle(f"Карточка компьютера: {pc_name}")
        self.setGeometry(150, 150, 550, 650)
        self.setWindowFlags(self.windowFlags() | Qt.Window)

        self.main_layout = QVBoxLayout(self)
        self.setup_ui()

    def create_readonly_lineedit(self, text):
        """Создает нередактируемое поле с текстом и рамкой."""
        line_edit = QLineEdit(str(text) if text is not None else "")
        line_edit.setReadOnly(True)
        line_edit.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 3px; padding: 2px;")
        return line_edit
    
    # НОВЫЙ МЕТОД
    def create_readonly_textedit(self, text):
        """Создает нередактируемое многострочное поле с автовысотой."""
        text_edit = QTextEdit(str(text) if text is not None else "")
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 3px; padding: 2px;")
        
        # Автоматическая подстройка высоты по содержимому
        text_edit.document().setTextWidth(text_edit.viewport().width())
        height = text_edit.document().size().height()
        text_edit.setFixedHeight(int(height) + 15) # +15 для небольшого запаса
        
        return text_edit

    # ИЗМЕНЕННЫЙ МЕТОД
    def setup_ui(self):
        # Группа "Общая информация"
        general_group = QGroupBox("Общая информация")
        general_layout = QFormLayout(general_group)
        general_layout.addRow("Имя файла:", self.create_readonly_lineedit(self.data.get('Имя файла')))
        general_layout.addRow("Название ПК:", self.create_readonly_lineedit(self.data.get('Название ПК')))
        general_layout.addRow("Операционная система:", self.create_readonly_textedit(self.data.get('ОС'))) # ИЗМЕНЕНО
        general_layout.addRow("Дата BIOS:", self.create_readonly_lineedit(self.data.get('Дата BIOS')))
        self.main_layout.addWidget(general_group)

        # Группа "Процессор и память"
        cpu_ram_group = QGroupBox("Процессор и память")
        cpu_ram_layout = QFormLayout(cpu_ram_group)
        cpu_ram_layout.addRow("Процессор:", self.create_readonly_textedit(self.data.get('Процессор'))) # ИЗМЕНЕНО
        cpu_ram_layout.addRow("Сокет:", self.create_readonly_lineedit(self.data.get('Сокет')))
        cpu_ram_layout.addRow("Материнская плата:", self.create_readonly_textedit(self.data.get('Материнская плата'))) # ИЗМЕНЕНО
        cpu_ram_layout.addRow("Объем ОЗУ:", self.create_readonly_lineedit(self.data.get('Объем ОЗУ')))
        cpu_ram_layout.addRow("Модели плашек:", self.create_readonly_textedit(self.data.get('Модели плашек ОЗУ'))) # ИЗМЕНЕНО
        self.main_layout.addWidget(cpu_ram_group)
        
        # Группа "Накопители и SMART"
        disk_group = QGroupBox("Накопители и SMART")
        disk_layout = QFormLayout(disk_group)
        disk_layout.addRow("Дисковые накопители:", self.create_readonly_textedit(self.data.get('Дисковые накопители'))) # ИЗМЕНЕНО
        
        internal_status = self.data.get('internal_smart_status', 'GOOD')
        smart_display_text = self.data.get('SMART Статус', internal_status)
        
        smart_status_label = QLabel(smart_display_text)
        status_color = {"BAD": "#9C0006", "OK": "#9C6500", "GOOD": "green"}
        smart_status_label.setStyleSheet(f"color: {status_color.get(internal_status, 'black')}; font-weight: bold;")
        smart_status_label.setWordWrap(True)
        disk_layout.addRow("SMART Статус:", smart_status_label)
        self.main_layout.addWidget(disk_group)
        
        # Группа "Проблемы и рекомендации"
        issues_group = QGroupBox("Проблемы и рекомендации")
        issues_layout = QFormLayout(issues_group)
        
        category = self.data.get('category', 3)
        category_map = {1: "Категория 1: Полная замена", 2: "Категория 2: Частичный апгрейд", 3: "Категория 3: В порядке"}
        category_label = QLabel(category_map.get(category, "Неизвестно"))
        category_color = {1: "#FFC7CE", 2: "#FFEB9C", 3: "#C6EFCE"}
        category_label.setStyleSheet(f"background-color: {category_color.get(category, '#ffffff')}; padding: 3px; font-weight: bold; border-radius: 3px;")
        
        issues_layout.addRow("Категория:", category_label)
        issues_layout.addRow("Ключевые проблемы:", self.create_readonly_textedit(self.data.get('problems'))) # ИЗМЕНЕНО
        self.main_layout.addWidget(issues_group)

        self.main_layout.addStretch()

    def closeEvent(self, event):
        """Вызывается при закрытии окна"""
        if self.on_close_callback:
            self.on_close_callback(self.data.get('Имя файла'))
        super().closeEvent(event)