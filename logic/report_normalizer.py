# logic/report_normalizer.py
import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def normalize_html_report(html_content: str, filename: str) -> str:
    """Простая функция, которая ничего не делает, но нужна для импорта."""
    # Мы пока отключаем нормализацию, чтобы убедиться, что проблема не в ней.
    # logger.info(f"Нормализация отключена для: {filename}")
    return html_content