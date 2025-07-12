import os
import logging
import platform
import re
import socket
import subprocess
from threading import Thread

import psutil
from PySide6.QtCore import QObject, Signal

# --- НОВЫЕ ИМПОРТЫ ---
from logic.parser import parse_aida_report
from logic.analyzer import analyze_system # Импортируем анализатор
from logic.excel_handler import write_to_excel
from logic.database_handler import save_data_to_db, fetch_all_data_from_db, update_single_field_in_db
from utils.helpers import natural_sort_key

logger = logging.getLogger(__name__)

class AidaWorker(QObject):
    log_message = Signal(str, str); progress_update = Signal(int, int); status_update = Signal(str, bool); result_ready = Signal(dict); finished = Signal(str) 
    def __init__(self, reports_dir, config): super().__init__(); self.reports_dir = reports_dir; self.config = config; self.is_running = True
    def run(self):
        try:
            output_file = self.config.get('Settings', 'output_filename', fallback='system_analysis.xlsx'); report_files = [f for f in os.listdir(self.reports_dir) if f.lower().endswith(('.htm', '.html'))]
            if not report_files: self.log_message.emit("В указанной папке не найдено файлов отчетов .htm/.html.", "warning"); self.finished.emit(""); return
            self.log_message.emit(f"Найдено отчетов: {len(report_files)}", "info"); all_reports_data = []; total_files = len(report_files)
            
            for i, filename in enumerate(report_files):
                if not self.is_running: break
                self.progress_update.emit(i + 1, total_files)
                file_path = os.path.join(self.reports_dir, filename)
                
                # --- ИЗМЕНЕННАЯ ЛОГИКА ---
                # Шаг 1: Получаем только "сырые" данные из парсера
                raw_data = parse_aida_report(file_path, self.config, self.log_message.emit)
                
                if raw_data:
                    # Шаг 2: Передаем сырые данные в анализатор
                    category, problems_text = analyze_system(raw_data, self.config)
                    
                    # Шаг 3: Дополняем словарь результатами анализа
                    raw_data['category'] = category
                    raw_data['problems'] = problems_text
                    
                    self.result_ready.emit(raw_data)
                    all_reports_data.append(raw_data)
            
            if not self.is_running: self.log_message.emit("Процесс анализа был прерван пользователем.", "warning"); self.finished.emit(""); return
            
            self.status_update.emit("Сохранение данных в базу...", True); save_data_to_db(all_reports_data); self.status_update.emit("Экспорт в Excel...", True)
            
            all_data_from_db = fetch_all_data_from_db(); all_data_from_db.sort(key=lambda item: natural_sort_key(item.get('Имя файла')))
            
            write_to_excel(all_data_from_db, output_file, self.log_message.emit); self.finished.emit(output_file)
        except Exception as e:
            self.log_message.emit(f"КРИТИЧЕСКАЯ ОШИБКА в потоке анализа: {e}", "error"); logger.error(f"Критическая ошибка в потоке AidaWorker: {e}", exc_info=True); self.finished.emit("")
class DatabaseUpdateWorker(QObject):
    log_message = Signal(str, str); finished = Signal()
    def __init__(self, config, unique_id, header_to_update, new_value): super().__init__(); self.config = config; self.unique_id = unique_id; self.header = header_to_update; self.new_value = new_value
    def run(self):
        try:
            if update_single_field_in_db(self.unique_id, self.header, self.new_value):
                self.log_message.emit(f"Ячейка '{self.header}' для '{self.unique_id}' обновлена в БД.", "info"); output_file = self.config.get('Settings', 'output_filename', fallback='system_analysis.xlsx')
                all_data = fetch_all_data_from_db(); all_data.sort(key=lambda item: natural_sort_key(item.get('Имя файла', '')))
                write_to_excel(all_data, output_file, self.log_message.emit); self.log_message.emit("Файл Excel обновлен.", "info")
            else: self.log_message.emit(f"Не удалось обновить ячейку '{self.header}' для '{self.unique_id}'.", "error")
        except Exception as e: self.log_message.emit(f"Ошибка при обновлении БД: {e}", "error"); logger.error(f"Ошибка обновления БД: {e}", exc_info=True)
        finally: self.finished.emit()

