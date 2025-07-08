# ui/log_window.py
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit

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