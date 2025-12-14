import time

import requests

TARGET_URL = "http://0.0.0.0:8080/"
RPS = 0.1
INTERVAL = 1 / RPS

print(f"Запуск нагрузки: {TARGET_URL} с интервалом {INTERVAL} сек.")
try:
    while True:
        start_time = time.time()
        try:
            response = requests.get(TARGET_URL, timeout=2)
            print(f"[{time.strftime('%H:%M:%S')}] Status: {response.status_code}")
        except Exception as e:
            print(f"Ошибка запроса: {e}")

        elapsed = time.time() - start_time
        time.sleep(max(0, INTERVAL - elapsed))
except KeyboardInterrupt:
    print("Генерация нагрузки остановлена.")
