#!/usr/bin/env python3
"""Run the atypical-result analysis for every eligible UNAM program."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_program import DEFAULT_DATA, analyze_program

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results_all"
REQUIRED_YEARS = set(range(2021, 2027))
SCORE_COLUMNS = (
    "expected_score_mean",
    "expected_score_stdev",
    "obtained_score_mean",
    "obtained_score_stdev",
    "inferred_atypical_mean",
    "inferred_atypical_stdev",
)
FRACTION_COLUMNS = ("fraction_atypical_mean", "fraction_atypical_stdev")


def _analyze_one(program_data: pd.DataFrame) -> dict[str, object]:
    program = str(program_data["carrera"].iloc[0])
    return analyze_program(
        program=program,
        output_dir=None,
        verbose=False,
        data_frame=program_data,
    )


def flatten_result(result: dict[str, object]) -> dict[str, object]:
    expected = result["expected_score"]
    obtained = result["obtained_score"]
    atypical = result["inferred_atypical"]
    fraction = result["fraction"]
    return {
        "area": result["area"],
        "program": result["program"],
        "expected_score_mean": expected["mean"],
        "expected_score_stdev": expected["stdev"],
        "obtained_score_mean": obtained["mean"],
        "obtained_score_stdev": obtained["stdev"],
        "inferred_atypical_mean": atypical["mean"],
        "inferred_atypical_stdev": atypical["stdev"],
        "fraction_atypical_mean": fraction["mean"],
        "fraction_atypical_stdev": fraction["stdev"],
        "num_2026": result["n_2026"],
        "estimated_atypical_count": result["n_2026"] * fraction["mean"],
    }


def formatted_results(results: pd.DataFrame) -> pd.DataFrame:
    columns = ["area", "program", "num_2026", *SCORE_COLUMNS, *FRACTION_COLUMNS]
    output = results.loc[:, columns].copy()
    for column in SCORE_COLUMNS:
        output[column] = output[column].map(lambda value: f"{value:.2f}")
    for column in FRACTION_COLUMNS:
        output[column] = output[column].map(lambda value: f"{value:.5f}")
    return output


def save_top_bottom_table(results: pd.DataFrame, output_dir: Path) -> None:
    ordered = results.sort_values("fraction_atypical_mean", ascending=False)
    top = ordered.head(10).copy()
    top.insert(0, "group", "Top 10")
    bottom = ordered.tail(10).sort_values("fraction_atypical_mean").copy()
    bottom.insert(0, "group", "Bottom 10")
    table = pd.concat([top, bottom], ignore_index=True)
    table_output = table[
        [
            "group",
            "area",
            "program",
            "num_2026",
            "fraction_atypical_mean",
            "fraction_atypical_stdev",
        ]
    ].copy()
    for column in FRACTION_COLUMNS:
        table_output[column] = table_output[column].map(lambda value: f"{value:.5f}")
    table_output.to_csv(output_dir / "top_bottom_10.csv", index=False)

    display = table_output.copy()
    display["fraction"] = table.apply(
        lambda row: (
            f"{100 * row['fraction_atypical_mean']:.2f}% "
            f"± {100 * row['fraction_atypical_stdev']:.2f}%"
        ),
        axis=1,
    )
    display = display[["group", "area", "program", "num_2026", "fraction"]]
    fig, ax = plt.subplots(figsize=(12, 8), constrained_layout=True)
    ax.axis("off")
    rendered = ax.table(
        cellText=display.values,
        colLabels=["Group", "Area", "Program", "Students in 2026", "Atypical fraction"],
        cellLoc="left",
        colLoc="left",
        loc="center",
        colWidths=[0.10, 0.06, 0.48, 0.15, 0.21],
    )
    rendered.auto_set_font_size(False)
    rendered.set_fontsize(9)
    rendered.scale(1, 1.45)
    for column in range(5):
        rendered[(0, column)].set_text_props(weight="bold")
        rendered[(0, column)].set_facecolor("#d9eaf7")
    ax.set_title("Programs with highest and lowest inferred atypical fractions", pad=20)
    fig.savefig(output_dir / "top_bottom_10.png", dpi=180)
    plt.close(fig)


def save_count_histograms(results: pd.DataFrame, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    colors = {1: "tab:blue", 2: "tab:green", 3: "tab:orange", 4: "tab:purple"}
    minimum = max(results["estimated_atypical_count"].min(), 1)
    maximum = results["estimated_atypical_count"].max()
    bins = np.geomspace(minimum, maximum, 18)
    for area in range(1, 5):
        values = results.loc[
            results["area"].eq(area), "estimated_atypical_count"
        ].to_numpy()
        ax.hist(
            values,
            bins=bins,
            histtype="step",
            linewidth=2,
            color=colors[area],
            label=f"Area {area} (n={len(values)} programs)",
        )
    ax.set(
        title="Distribution of estimated atypical-result counts by area",
        xlabel="Estimated number of atypical results in a program",
        ylabel="Number of programs",
    )
    ax.set_xscale("log")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(output_dir / "atypical_counts_by_area.png", dpi=180)
    plt.close(fig)


def save_fraction_vs_expected(results: pd.DataFrame, output_dir: Path) -> dict[str, float]:
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    colors = {1: "tab:blue", 2: "tab:green", 3: "tab:orange", 4: "tab:purple"}
    size_scale = 260 / np.sqrt(results["num_2026"].max())
    for area in range(1, 5):
        subset = results.loc[results["area"].eq(area)]
        ax.scatter(
            subset["expected_score_mean"],
            100 * subset["fraction_atypical_mean"],
            s=size_scale * np.sqrt(subset["num_2026"]),
            alpha=0.75,
            color=colors[area],
            label=f"Area {area}",
        )

    x = results["expected_score_mean"].to_numpy()
    y = results["fraction_atypical_mean"].to_numpy()
    slope, intercept = np.polyfit(x, y, 1)
    grid = np.linspace(x.min(), x.max(), 200)
    ax.plot(grid, 100 * (intercept + slope * grid), "k--", label="Linear trend")
    pearson = float(np.corrcoef(x, y)[0, 1])
    spearman = float(pd.Series(x).corr(pd.Series(y), method="spearman"))
    ax.text(
        0.02,
        0.98,
        f"Pearson r = {pearson:.3f}\nSpearman ρ = {spearman:.3f}",
        transform=ax.transAxes,
        va="top",
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "0.8"},
    )
    ax.set(
        title="Inferred atypical fraction versus expected score",
        xlabel="Expected score from 2021–2025 fitted usual distributions",
        ylabel="Inferred atypical fraction (%)",
    )
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(output_dir / "fraction_vs_expected_score.png", dpi=180)
    plt.close(fig)
    return {
        "pearson_r": round(pearson, 5),
        "spearman_rho": round(spearman, 5),
        "linear_slope_fraction_per_score": round(float(slope), 5),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = pd.read_csv(
        args.data,
        usecols=["aciertos", "año", "area", "carrera"],
    ).dropna(subset=["aciertos"])
    args.output_dir.mkdir(parents=True, exist_ok=True)

    eligible: list[pd.DataFrame] = []
    skipped_rows = []
    for (area, program), group in data.groupby(["area", "carrera"], sort=True):
        available = set(int(year) for year in group["año"].unique())
        missing = sorted(REQUIRED_YEARS - available)
        if missing:
            skipped_rows.append(
                {
                    "area": int(area),
                    "program": program,
                    "missing_years": ",".join(map(str, missing)),
                    "reason": "Requires observed scores in every year 2021-2026",
                }
            )
        else:
            eligible.append(group.copy())

    results = []
    failures = []
    total = len(eligible)
    for completed, group in enumerate(eligible, start=1):
        program = str(group["carrera"].iloc[0])
        try:
            result = flatten_result(_analyze_one(group))
            results.append(result)
            print(
                f"[{completed:3d}/{total}] {program}: "
                f"{100 * result['fraction_atypical_mean']:.2f}%",
                flush=True,
            )
        except Exception as error:
            failures.append(
                {"program": program, "reason": f"{type(error).__name__}: {error}"}
            )
            print(f"[{completed:3d}/{total}] {program}: FAILED ({error})", flush=True)

    if not results:
        raise RuntimeError("No program analyses completed successfully")
    results_table = pd.DataFrame(results).sort_values(["area", "program"]).reset_index(drop=True)
    formatted_results(results_table).to_csv(
        args.output_dir / "all_program_results.csv", index=False
    )
    pd.DataFrame(skipped_rows + failures).to_csv(
        args.output_dir / "skipped_programs.csv", index=False
    )
    save_top_bottom_table(results_table, args.output_dir)
    save_count_histograms(results_table, args.output_dir)
    correlation = save_fraction_vs_expected(results_table, args.output_dir)
    metadata = {
        "programs_analyzed": len(results_table),
        "programs_skipped": len(skipped_rows),
        "programs_failed": len(failures),
        "correlation_fraction_vs_expected_score": correlation,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nCompleted {len(results_table)} programs.")
    print(f"Results saved to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
