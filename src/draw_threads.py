import matplotlib.pyplot as plt
import pandas as pd


def analyze_threads(threads_file):
    df = pd.read_csv(threads_file)

    thread_summary = (
        df.groupby("thread_id")
        .agg(
            total_user_cpu=("cpu_user_delta", "sum"),
            total_system_cpu=("cpu_system_delta", "sum"),
            num_observations=("thread_id", "size"),
        )
        .sort_values(by="total_user_cpu", ascending=False)
    )

    top_10 = thread_summary.head(10)

    print("--- 10 самых активных потоков (по CPU User Time) ---")
    print(top_10[["total_user_cpu", "total_system_cpu"]])

    top_10[["total_user_cpu", "total_system_cpu"]].plot(
        kind="bar", figsize=(12, 6), stacked=True
    )
    plt.title(f"Общая загрузка CPU по потокам ({threads_file})")
    plt.ylabel("Суммарное CPU-время (Ticks)")
    plt.xlabel("Thread ID")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(f"{threads_file.replace('.csv', '_summary.png')}")
    plt.show()


analyze_threads("threads_idle.csv")
