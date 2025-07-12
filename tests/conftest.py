# tests/conftest.py
import sys
import os

# Добавляем корневую папку проекта в путь,
# чтобы pytest мог найти модуль 'logic'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))