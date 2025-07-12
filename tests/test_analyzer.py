# tests/test_analyzer.py
import configparser
from logic.analyzer import analyze_system

# Создаем базовый конфиг для тестов
config = configparser.ConfigParser()
config.read_string("""
[Analysis]
bios_age_limit_years = 5
ram_critical_gb = 3.8
ram_upgrade_gb = 7.8
""")

def test_perfect_pc():
    """Тест: Идеальный ПК должен получить категорию 3."""
    pc_data = {
        'ОС': 'Windows 11 Pro',
        'Сокет': 'AM4',
        'Объем ОЗУ': '16 ГБ',
        'Дисковые накопители': 'NVMe SSD 1TB',
        'Видеоадаптер': 'NVIDIA GeForce RTX 3070',
        'Дата BIOS': '10/10/2023',
        'internal_smart_status': 'GOOD',
        'SMART Проблемы': []
    }
    category, problems = analyze_system(pc_data, config)
    assert category == 3
    assert "хорошее" in problems

def test_ancient_pc():
    """Тест: Очень старый ПК должен получить категорию 1."""
    pc_data = {
        'ОС': 'Windows 7',
        'Сокет': 'LGA775',
        'Объем ОЗУ': '2 ГБ',
        'Дисковые накопители': 'HDD 120GB',
        'Видеоадаптер': 'NVIDIA GeForce 8600 GT',
        'Дата BIOS': '01/01/2010',
        'internal_smart_status': 'GOOD',
        'SMART Проблемы': []
    }
    category, problems = analyze_system(pc_data, config)
    assert category == 1
    assert "Критично: Очень старая платформа" in problems
    assert "Критично: Мало ОЗУ" in problems
