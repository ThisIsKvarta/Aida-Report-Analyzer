# ЗАМЕНИТЬ ПОЛНОСТЬЮ ФАЙЛ ui/details_window.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QGroupBox, QLabel,
                               QLineEdit, QSizePolicy, QFrame, QScrollArea)
from PySide6.QtCore import Qt

def create_multiline_label(text):
    """Создает QLabel, который выглядит как поле ввода и правильно обрабатывает многострочный текст."""
    label = QLabel(str(text) if text is not None else "")
    label.setWordWrap(True) 
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    # Стилизуем под QLineEdit из темы, чтобы все выглядело одинаково
    label.setStyleSheet("""
        QLabel {
            background-color: #3c3f41;
            border: 1px solid #5a5a5a;
            padding: 5px;
            border-radius: 4px;
            min-height: 22px; /* Минимальная высота как у QLineEdit */
        }
    """)
    label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
    return label

class DetailsWindow(QWidget):
    def __init__(self, data, on_close_callback, stylesheet, parent=None):
        super().__init__(parent)
        self.data = data
        self.on_close_callback = on_close_callback
        
        # Глобальный стиль будет применен здесь
        self.setStyleSheet(stylesheet)
        self.setObjectName("detailsWindow")

        pc_name = self.data.get('Название ПК', 'N/A')
        self.setWindowTitle(f"Карточка компьютера: {pc_name}")
        self.setGeometry(150, 150, 550, 700)
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setup_ui()

    def create_readonly_lineedit(self, text):
        line_edit = QLineEdit(str(text) if text is not None else "")
        line_edit.setReadOnly(True)
        return line_edit

    def setup_ui(self):
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        # Добавляем немного "воздуха" по краям
        content_layout.setContentsMargins(10, 0, 10, 10)
        
        general_group = QGroupBox("Общая информация")
        general_layout = QFormLayout(general_group)
        general_layout.addRow("Имя файла:", self.create_readonly_lineedit(self.data.get('Имя файла')))
        general_layout.addRow("Название ПК:", self.create_readonly_lineedit(self.data.get('Название ПК')))
        general_layout.addRow("Операционная система:", create_multiline_label(self.data.get('ОС')))
        general_layout.addRow("Дата BIOS:", self.create_readonly_lineedit(self.data.get('Дата BIOS')))
        content_layout.addWidget(general_group)
        
        cpu_ram_group = QGroupBox("Процессор и память")
        cpu_ram_layout = QFormLayout(cpu_ram_group)
        cpu_ram_layout.addRow("Процессор:", create_multiline_label(self.data.get('Процессор')))
        cpu_ram_layout.addRow("Сокет:", self.create_readonly_lineedit(self.data.get('Сокет')))
        cpu_ram_layout.addRow("Материнская плата:", create_multiline_label(self.data.get('Материнская плата')))
        cpu_ram_layout.addRow("Объем ОЗУ:", self.create_readonly_lineedit(self.data.get('Объем ОЗУ')))
        cpu_ram_layout.addRow("Модели плашек:", create_multiline_label(self.data.get('Модели плашек ОЗУ')))
        content_layout.addWidget(cpu_ram_group)
        
        disk_group = QGroupBox("Накопители и SMART")
        disk_layout = QFormLayout(disk_group)
        disk_layout.addRow("Дисковые накопители:", create_multiline_label(self.data.get('Дисковые накопители')))
        disk_layout.addRow("SMART Статус:", create_multiline_label(self.data.get('SMART Статус')))
        content_layout.addWidget(disk_group)
        
        issues_group = QGroupBox("Проблемы и рекомендации")
        issues_layout = QFormLayout(issues_group)
        category_map = {1: "Категория 1: Полная замена", 2: "Категория 2: Частичный апгрейд", 3: "Категория 3: В порядке"}
        category_label = QLabel(category_map.get(self.data.get('category', 3), "Неизвестно"))
        category_label.setStyleSheet("background-color: transparent; border: none; font-weight: bold;")
        category_color = {1: "#e57373", 2: "#fff176", 3: "#81c784"}
        category_label.setStyleSheet(f"color: {category_color.get(self.data.get('category', 3), 'white')}; font-weight: bold; background: none; border: none;")
        issues_layout.addRow("Категория:", category_label)
        issues_layout.addRow("Ключевые проблемы:", create_multiline_label(self.data.get('problems')))
        content_layout.addWidget(issues_group)

        content_layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def closeEvent(self, event):
        if self.on_close_callback: self.on_close_callback(self.data.get('Имя файла'))
        super().closeEvent(event)