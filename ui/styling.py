# ЗАМЕНИТЬ ПОЛНОСТЬЮ ФАЙЛ ui/styling.py

def get_graphite_theme():
    return """
    QWidget { background-color: #2b2b2b; color: #dcdcdc; font-family: Calibri; font-size: 10pt; border: none; }
    QMainWindow, QDialog, QWidget#detailsWindow, QWidget#logWindow { background-color: #2b2b2b; }
    QTabWidget::pane { border: 1px solid #4a4a4a; border-radius: 4px; }
    QTabBar::tab { background: #3c3f41; color: #dcdcdc; padding: 8px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; border: 1px solid #4a4a4a; border-bottom: none; margin-right: 2px; }
    QTabBar::tab:selected { background: #007acc; color: white; }
    QTabBar::tab:hover { background: #4d4d4d; }
    QTableWidget { background-color: #3c3f41; border: 1px solid #4a4a4a; gridline-color: #4a4a4a; }
    QTableWidget::item:selected { background-color: #007acc; color: white; }
    QHeaderView::section { background-color: #2b2b2b; padding: 5px; border: 1px solid #4a4a4a; font-weight: bold; }
    QTableCornerButton::section { background-color: #2b2b2b; border: 1px solid #4a4a4a; }
    
    /* --- НОВЫЙ, ПРАВИЛЬНЫЙ СТИЛЬ ДЛЯ РАЗДЕЛОВ --- */
    QGroupBox {
        border: 1px solid #4a4a4a;
        border-radius: 5px;
        margin-top: 1em; /* отступ СВЕРХУ, чтобы заголовок не прилипал */
        font-weight: bold;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center; /* Позиция заголовка */
        padding: 0 5px;
        background-color: #2b2b2b; /* тот же фон, что и у окна */
    }
    
    QPushButton { background-color: #3c3f41; border: 1px solid #5a5a5a; padding: 6px; border-radius: 4px; }
    QPushButton:hover { background-color: #4d4d4d; border: 1px solid #007acc; }
    QPushButton:pressed { background-color: #005a9c; }
    QPushButton#startBtn { font-weight: bold; background-color: #2d5a2d; border: 1px solid #3c7a3c; }
    QPushButton#startBtn:hover { background-color: #3c7a3c; }
    QLineEdit, QComboBox { background-color: #3c3f41; border: 1px solid #5a5a5a; padding: 5px; border-radius: 4px; }
    QProgressBar { border: 1px solid #5a5a5a; border-radius: 4px; text-align: center; background-color: #3c3f41; color: #dcdcdc; }
    QProgressBar::chunk { background-color: #007acc; border-radius: 3px; margin: 1px; }
    QFrame#filterPanel { border: none; }
    QStatusBar { font-size: 9pt; }
    QMenu { background-color: #3c3f41; border: 1px solid #5a5a5a; }
    QMenu::item:selected { background-color: #007acc; }
    QScrollBar:vertical { border: none; background: #2b2b2b; width: 10px; margin: 0px 0px 0px 0px; }
    QScrollBar::handle:vertical { background: #4d4d4d; min-height: 20px; border-radius: 5px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar:horizontal { border: none; background: #2b2b2b; height: 10px; margin: 0px 0px 0px 0px; }
    QScrollBar::handle:horizontal { background: #4d4d4d; min-width: 20px; border-radius: 5px; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
    #titleBar { background-color: #2b2b2b; }
    #titleBar QPushButton { background-color: transparent; border: none; padding: 4px; border-radius: 0px; }
    #titleBar QPushButton:hover { background-color: #4d4d4d; }
    #closeButton:hover { background-color: #e81123; }
    #titleLabel { font-weight: bold; padding-left: 5px; }
    """
