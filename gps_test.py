import machine
import time
import struct

# Настройка UART
uart = machine.UART(1, baudrate=9600, tx=21, rx=20)

def calculate_checksum(msg):
    ck_a = 0
    ck_b = 0
    for b in msg:
        ck_a = (ck_a + b) & 0xFF
        ck_b = (ck_b + ck_a) & 0xFF
    return bytes([ck_a, ck_b])

def nmea_coord_to_float(coord, direction):
    # NMEA: DDMM.MMMM для широты, DDDMM.MMMM для долготы
    if not coord or not direction:
        return None
    if '.' not in coord:
        return None
    if len(coord) < 6:
        return None
    if len(coord.split('.')[0]) > 4:  # долгота
        deg = int(coord[:3])
        minute = float(coord[3:])
    else:  # широта
        deg = int(coord[:2])
        minute = float(coord[2:])
    val = deg + minute/60
    if direction in ['S','W']:
        val *= -1
    return val

def extract_lat_lon(nmea_line):
    # Принимает строку NMEA, возвращает (lat, lon) или (None, None)
    parts = nmea_line.split(',')
    if nmea_line.startswith('$GPGGA') and len(parts) >= 6 and parts[2] and parts[4]:
        lat = nmea_coord_to_float(parts[2], parts[3])
        lon = nmea_coord_to_float(parts[4], parts[5])
        return lat, lon
    elif nmea_line.startswith('$GPRMC') and len(parts) >= 7 and parts[3] and parts[5]:
        lat = nmea_coord_to_float(parts[3], parts[4])
        lon = nmea_coord_to_float(parts[5], parts[6])
        return lat, lon
    return None, None

def send_ubx(msg_class, msg_id, payload):
    header = b'\xB5\x62'
    length = struct.pack('<H', len(payload))
    body = bytes([msg_class, msg_id]) + length + payload
    checksum = calculate_checksum(body)
    packet = header + body + checksum
    uart.write(packet)
    print(f"-> UBX Class 0x{msg_class:02X} ID 0x{msg_id:02X} отправлен")

# --- ЛОГИКА КОНФИГУРАЦИИ ---
# На NEO-7M конфигурация GNSS отправляется одним пакетом, 
# где мы перечисляем блоки для каждой системы.
# Порядок блоков в памяти модуля: GPS(0), SBAS(1), Galileo(2), Beidou(3), IMES(4), QZSS(5), GLONASS(6).

# Мы сформируем пакет, который сразу делает то, что вы нашли:
# 1. QZSS -> OFF
# 2. SBAS -> OFF
# 3. GPS -> OFF
# 4. GLONASS -> ON

payload_cfg_gnss = (
    b'\x00'       # msgVer
    b'\x20'       # numTrkChHw (32)
    b'\x20'       # numTrkChUse (32)
    b'\x04'       # numConfigBlocks (Мы отправим настройки для 4 систем: GPS, SBAS, QZSS, GLONASS)
    
    # Блок 1: GPS (ID 0) -> ОТКЛЮЧАЕМ
    b'\x00'       # gnssId
    b'\x04'       # resTrkCh
    b'\xFF'       # maxTrkCh
    b'\x00'       # reserved
    b'\x00\x00\x00\x00' # flags: 0 = disable
    
    # Блок 2: SBAS (ID 1) -> ОТКЛЮЧАЕМ
    b'\x01'       # gnssId
    b'\x00'       # resTrkCh
    b'\x03'       # maxTrkCh
    b'\x00'       # reserved
    b'\x00\x00\x00\x00' # flags: 0 = disable

    # Блок 3: QZSS (ID 5) -> ОТКЛЮЧАЕМ
    b'\x05'       # gnssId
    b'\x00'       # resTrkCh
    b'\x03'       # maxTrkCh
    b'\x00'       # reserved
    b'\x00\x00\x00\x00' # flags: 0 = disable
    
    # Блок 4: GLONASS (ID 6) -> ВКЛЮЧАЕМ
    b'\x06'       # gnssId
    b'\x08'       # resTrkCh
    b'\xFF'       # maxTrkCh
    b'\x00'       # reserved
    b'\x01\x00\x00\x00' # flags: 1 = enable
)

# 1. Отправляем конфигурацию
print("Применяем настройки GNSS...")
send_ubx(0x06, 0x3E, payload_cfg_gnss) # CFG-GNSS
time.sleep(1)

# 2. Сохраняем (чтобы не сбросилось)
print("Сохраняем в память...")
save_payload = b'\x00\x00\x00\x00\x1F\x00\x00\x00\x00\x00\x00\x00\x1F'
send_ubx(0x06, 0x09, save_payload) # CFG-CFG
time.sleep(1)

# 3. Сброс (Cold Start) - ОБЯЗАТЕЛЬНО для смены частоты с GPS на GLONASS
print("Перезагрузка модуля (Cold Start)...")
rst_payload = b'\xFF\xFF\x01\x00'
send_ubx(0x06, 0x04, rst_payload) # CFG-RST

print("Ждем данные (10 сек)...")
time.sleep(5) 
# Очищаем буфер от мусора при перезагрузке
while uart.any():
    uart.read()

print("--- Чтение данных ---")

while True:
    if uart.any():
        line = uart.readline()
        if line:
            # ВОТ ЗДЕСЬ ИСПРАВЛЕНИЕ ОШИБКИ UNICODE:
            try:
                # errors='replace' заменит битые байты на знаки вопроса, но не уронит программу
                decoded_line = line.decode('utf-8', 'replace').strip()
                
                # Фильтруем пустые строки
                if decoded_line:
                    lat, lon = extract_lat_lon(decoded_line)
                    if lat is not None and lon is not None:
                        print("COORDS:", lat, lon)
                    print(decoded_line)

                    
            except UnicodeError:
                # На всякий случай, если replace не сработает (хотя должен)
                print("Binary/Garbage data received")
                
    time.sleep(0.1)
