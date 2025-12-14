import matplotlib.pyplot as plt
import pandas as pd


def create_detailed_plot(df_idle, df_load, metric_name, ylabel, title, filename):
    """Создает отдельный файл с двумя графиками (idle и load) для одной метрики."""
    fig, axs = plt.subplots(1, 2, figsize=(16, 6))

    # 1. Режим "Покой" (Idle)
    axs[0].plot(df_idle["timestamp"], df_idle[metric_name], color="blue")
    axs[0].set_title(f"{title} (Покой)")
    axs[0].set_xlabel("Время, с")
    axs[0].set_ylabel(ylabel)
    axs[0].grid(True)

    # 2. Режим "Нагрузка" (Load)
    axs[1].plot(df_load["timestamp"], df_load[metric_name], color="red")
    axs[1].set_title(f"{title} (Нагрузка 0.2 RPS)")
    axs[1].set_xlabel("Время, с")
    axs[1].set_ylabel(ylabel)
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(filename)
    print(f"фалй с графиком: {filename}")
    plt.close(fig)


def plot_detailed_comparison(idle_file, load_file):
    """Генерирует 4 файла с подробными графиками."""
    try:
        df_idle = pd.read_csv(idle_file)
        df_load = pd.read_csv(load_file)
    except FileNotFoundError as e:
        print(
            f"Ошибка: Не найден файл {e.filename}. Убедитесь, что вы запустили сбор данных."
        )
        return

    df_idle["timestamp"] = df_idle["timestamp"] - df_idle["timestamp"].iloc[0]
    df_load["timestamp"] = df_load["timestamp"] - df_load["timestamp"].iloc[0]

    create_detailed_plot(
        df_idle,
        df_load,
        metric_name="cpu_user",
        ylabel="CPU User Time (Ticks/sec)",
        title="1. Загрузка CPU User Time",
        filename="01_cpu_user_time.png",
    )

    create_detailed_plot(
        df_idle,
        df_load,
        metric_name="ctx_switches",
        ylabel="Переключения контекста (Delta/sec)",
        title="2. Интенсивность переключений контекста",
        filename="02_context_switches.png",
    )

    create_detailed_plot(
        df_idle,
        df_load,
        metric_name="rss_mb",
        ylabel="RSS (Resident Set Size), MB",
        title="3. Потребление оперативной памяти (RSS)",
        filename="03_memory_rss.png",
    )

    create_detailed_plot(
        df_idle,
        df_load,
        metric_name="io_write_kb",
        ylabel="Объем записи (KB/sec)",
        title="4. Интенсивность записи на диск",
        filename="04_disk_write_io.png",
    )

    create_detailed_plot(
        df_idle,
        df_load,
        metric_name="pfaults_minor",
        ylabel="Minor Page Faults (Delta/sec)",
        title="5. Minor Page Faults (Активность выделения памяти)",
        filename="05_page_faults_minor.png",
    )

    df_idle["tcp_recv_q_int"] = df_idle["tcp_recv_q"].astype(int)
    df_load["tcp_recv_q_int"] = df_load["tcp_recv_q"].astype(int)
    create_detailed_plot(
        df_idle,
        df_load,
        metric_name="tcp_recv_q_int",
        ylabel="Размер очереди (пакетов)",
        title="6. Размер очереди TCP Recv-Q",
        filename="06_tcp_recv_q.png",
    )

    print("\nГенерация детализированных графиков завершена.")


if __name__ == "__main__":
    plot_detailed_comparison("metrics_idle.csv", "metrics_load.csv")
