#!/usr/bin/env python3
"""Build a self-contained interactive plot for all program-level results."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from bokeh.embed import file_html
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Div, HoverTool
from bokeh.plotting import figure
from bokeh.resources import INLINE

BASE_DIR = Path(__file__).resolve().parents[2]
RESULTS_CSV = Path(__file__).resolve().parent / "results_all" / "all_program_results.csv"
DATA_CSV = BASE_DIR / "data" / "processed" / "aciertos_unam_2021_2026.csv"
OUTPUT_HTML = Path(__file__).resolve().parent / "results_all" / "fraction_vs_expected_interactive.html"

AREA_NAMES = {
    1: "Ciencias Físico-Matemáticas e Ingenierías",
    2: "Ciencias Biológicas, Químicas y de la Salud",
    3: "Ciencias Sociales",
    4: "Humanidades y Artes",
}
AREA_COLORS = {1: "#326B85", 2: "#477A50", 3: "#B36A2E", 4: "#76528A"}


def load_results() -> pd.DataFrame:
    results = pd.read_csv(RESULTS_CSV)
    if "num_2026" not in results:
        raw = pd.read_csv(DATA_CSV, usecols=["año", "carrera", "aciertos"])
        counts = (
            raw.loc[raw["año"].eq(2026)]
            .dropna(subset=["aciertos"])
            .groupby("carrera")
            .size()
        )
        results.insert(2, "num_2026", results["program"].map(counts).astype(int))
    results["area_name"] = results["area"].map(AREA_NAMES)
    maximum = results["num_2026"].max()
    results["point_size"] = 9 + 27 * np.sqrt(results["num_2026"] / maximum)
    return results


def build_plot(results: pd.DataFrame):
    plot = figure(
        height=610,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
        x_axis_label="Puntaje esperado · promedio 2021–2025",
        y_axis_label="Fracción atípica inferida · 2026",
        y_range=(0.07, 1.04),
        toolbar_location="above",
    )
    plot.background_fill_color = "#E2DDCC"
    plot.border_fill_color = "#E2DDCC"
    plot.outline_line_color = "#CEC6AF"
    plot.grid.grid_line_color = "#CEC6AF"
    plot.grid.grid_line_alpha = 0.75
    plot.axis.axis_line_color = "#59616C"
    plot.axis.major_tick_line_color = "#59616C"
    plot.axis.minor_tick_line_color = None
    plot.axis.axis_label_text_font = "IBM Plex Sans"
    plot.axis.axis_label_text_font_style = "normal"
    plot.axis.major_label_text_font = "IBM Plex Mono"
    plot.yaxis.formatter.use_scientific = False
    plot.yaxis.major_label_overrides = {
        0.2: "20%",
        0.4: "40%",
        0.6: "60%",
        0.8: "80%",
        1.0: "100%",
    }

    hover_renderers = []
    for area in range(1, 5):
        subset = results.loc[results["area"].eq(area)].copy()
        source = ColumnDataSource(subset)
        renderer = plot.scatter(
            x="expected_score_mean",
            y="fraction_atypical_mean",
            size="point_size",
            source=source,
            color=AREA_COLORS[area],
            fill_alpha=0.75,
            line_color="#ECE8DC",
            line_width=1.5,
            hover_fill_alpha=1,
            hover_line_color="#1B2430",
            legend_label=f"Área {area} · {AREA_NAMES[area]}",
            name=f"area_{area}",
        )
        hover_renderers.append(renderer)

    tooltips = """
    <div class="unam-tooltip">
      <div class="tooltip-area">ÁREA @area</div>
      <div class="tooltip-title">@program</div>
      <div class="tooltip-area-name">@area_name</div>
      <div class="tooltip-students"><span>Aspirantes 2026: </span><b>@num_2026{0,0}</b></div>
      <div class="tooltip-row"><span>Esperado 2021–2025: </span><b>@expected_score_mean{0.00} ± @expected_score_stdev{0.00}</b></div>
      <div class="tooltip-row"><span>Observado 2026: </span><b>@obtained_score_mean{0.00} ± @obtained_score_stdev{0.00}</b></div>
      <div class="tooltip-row"><span>Componente atípico 2026: </span><b>@inferred_atypical_mean{0.00} ± @inferred_atypical_stdev{0.00}</b></div>
      <div class="tooltip-row tooltip-highlight"><span>Fracción atípica 2026: </span><b>@fraction_atypical_mean{0.00%} ± @fraction_atypical_stdev{0.00%}</b></div>
      <div class="tooltip-note"><i>Media ± desviación estándar</i></div>
    </div>
    """
    plot.add_tools(HoverTool(tooltips=tooltips, renderers=hover_renderers, point_policy="follow_mouse"))
    plot.legend.location = "top_right"
    plot.legend.click_policy = "hide"
    plot.legend.background_fill_color = "#ECE8DC"
    plot.legend.background_fill_alpha = 0.92
    plot.legend.border_line_color = "#CEC6AF"
    plot.legend.label_text_font = "IBM Plex Sans"
    plot.legend.label_text_font_style = "normal"
    return plot


def main() -> None:
    results = load_results()
    header = Div(
        text="""
        <section class="unam-header">
          <p class="eyebrow">folio· 2021 — 2026 · admisión a licenciatura</p>
          <h1>Resultados atípicos por carrera</h1>
          <p class="lede">Compara el puntaje esperado —estimado con los resultados de
          2021 a 2025— con la fracción atípica inferida para 2026. Cada círculo
          representa una carrera y su tamaño indica cuántos aspirantes presentaron examen.</p>
          <p class="disclaimer"><b>Nota:</b> “atípico” describe pertenencia al componente
          de puntajes altos del modelo estadístico. No identifica conductas individuales
          ni demuestra por sí solo la causa de esos resultados.</p>
        </section>
        """,
        sizing_mode="stretch_width",
    )
    instructions = Div(
        text="""
        <div class="plot-note">
          Pasa el cursor sobre un punto para consultar todos los resultados.
          Haz clic en un área de la leyenda para ocultarla o mostrarla.
        </div>
        """,
        sizing_mode="stretch_width",
    )
    footer = Div(
        text="""
        <footer><b>Metodología.</b> Cada carrera se modeló con distribuciones
        beta-binomiales. Los parámetros de 2021–2025 definen el componente usual;
        la distribución 2026 se ajustó como una mezcla usual + atípica. Se excluyen
        aspirantes sin puntaje registrado.</footer>
        """,
        sizing_mode="stretch_width",
    )
    page = column(header, instructions, build_plot(results), footer, sizing_mode="stretch_width")
    template = """
    {% block preamble %}
    <style>
      html, body { margin: 0; background: #ECE8DC; color: #1B2430; }
      body { font-family: "IBM Plex Sans", system-ui, sans-serif; }
      .bk-Row, .bk-Column { max-width: 1160px; margin-left: auto; margin-right: auto; }
      .unam-header { padding: 48px 26px 10px; max-width: 820px; }
      .eyebrow { color:#59616C; font: 12px "IBM Plex Mono", monospace; letter-spacing:.11em; text-transform:uppercase; }
      .eyebrow::first-letter { color:#B23A2E; }
      h1 { font: 600 clamp(38px,6vw,62px)/1.04 Georgia, serif; margin: 16px 0; }
      .lede { color:#59616C; font-size:17px; max-width:70ch; line-height:1.55; }
      .disclaimer { border-left:2px solid #9AA3AE; color:#59616C; font-size:13px; max-width:72ch; padding-left:13px; }
      .plot-note { border-top:1px dashed #CEC6AF; color:#59616C; font:12px "IBM Plex Mono",monospace; margin:8px 26px 0; padding:16px 0 4px; }
      footer { border-top:1px solid #CEC6AF; color:#59616C; font-size:13px; line-height:1.55; margin:26px; padding:24px 0 48px; max-width:78ch; }
      .bk-tooltip { background:#ECE8DC !important; border:1px solid #CEC6AF !important; color:#1B2430 !important; padding:0 !important; }
      .unam-tooltip { min-width:315px; padding:15px; }
      .tooltip-area { color:#B23A2E; font:500 11px "IBM Plex Mono",monospace; letter-spacing:.08em; }
      .tooltip-title { font:600 20px/1.15 Georgia,serif; margin:5px 0 3px; max-width:330px; }
      .tooltip-area-name { color:#59616C; font-size:11px; margin-bottom:11px; max-width:330px; }
      .tooltip-students, .tooltip-row { align-items:end; border-top:1px dashed #CEC6AF; display:flex; justify-content:space-between; gap:14px; padding:7px 0; }
      .tooltip-students span, .tooltip-row span { color:#59616C; font:10px "IBM Plex Mono",monospace; text-transform:uppercase; }
      .tooltip-students b, .tooltip-row b { font:500 13px "IBM Plex Mono",monospace; white-space:nowrap; }
      .tooltip-students b { font-size:18px; }
      .tooltip-highlight { background:#E7CFC9; border-left:3px solid #B23A2E; margin:4px -7px 0; padding:9px 7px; }
      .tooltip-highlight b { color:#B23A2E; }
      .tooltip-note { color:#59616C; font-size:10px; margin-top:7px; }
    </style>
    {% endblock %}
    {% block contents %}{{ super() }}{% endblock %}
    """
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(
        file_html(page, INLINE, "Resultados atípicos por carrera · UNAM 2026", template=template),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_HTML} ({OUTPUT_HTML.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
