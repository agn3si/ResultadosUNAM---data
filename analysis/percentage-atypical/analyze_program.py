#!/usr/bin/env python3
"""Estimate the atypical fraction in one UNAM program's 2026 scores.

The 2021--2025 score distributions are fit independently with beta-binomial
models. The 2026 histogram is then fit five times as

    (1 - fraction_atypical) * BB_usual
        + fraction_atypical * BB_atypical.

Each fit fixes the usual component to the parameters obtained in one historical
year. The mean and sample standard deviation across those five fits summarize
the sensitivity to the choice of usual year. The atypical component is
constrained to have a higher mean, which identifies the mixture labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, gammaln, logsumexp
from scipy.stats import betabinom

N_QUESTIONS = 120
BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA = BASE_DIR / "data" / "processed" / "aciertos_unam_2021_2026.csv"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results_program"
USUAL_YEARS = tuple(range(2021, 2026))


def bb_logpmf(scores: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """Beta-binomial log-PMF on 0,...,N_QUESTIONS."""
    n = N_QUESTIONS
    x = np.asarray(scores, dtype=float)
    return (
        gammaln(n + 1)
        - gammaln(x + 1)
        - gammaln(n - x + 1)
        + gammaln(x + alpha)
        + gammaln(n - x + beta)
        - gammaln(n + alpha + beta)
        + gammaln(alpha + beta)
        - gammaln(alpha)
        - gammaln(beta)
    )


def mean_concentration(alpha: float, beta: float) -> tuple[float, float]:
    return alpha / (alpha + beta), alpha + beta


def bb_score_sd(alpha: float, beta: float) -> float:
    """Standard deviation of beta-binomial scores on the score scale."""
    return float(betabinom.std(N_QUESTIONS, alpha, beta))


def fit_bb(hist: np.ndarray) -> dict[str, float]:
    """Maximum-likelihood beta-binomial fit to a histogram."""
    scores = np.arange(N_QUESTIONS + 1)
    sample_mean = np.dot(scores, hist) / hist.sum() / N_QUESTIONS
    initial = np.log([max(sample_mean * 8, 0.1), max((1 - sample_mean) * 8, 0.1)])

    def objective(log_parameters: np.ndarray) -> float:
        alpha, beta = np.exp(log_parameters)
        return float(-np.dot(hist, bb_logpmf(scores, alpha, beta)))

    fit = minimize(objective, initial, method="L-BFGS-B", bounds=[(-8, 12), (-8, 12)])
    if not fit.success:
        fallback = minimize(
            objective,
            initial,
            method="Powell",
            bounds=[(-8, 12), (-8, 12)],
        )
        if not fallback.success:
            raise RuntimeError(
                f"Beta-binomial fit failed: {fit.message}; fallback: {fallback.message}"
            )
        fit = fallback
    alpha, beta = np.exp(fit.x)
    mean, _ = mean_concentration(alpha, beta)
    return {
        "alpha": float(alpha),
        "beta": float(beta),
        # "mean_probability": float(mean),
        "mean_score": float(N_QUESTIONS * mean),
        "score_sd": bb_score_sd(alpha, beta),
        # "negative_log_likelihood": float(fit.fun),
    }


def fit_mixture(hist: np.ndarray, usual_alpha: float, usual_beta: float) -> dict[str, float]:
    """Fit the high-score component and its fraction, holding usual BB fixed."""
    scores = np.arange(N_QUESTIONS + 1)
    usual_mean, _ = mean_concentration(usual_alpha, usual_beta)
    log_usual = bb_logpmf(scores, usual_alpha, usual_beta)

    # theta = logit(relative increase above usual mean), log(concentration),
    #         logit(atypical fraction)
    initial = np.array([0.0, np.log(12.0), -1.0])

    def unpack(theta: np.ndarray) -> tuple[float, float, float, float, float]:
        atypical_mean = usual_mean + (1 - usual_mean) * expit(theta[0])
        concentration = np.exp(theta[1])
        atypical_alpha = atypical_mean * concentration
        atypical_beta = (1 - atypical_mean) * concentration
        fraction = expit(theta[2])
        return atypical_alpha, atypical_beta, atypical_mean, concentration, fraction

    def objective(theta: np.ndarray) -> float:
        aa, ab, _, _, fraction = unpack(theta)
        components = np.vstack(
            (np.log1p(-fraction) + log_usual, np.log(fraction) + bb_logpmf(scores, aa, ab))
        )
        return float(-np.dot(hist, logsumexp(components, axis=0)))

    best = None
    for atypical_logit in (-2.0, 0.0, 2.0):
        for fraction_logit in (-2.0, -0.5, 1.0):
            start = initial.copy()
            start[[0, 2]] = [atypical_logit, fraction_logit]
            candidate = minimize(
                objective,
                start,
                method="L-BFGS-B",
                bounds=[(-8, 8), (-8, 12), (-10, 10)],
            )
            if candidate.success and (best is None or candidate.fun < best.fun):
                best = candidate
    if best is None:
        raise RuntimeError("All 2026 mixture optimizations failed")

    aa, ab, amean, _, fraction = unpack(best.x)
    return {
        "atypical_alpha": float(aa),
        "atypical_beta": float(ab),
        # "atypical_mean_probability": float(amean),
        "atypical_mean_score": float(N_QUESTIONS * amean),
        "atypical_score_sd": bb_score_sd(aa, ab),
        "fraction_atypical": float(fraction),
        # "negative_log_likelihood": float(best.fun),
    }


def save_plot(
    histogram_table: pd.DataFrame,
    reference_usual: dict[str, float],
    reference_mixture: dict[str, float],
    reference_year: int,
    fraction_mean: float,
    fraction_sd: float,
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 9), constrained_layout=True)
    for year in range(2021, 2027):
        values = histogram_table.loc[histogram_table["year"] == year, "count"].to_numpy()
        axes[0].plot(np.arange(N_QUESTIONS + 1), values / values.sum(), label=str(year))
    axes[0].set(title="Observed score histograms", xlabel="Score", ylabel="Proportion")
    axes[0].legend(ncol=3)

    scores = np.arange(N_QUESTIONS + 1)
    observed = histogram_table.loc[histogram_table["year"] == 2026, "count"].to_numpy()
    observed = observed / observed.sum()
    usual = np.exp(bb_logpmf(scores, reference_usual["alpha"], reference_usual["beta"]))
    atypical = np.exp(
        bb_logpmf(scores, reference_mixture["atypical_alpha"], reference_mixture["atypical_beta"])
    )
    fraction = reference_mixture["fraction_atypical"]
    axes[1].bar(scores, observed, width=1, alpha=0.35, label="2026 observed")
    axes[1].plot(scores, (1 - fraction) * usual + fraction * atypical, label="Fitted mixture")
    axes[1].plot(
        scores,
        (1 - fraction) * usual,
        "--",
        label=f"Usual contribution ({100 * (1 - fraction_mean):.1f}% ± {100 * fraction_sd:.1f}%)",
    )
    axes[1].plot(
        scores,
        fraction * atypical,
        "--",
        label=f"Atypical contribution ({100 * fraction_mean:.1f}% ± {100 * fraction_sd:.1f}%)",
    )
    axes[1].set(
        title=f"2026 mixture fit using {reference_year} as the usual component",
        xlabel="Score",
        ylabel="Probability",
    )
    axes[1].legend()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_parameter_plot(
    histogram_table: pd.DataFrame,
    yearly_fits: pd.DataFrame,
    mixture_fits: pd.DataFrame,
    output_path: Path,
) -> None:
    """Compare observed and fitted score means with one-standard-deviation bars."""
    scores = np.arange(N_QUESTIONS + 1)
    observed_rows = []
    for year in range(2021, 2027):
        counts = histogram_table.loc[histogram_table["year"].eq(year), "count"].to_numpy()
        mean = np.average(scores, weights=counts)
        score_sd = np.sqrt(np.average((scores - mean) ** 2, weights=counts))
        observed_rows.append({"year": year, "mean_score": mean, "score_sd": score_sd})
    observed = pd.DataFrame(observed_rows)

    atypical_mean = mixture_fits["atypical_mean_score"].mean()
    atypical_sd = mixture_fits["atypical_score_sd"].mean()

    fig, ax = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    ax.errorbar(
        observed["year"],
        observed["mean_score"],
        yerr=observed["score_sd"],
        fmt="o-",
        capsize=5,
        color="tab:blue",
        alpha=0.75,
        label="Observed: mean ± 1σ",
    )
    fitted_usual = ax.errorbar(
        yearly_fits["year"]+0.15,
        yearly_fits["mean_score"],
        yerr=yearly_fits["score_sd"],
        fmt="o--",
        capsize=5,
        color="navy",
        label="Fitted usual BB: mean ± 1σ",
    )
    fitted_atypical = ax.errorbar(
        [2026+0.15],
        [atypical_mean],
        yerr=[atypical_sd],
        fmt="o--",
        capsize=5,
        markersize=8,
        color="tab:red",
        label="Fitted atypical BB: mean across 5 fits ± 1σ",
    )
    for errorbar in (fitted_usual, fitted_atypical):
        for stem in errorbar[2]:
            stem.set_linestyle("--")
    ax.set(
        title="Observed and fitted score distributions by year",
        xlabel="Year",
        ylabel="Score",
        xticks=range(2021, 2027),
        ylim=(0, N_QUESTIONS),
    )
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", default="ACTUARIA", help="Exact carrera label")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="Do not create CSV, JSON, or plot files",
    )
    return parser.parse_args()


def analyze_program(
    program: str,
    data_path: Path = DEFAULT_DATA,
    output_dir: Path | None = DEFAULT_OUTPUT,
    verbose: bool = False,
    data_frame: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Run one program analysis and return its atypical-fraction summary.

    Set ``output_dir=None`` to suppress all file creation. This is the intended
    interface for a future loop over programs.
    """
    program = program.strip().upper()
    if output_dir is not None and not program == 'ACTUARIA':
        output_dir = Path(__file__).resolve().parent / f"results_program_{program}"

    if data_frame is None:
        data = pd.read_csv(data_path, usecols=["aciertos", "año", "area", "carrera"])
    else:
        required = {"aciertos", "año", "area", "carrera"}
        missing_columns = required - set(data_frame.columns)
        if missing_columns:
            raise ValueError(f"data_frame is missing columns: {sorted(missing_columns)}")
        data = data_frame
    data = data.loc[data["carrera"].eq(program) & data["año"].between(2021, 2026)].copy()
    data = data.dropna(subset=["aciertos"])
    if data.empty:
        raise ValueError(f"No observed scores found for carrera={program!r}")
    if not np.all(data["aciertos"].to_numpy() == data["aciertos"].astype(int).to_numpy()):
        raise ValueError("Beta-binomial model requires integer scores")
    if not data["aciertos"].between(0, N_QUESTIONS).all():
        raise ValueError(f"Scores must be between 0 and {N_QUESTIONS}")
    missing_years = set(range(2021, 2027)) - set(data["año"].unique())
    if missing_years:
        raise ValueError(f"Missing observed scores for years: {sorted(missing_years)}")
    areas = data["area"].unique()
    if len(areas) != 1:
        raise ValueError(f"Expected one area for {program!r}, found {areas.tolist()}")
    area = int(areas[0])

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
    score_grid = np.arange(N_QUESTIONS + 1)
    histograms: dict[int, np.ndarray] = {}
    histogram_rows = []
    for year in range(2021, 2027):
        hist = np.bincount(
            data.loc[data["año"].eq(year), "aciertos"].astype(int), minlength=N_QUESTIONS + 1
        )
        histograms[year] = hist
        histogram_rows.extend({"year": year, "score": x, "count": int(hist[x])} for x in score_grid)
    histogram_table = pd.DataFrame(histogram_rows)
    # histogram_table.to_csv(args.output_dir / "histograms.csv", index=False)

    yearly_rows = []
    for year in USUAL_YEARS:
        fit = fit_bb(histograms[year])
        yearly_rows.append({"year": year, "n_observed": int(histograms[year].sum()), **fit})
    yearly_fits = pd.DataFrame(yearly_rows)
    yearly_fits_header = ""
    yearly_fits_header += f"Fits year per year for usual results: 2021-2025\n"
    yearly_fits_header += f"Program: {program}\n"
    if output_dir is not None:
        np.savetxt(output_dir / "usual_yearly_fits.csv", np.empty(0), header=yearly_fits_header)
        yearly_output = yearly_fits.copy()
        for column in ("mean_score", "score_sd"):
            yearly_output[column] = yearly_output[column].map(lambda value: f"{value:.2f}")
        for column in ("alpha", "beta"):
            yearly_output[column] = yearly_output[column].map(lambda value: f"{value:.4f}")
        yearly_output.to_csv(output_dir / "usual_yearly_fits.csv", index=False, mode="a")

    mixture_rows = []
    for usual in yearly_fits.itertuples(index=False):
        mixture = fit_mixture(histograms[2026], usual.alpha, usual.beta)
        mixture_rows.append(
            {
                "usual_year": int(usual.year),
                "usual_alpha": usual.alpha,
                "usual_beta": usual.beta,
                "usual_mean_score": usual.mean_score,
                "usual_score_sd": usual.score_sd,
                **mixture,
            }
        )
    mixture_fits = pd.DataFrame(mixture_rows)
    mixture_fits_header = ""
    mixture_fits_header += f"Inferred cheater fraction depending on baseline year: 2021-2025\n"
    mixture_fits_header += f"Program: {program}\n"
    if output_dir is not None:
        np.savetxt(
            output_dir / "mixture_fits_by_usual_year.csv",
            np.empty(0),
            header=mixture_fits_header,
        )
    mixture_fits_columns_to_write = [
        "usual_year",
        "usual_mean_score",
        "usual_score_sd",
        "atypical_mean_score",
        "atypical_score_sd",
        "fraction_atypical",
    ]
    if output_dir is not None:
        mixture_output = mixture_fits[mixture_fits_columns_to_write].copy()
        score_columns = [
            "usual_mean_score",
            "usual_score_sd",
            "atypical_mean_score",
            "atypical_score_sd",
        ]
        for column in score_columns:
            mixture_output[column] = mixture_output[column].map(lambda value: f"{value:.2f}")
        mixture_output["fraction_atypical"] = mixture_output["fraction_atypical"].map(
            lambda value: f"{value:.5f}"
        )
        mixture_output.to_csv(
            output_dir / "mixture_fits_by_usual_year.csv", index=False, mode="a"
        )

    fraction = mixture_fits["fraction_atypical"]
    summary = {
        "program": program,
        "n_2026_observed": int(histograms[2026].sum()),
        "number_of_fits": len(mixture_fits),
        "usual_parameter_years": list(USUAL_YEARS),
        "fraction_atypical": {
            "mean": round(float(fraction.mean()), 5),
            "sample_sd": round(float(fraction.std(ddof=1)), 5),
        },
    }
    if output_dir is not None:
        (output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        reference_index = (fraction - fraction.mean()).abs().idxmin()
        reference_mixture = mixture_fits.loc[reference_index].to_dict()
        reference_year = int(reference_mixture["usual_year"])
        reference_usual = yearly_fits.loc[
            yearly_fits["year"].eq(reference_year)
        ].iloc[0].to_dict()
        save_plot(
            histogram_table,
            reference_usual,
            reference_mixture,
            reference_year,
            fraction.mean(),
            fraction.std(ddof=1),
            output_dir / "diagnostic.png",
        )
        save_parameter_plot(
            histogram_table,
            yearly_fits,
            mixture_fits,
            output_dir / "parameters_by_year.png",
        )

    result = {
        "area": area,
        "program": program,
        "expected_score": {
            "mean": round(float(yearly_fits["mean_score"].mean()), 2),
            "stdev": round(float(yearly_fits["score_sd"].mean()), 2),
        },
        "obtained_score": {
            "mean": round(
                float(np.average(score_grid, weights=histograms[2026])),
                2,
            ),
            "stdev": round(
                float(
                    np.sqrt(
                        np.average(
                            (
                                score_grid
                                - np.average(score_grid, weights=histograms[2026])
                            )
                            ** 2,
                            weights=histograms[2026],
                        )
                    )
                ),
                2,
            ),
        },
        "inferred_atypical": {
            "mean": round(float(mixture_fits["atypical_mean_score"].mean()), 2),
            "stdev": round(float(mixture_fits["atypical_score_sd"].mean()), 2),
        },
        "fraction": {
            "mean": round(float(fraction.mean()), 5),
            "stdev": round(float(fraction.std(ddof=1)), 5),
        },
        "n_2026": int(histograms[2026].sum()),
    }
    if verbose:
        yearly_print = yearly_fits.copy()
        yearly_print[["mean_score", "score_sd"]] = yearly_print[
            ["mean_score", "score_sd"]
        ].round(2)
        mixture_print = mixture_fits.copy()
        score_columns = [
            "usual_mean_score",
            "usual_score_sd",
            "atypical_mean_score",
            "atypical_score_sd",
        ]
        mixture_print[score_columns] = mixture_print[score_columns].round(2)
        mixture_print["fraction_atypical"] = mixture_print["fraction_atypical"].round(5)
        print("\nYEARLY USUAL BETA-BINOMIAL FITS (2021-2025)")
        print(yearly_print.to_string(index=False))
        print("\n2026 MIXTURE FITS, ONE PER USUAL YEAR")
        print(mixture_print.to_string(index=False))
        print("\nFRACTION-ATYPICAL SUMMARY ACROSS THE FIVE FITS")
        print(json.dumps(result, indent=2))
        if output_dir is not None:
            print(f"\nResults saved to: {output_dir.resolve()}")
    return result


def main() -> None:
    args = parse_args()
    analyze_program(
        program=args.program,
        data_path=args.data,
        output_dir=None if args.no_output else args.output_dir,
        verbose=True,
    )


if __name__ == "__main__":
    main()
