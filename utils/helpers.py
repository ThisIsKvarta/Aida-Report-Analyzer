# utils/helpers.py
import re

def natural_sort_key(s):
    """
    Ключ для "естественной" сортировки строк (например, 'file10' идет после 'file2').
    Устойчив к None.
    """
    if s is None:
        return [] # Возвращаем пустой список для None, он будет в начале сортировки
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]