class FullExcelExportWorker(QObject):
    log_message = Signal(str, str); finished = Signal(str)
    def __init__(self, config): super().__init__(); self.config = config
    def run(self):
        try:
            self.log_message.emit("Экспорт всех данных в Excel запущен...", "info"); output_file = self.config.get('Settings', 'output_filename', fallback='system_analysis.xlsx')
            all_data = fetch_all_data_from_db(); all_data.sort(key=lambda item: natural_sort_key(item.get('Имя файла', '')))
            write_to_excel(all_data, output_file, self.log_message.emit); self.finished.emit(output_file)
        except Exception as e:
            self.log_message.emit(f"Ошибка при экспорте в Excel: {e}", "error"); logger.error(f"Ошибка при экспорте в Excel: {e}", exc_info=True); self.finished.emit("")


class IPUpdateWorker(QObject):
    log_message = Signal(str, str)
    finished = Signal()

    IGNORE_KEYWORDS = ['loopback', 'teredo', 'isatap', 'virtual', 'vmware', 'vbox', 'radmin', 'hamachi', 'tap-windows', 'hyper-v', 'wsl', 'vethernet']
    PHYSICAL_KEYWORDS = ['ethernet', 'wi-fi', 'беспроводная', 'локальной сети']

    def _get_local_net_info(self):
        self.log_message.emit("Начинаю интеллектуальный поиск сетевого адаптера...", "info")
        try:
            all_interfaces = psutil.net_if_addrs()
            candidate_adapters = []
            
            self.log_message.emit("-> Этап 1: Фильтрация по черному списку...", "debug")
            for name, addresses in all_interfaces.items():
                if any(keyword in name.lower() for keyword in self.IGNORE_KEYWORDS):
                    self.log_message.emit(f"--> Игнорирую: '{name}' (содержит запрещенное слово).", "debug"); continue
                
                ip_addr, mac_addr = None, None
                for addr in addresses:
                    if addr.family == socket.AF_INET and not addr.address.startswith('169.254.'): ip_addr = addr.address
                    if addr.family == psutil.AF_LINK or str(addr.family) == 'AddressFamily.AF_PACKET': mac_addr = addr.address
                
                if ip_addr and mac_addr:
                    candidate_adapters.append({'name': name, 'ip': ip_addr, 'mac': mac_addr.upper().replace(':', '-')})
                    self.log_message.emit(f"--> Кандидат: '{name}' с IP {ip_addr} и MAC {mac_addr}", "debug")

            if not candidate_adapters:
                self.log_message.emit("Не найдено ни одного подходящего сетевого адаптера после фильтрации!", "error"); return None
            
            self.log_message.emit("-> Этап 2: Выбор лучшего из кандидатов...", "debug")
            for adapter in candidate_adapters:
                if any(keyword in adapter['name'].lower() for keyword in self.PHYSICAL_KEYWORDS):
                    subnet = ".".join(adapter['ip'].split('.')[:-1]) + ".0/24"
                    self.log_message.emit(f"✔️ Найден приоритетный адаптер: '{adapter['name']}' с IP: {adapter['ip']}", "info")
                    return {'ip': adapter['ip'], 'mac': adapter['mac'], 'subnet': subnet}
            
            first_adapter = candidate_adapters[0]
            subnet = ".".join(first_adapter['ip'].split('.')[:-1]) + ".0/24"
            self.log_message.emit(f"✔️ Выбран первый доступный адаптер: '{first_adapter['name']}' с IP: {first_adapter['ip']}", "warning")
            return {'ip': first_adapter['ip'], 'mac': first_adapter['mac'], 'subnet': subnet}
        except Exception as e:
            self.log_message.emit(f"Критическая ошибка при поиске сетевого адаптера: {e}", "error"); return None

    def _warm_up_arp_cache(self, subnet):
        command, is_windows = [], platform.system().lower() == "windows"
        try:
            subprocess.run(['nmap', '-V'], capture_output=True, check=True); command = ['nmap', '-sn', '-PR', subnet]
            self.log_message.emit(f"Использую nmap для сканирования сети: {' '.join(command)}", "info")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_message.emit("nmap не найден. Использую стандартный ping (может быть медленнее).", "warning")
            if is_windows:
                base_ip = ".".join(subnet.split('.')[:-1]);
                for i in range(1, 255): subprocess.Popen(['ping', '-n', '1', '-w', '100', f"{base_ip}.{i}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.log_message.emit("Запущен пинг всех адресов в сети (это может занять до минуты)...", "debug"); import time; time.sleep(60)
            else: self.log_message.emit("Для Linux/macOS рекомендуется установить nmap для быстрого сканирования.", "warning")
        if command:
            try: subprocess.run(command, capture_output=True, text=True, check=True, timeout=90)
            except Exception as e: self.log_message.emit(f"Ошибка при выполнении команды сканирования: {e}", "error")

    def _get_arp_table(self):
        try:
            self.log_message.emit("Получаю ARP-таблицу системы...", "debug")
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, check=True, encoding='cp866' if platform.system().lower() == 'windows' else 'utf-8')
            mac_ip_map = {}
            pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2})")
            for line in result.stdout.splitlines():
                match = pattern.search(line.lower())
                if match: mac_ip_map[match.groups()[1].replace(':', '-').upper()] = match.groups()[0]
            self.log_message.emit(f"ARP-таблица успешно получена. Найдено {len(mac_ip_map)} устройств.", "info")
            return mac_ip_map
        except Exception as e: self.log_message.emit(f"Не удалось получить ARP-таблицу: {e}", "error"); return {}

    def run(self):
        self.log_message.emit("--- НАЧАЛО ОБНОВЛЕНИЯ IP ---", "info"); logger.info("IPUpdateWorker: Запуск.")
        try:
            net_info = self._get_local_net_info()
            if not net_info: self.log_message.emit("Не удалось продолжить без информации о подсети.", "error"); return
            
            self.log_message.emit("Прогрев ARP-кэша...", "info"); self._warm_up_arp_cache(net_info['subnet'])
            
            arp_table = self._get_arp_table()
            self.log_message.emit(f"Добавляю информацию о локальном хосте в ARP-таблицу: {net_info['ip']} -> {net_info['mac']}", "debug")
            arp_table[net_info['mac']] = net_info['ip']
            
            db_data = fetch_all_data_from_db()
            if not db_data: self.log_message.emit("База данных пуста, нечего обновлять.", "warning"); return

            update_count = 0
            for record in db_data:
                mac_from_db = record.get("MAC-адрес")
                if not mac_from_db: continue
                normalized_mac_db = mac_from_db.upper().replace(':', '-')
                if normalized_mac_db in arp_table:
                    current_ip = arp_table[normalized_mac_db]
                    if current_ip != record.get("Локальный IP"):
                        update_single_field_in_db(record["Имя файла"], "Локальный IP", current_ip)
                        self.log_message.emit(f"IP ОБНОВЛЕН для {record['Название ПК']} ({normalized_mac_db}): {record.get('Локальный IP')} -> {current_ip}", "info"); update_count += 1
            
            if update_count > 0:
                self.log_message.emit(f"Обновлено IP-адресов: {update_count}.", "info"); self.log_message.emit("Обновляю Excel-файл...", "info")
                all_data = fetch_all_data_from_db(); all_data.sort(key=lambda item: natural_sort_key(item.get('Имя файла', '')))
                write_to_excel(all_data, 'system_analysis.xlsx', self.log_message.emit)
            else: self.log_message.emit("Изменений в IP-адресах не найдено.", "info")
        except Exception as e:
            self.log_message.emit(f"КРИТИЧЕСКАЯ ОШИБКА в потоке обновления IP: {e}", "error"); logger.error(f"Критическая ошибка в потоке IPUpdateWorker: {e}", exc_info=True)
        finally:
            logger.info("IPUpdateWorker: Завершение."); self.log_message.emit("--- КОНЕЦ ОБНОВЛЕНИЯ IP ---", "info"); self.finished.emit()
