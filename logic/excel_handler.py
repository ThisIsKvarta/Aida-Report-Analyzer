# ЗАМЕНИТЬ ПОЛНОСТЬЮ ФАЙЛ logic/excel_handler.py

import logging
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.cell import MergedCell
from openpyxl.chart import PieChart, BarChart, Reference
from utils.constants import HEADERS_MAIN, HEADERS_NETWORK, HEADERS_ANALYSIS

logger = logging.getLogger(__name__)

def write_to_excel(data_list, filename, log_emitter):
    if not data_list:
        log_emitter("Нет данных для экспорта в Excel.", "warning")
        return
        
    wb = Workbook()
    
    # --- СТИЛИ ---
    header_font = Font(bold=True, color="FFFFFF", name='Calibri', size=11)
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    data_font = Font(name='Calibri', size=11)
    data_alignment = Alignment(vertical='top', wrap_text=True, horizontal='left')
    cat1_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    cat1_font = Font(color="9C0006", name='Calibri', size=11)
    cat2_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    cat2_font = Font(color="9C6500", name='Calibri', size=11)
    cat3_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    smart_bad_font = Font(bold=True, color="9C0006", name='Calibri', size=11)

    # --- ЛИСТ 1: ВСЕ ДАННЫЕ ---
    ws_main = wb.active
    ws_main.title = "Все данные"
    
    # Создаем ЕДИНЫЙ и ПРАВИЛЬНЫЙ порядок колонок для Excel
    final_headers = list(HEADERS_MAIN)
    if '_RAW_DATA' in final_headers:
        final_headers.remove('_RAW_DATA')
    for h in HEADERS_NETWORK:
        if h not in final_headers:
            final_headers.append(h)
    
    # Записываем заголовки
    ws_main.append(final_headers)
    for cell in ws_main[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Заполняем данные
    for data_row in data_list:
        # Собираем значения, используя тот же самый список final_headers
        row_values = [data_row.get(h, '') for h in final_headers]
        ws_main.append(row_values)
        
        row_idx = ws_main.max_row
        category = data_row.get('category', 3)
        row_fill, row_font = {
            1: (cat1_fill, cat1_font),
            2: (cat2_fill, cat2_font),
            3: (cat3_fill, data_font)
        }.get(category, (None, data_font))
        
        for col_idx, cell in enumerate(ws_main[row_idx], 1):
            cell.font = row_font
            cell.alignment = data_alignment
            cell.border = thin_border
            if row_fill:
                cell.fill = row_fill
        
        # Особо выделяем плохой SMART
        try:
            smart_cell_index = final_headers.index('SMART Статус') + 1
            smart_cell = ws_main.cell(row=row_idx, column=smart_cell_index)
            if data_row.get('internal_smart_status') == 'BAD':
                smart_cell.font = smart_bad_font
        except (ValueError, IndexError):
            pass  # Колонка 'SMART Статус' может отсутствовать

    # Настраиваем ширину колонок
    for i, header_text in enumerate(final_headers, 1):
        column_letter = get_column_letter(i)
        max_length = len(header_text)
        for cell in ws_main[column_letter]:
            if cell.value:
                # Учитываем переводы строк
                cell_lines = str(cell.value).split('\n')
                max_length = max(max_length, *[len(line) for line in cell_lines])
        adjusted_width = min(max_length + 2, 60)
        ws_main.column_dimensions[column_letter].width = adjusted_width
        
    ws_main.freeze_panes = 'A2'
    
    # --- ЛИСТ 2: РЕКОМЕНДАЦИИ ---
    ws_analysis = wb.create_sheet("Рекомендации")
    cat_font = Font(bold=True, name='Calibri', size=12)
    for cat_num, cat_name, cat_fill in [(1, 'Категория 1: Полная замена', cat1_fill), (2, 'Категория 2: Частичный апгрейд', cat2_fill)]:
        ws_analysis.append([cat_name])
        merged_cell_header = ws_analysis.cell(row=ws_analysis.max_row, column=1)
        merged_cell_header.font = cat_font
        merged_cell_header.fill = cat_fill
        ws_analysis.merge_cells(start_row=ws_analysis.max_row, start_column=1, end_row=ws_analysis.max_row, end_column=len(HEADERS_ANALYSIS))
        
        ws_analysis.append(HEADERS_ANALYSIS)
        for cell in ws_analysis[ws_analysis.max_row]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
            
        for data in data_list:
            if data.get('category') == cat_num:
                # Формируем рекомендации
                rec_list = []
                problems_str = str(data.get('problems', '')).lower()
                if data.get('internal_smart_status') == "BAD":
                    rec_list.append("ЗАМЕНА ДИСКА!")
                elif cat_num == 1:
                    rec_list.append("Полная замена")
                else: # Категория 2
                    if 'ос' in problems_str or 'windows 7' in problems_str: rec_list.append("Обновить ОС")
                    if 'ssd' in problems_str: rec_list.append("Установить SSD")
                    if 'озу' in problems_str: rec_list.append("Добавить ОЗУ")
                    if 'видеодрайвер' in problems_str: rec_list.append("Установить видеодрайвер")
                    if 'bios' in problems_str: rec_list.append("Обновить BIOS (опционально)")

                rec = ", ".join(rec_list) if rec_list else "Частичный апгрейд"
                
                row_data = [
                    data.get('Имя файла', ''),
                    data.get('Название ПК', ''),
                    data.get('problems', ''),
                    rec
                ]
                ws_analysis.append(row_data)
        ws_analysis.append([]) # Пустая строка для разделения
        
    for col_idx in range(1, ws_analysis.max_column + 1):
        col_letter = get_column_letter(col_idx)
        max_length = max((len(str(cell.value)) for cell in ws_analysis[col_letter] if cell.value and not isinstance(cell, MergedCell)), default=0)
        ws_analysis.column_dimensions[col_letter].width = max(max_length + 2, 20)
            
    # --- ЛИСТ 3: ДАШБОРД (без изменений) ---
    ws_dash = wb.create_sheet("Дашборд")
    # ... (код для дашборда можно добавить позже) ...

    # --- Сохранение файла ---
    try:
        wb.save(filename)
        log_emitter(f"Файл Excel '{filename}' успешно сохранен.", "info")
    except IOError as e:
        log_emitter(f"Ошибка: Не удалось записать в файл {filename}. Возможно, он открыт в другой программе. Ошибка: {e}", "error")
        logger.error(f"Ошибка ввода/вывода при сохранении Excel-файла '{filename}': {e}", exc_info=True)