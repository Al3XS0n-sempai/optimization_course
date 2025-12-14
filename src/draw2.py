
#!/usr/bin/env python3
import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


REQUIRED = {
    "epoch", "tid", "tname",
    "voluntary", "nonvoluntary",
    "voluntary_delta", "nonvoluntary_delta",
}


def read_ctx_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise SystemExit(f"{path}: missing columns: {sorted(missing)}")

    # types
    df["epoch"] = pd.to_numeric(df["epoch"], errors="coerce")
    df["tid"] = pd.to_numeric(df["tid"], errors="coerce")
    df["voluntary_delta"] = pd.to_numeric(df["voluntary_delta"], errors="coerce").fillna(0)
    df["nonvoluntary_delta"] = pd.to_numeric(df["nonvoluntary_delta"], errors="coerce").fillna(0)

    df = df.dropna(subset=["epoch", "tid"]).copy()
    df["epoch"] = df["epoch"].astype("int64")
    df["tid"] = df["tid"].astype("int64")
    df["tname"] = df["tname"].astype(str)
    return df


def agg_by_thread(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["tid", "tname"], as_index=False).agg(
        voluntary_delta=("voluntary_delta", "sum"),
        nonvoluntary_delta=("nonvoluntary_delta", "sum"),
    )
    g["total_delta"] = g["voluntary_delta"] + g["nonvoluntary_delta"]
    g["label"] = g.apply(lambda r: f"{int(r['tid'])}:{r['tname']}", axis=1)
    return g


def totals_over_time(df: pd.DataFrame) -> pd.DataFrame:
    t = df.groupby("epoch", as_index=False).agg(
        voluntary_delta=("voluntary_delta", "sum"),
        nonvoluntary_delta=("nonvoluntary_delta", "sum"),
    ).sort_values("epoch")
    t["total_delta"] = t["voluntary_delta"] + t["nonvoluntary_delta"]
    return t


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def save_fig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def main():
    ap = argparse.ArgumentParser(
        description="Compare context switches (voluntary/nonvoluntary) between idle and load CSVs."
    )
    ap.add_argument("idle_csv", type=str, help="CSV in idle")
    ap.add_argument("load_csv", type=str, help="CSV under load")
    ap.add_argument("--top", type=int, default=25, help="Top N threads by load total delta (default: 25)")
    ap.add_argument("-o", "--outdir", type=str, default="ctx_plots", help="Output dir (default: ./ctx_plots)")
    ap.add_argument("--label-idle", type=str, default="idle", help="Legend label for idle (default: idle)")
    ap.add_argument("--label-load", type=str, default="load", help="Legend label for load (default: load)")
    args = ap.parse_args()

    idle_path = Path(args.idle_csv).expanduser().resolve()
    load_path = Path(args.load_csv).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    ensure_dir(outdir)

    idle = read_ctx_csv(idle_path)
    load = read_ctx_csv(load_path)

    idle_thr = agg_by_thread(idle).rename(columns={
        "voluntary_delta": "idle_v",
        "nonvoluntary_delta": "idle_nv",
        "total_delta": "idle_total",
        "label": "label",
    })
    load_thr = agg_by_thread(load).rename(columns={
        "voluntary_delta": "load_v",
        "nonvoluntary_delta": "load_nv",
        "total_delta": "load_total",
        "label": "label",
    })

    # merge threads, missing -> 0
    m = pd.merge(
        idle_thr[["tid", "tname", "label", "idle_v", "idle_nv", "idle_total"]],
        load_thr[["tid", "tname", "label", "load_v", "load_nv", "load_total"]],
        on=["tid", "tname", "label"],
        how="outer",
    ).fillna(0)

    # pick top-N by load_total (fallback: idle_total)
    m["rank_key"] = m["load_total"]
    if (m["rank_key"] == 0).all():
        m["rank_key"] = m["idle_total"]
    top = m.sort_values("rank_key", ascending=False).head(args.top)

    # ---- Plot 1: per-thread compare (stacked voluntary/nonvoluntary), idle vs load ----
    x = list(range(len(top)))
    width = 0.42

    plt.figure()
    # idle bars
    plt.bar([i - width/2 for i in x], top["idle_v"], width, label=f"{args.label_idle} voluntary")
    plt.bar([i - width/2 for i in x], top["idle_nv"], width, bottom=top["idle_v"], label=f"{args.label_idle} nonvoluntary")
    # load bars
    plt.bar([i + width/2 for i in x], top["load_v"], width, label=f"{args.label_load} voluntary")
    plt.bar([i + width/2 for i in x], top["load_nv"], width, bottom=top["load_v"], label=f"{args.label_load} nonvoluntary")

    plt.xticks(x, top["label"], rotation=90)
    plt.ylabel("Context switches (sum of deltas)")
    plt.title(f"Context switches by thread (top {len(top)}) — compare {args.label_idle} vs {args.label_load}")
    plt.legend()
    save_fig(outdir / "ctx_by_thread_compare.png")

    # ---- Plot 2: totals over time (sum across threads per epoch) ----
    idle_t = totals_over_time(idle).rename(columns={"total_delta": "idle_total"})
    load_t = totals_over_time(load).rename(columns={"total_delta": "load_total"})

    plt.figure()
    plt.plot(idle_t["epoch"], idle_t["idle_total"], label=f"{args.label_idle} total delta")
    plt.plot(load_t["epoch"], load_t["load_total"], label=f"{args.label_load} total delta")
    plt.xlabel("epoch")
    plt.ylabel("Context switches per sample (sum of deltas)")
    plt.title("Total context switches over time (sum of per-thread deltas)")
    plt.legend()
    save_fig(outdir / "ctx_total_over_time_compare.png")

    # Optional: write merged summary
    top_out = top.copy()
    top_out.to_csv(outdir / "ctx_thread_summary_top.csv", index=False)

    print(f"OK: {outdir}")
    print(" - ctx_by_thread_compare.png")
    print(" - ctx_total_over_time_compare.png")
    print(" - ctx_thread_summary_top.csv")


if __name__ == "__main__":
    main()

