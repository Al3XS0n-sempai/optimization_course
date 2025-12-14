import csv
import os
import subprocess
import time

import psutil

TARGET_PORT = 8080
OUTPUT_FILE = "metrics_load.csv"
INTERVAL = 1

# Индексы полей в /proc/<pid>/stat
# minor_faults: 9-е поле (индекс 9-1=8)
# major_faults: 11-е поле (индекс 11-1=10)
MINOR_FAULTS_INDEX = 9
MAJOR_FAULTS_INDEX = 11


def get_pid_by_port(port):
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == "LISTEN":
            return conn.pid
    return None


def get_network_queues(pid):
    """Безопасное получение Recv-Q и Send-Q (Уровень 3)"""
    try:
        cmd = f"ss -nltp | grep 'pid={pid},'"
        output = subprocess.check_output(
            cmd, shell=True, stderr=subprocess.DEVNULL
        ).decode()

        parts = output.split()
        if len(parts) >= 3:
            return parts[1], parts[2]

        cmd_active = f"ss -ntp | grep 'pid={pid},' | awk '{{print $2, $3}}'"
        output_active = (
            subprocess.check_output(cmd_active, shell=True, stderr=subprocess.DEVNULL)
            .decode()
            .strip()
            .split("\n")
        )

        if output_active and output_active[0]:
            parts_active = output_active[0].split()
            if len(parts_active) >= 2:
                return parts_active[0], parts_active[1]

    except subprocess.CalledProcessError:
        pass
    except Exception:
        pass

    return 0, 0


def get_page_faults_from_proc(pid):
    """Чтение minor и major page faults напрямую из /proc/<pid>/stat"""
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            data = f.read().split()
            minor_faults = int(data[MINOR_FAULTS_INDEX - 1])
            major_faults = int(data[MAJOR_FAULTS_INDEX - 1])
            return minor_faults, major_faults
    except Exception:
        return 0, 0


def collect_metrics(pid, duration_sec=300):
    proc = psutil.Process(pid)
    print(f"Сбор данных для PID {pid} запущен...")

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "cpu_user",
                "cpu_system",
                "threads",
                "ctx_switches",
                "rss_mb",
                "vms_mb",
                "pfaults_minor",
                "pfaults_major",
                "io_read_kb",
                "io_write_kb",
                "tcp_recv_q",
                "tcp_send_q",
            ]
        )

        last_io = proc.io_counters()
        last_pf_minor, last_pf_major = get_page_faults_from_proc(pid)

        start_time = time.time()
        prev_time, cur_time = 0, 0
        while time.time() - start_time < duration_sec:
            cur_time = time.time() - start_time
            if cur_time - prev_time > 60:
                print(f"Elapsed {int(cur_time) // 60} minutes")
                prev_time = cur_time
            try:
                # CPU и потоки
                cpu_times = proc.cpu_times()
                threads = proc.num_threads()
                ctx = proc.num_ctx_switches()

                # Память и Диск
                mem = proc.memory_info()
                io = proc.io_counters()
                current_pf_minor, current_pf_major = get_page_faults_from_proc(pid)

                # Считаем диф за интервал
                read_kb = (io.read_bytes - last_io.read_bytes) / 1024
                write_kb = (io.write_bytes - last_io.write_bytes) / 1024

                pf_minor = current_pf_minor - last_pf_minor
                pf_major = current_pf_major - last_pf_major

                # Сетевой стек
                recv_q, send_q = get_network_queues(pid)

                writer.writerow(
                    [
                        round(time.time() - start_time, 2),
                        cpu_times.user,
                        cpu_times.system,
                        threads,
                        ctx.voluntary + ctx.involuntary,
                        round(mem.rss / 1024 / 1024, 2),
                        round(mem.vms / 1024 / 1024, 2),
                        pf_minor,
                        pf_major,
                        read_kb,
                        write_kb,
                        recv_q,
                        send_q,
                    ]
                )

                last_io = io
                last_pf_minor, last_pf_major = current_pf_minor, current_pf_major

                time.sleep(INTERVAL)
            except psutil.NoSuchProcess:
                print("Процесс завершился.")
                break


if __name__ == "__main__":
    pid = get_pid_by_port(TARGET_PORT)
    if pid:
        collect_metrics(pid, duration_sec=6000)  # 100 минут замера под нагрузкой
    else:
        print(f"Приложение на порту {TARGET_PORT} нету")
