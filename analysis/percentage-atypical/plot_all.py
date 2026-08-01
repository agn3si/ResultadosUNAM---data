from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results_all"
PATH_RESULTS_ALL = DEFAULT_OUTPUT / "all_program_results.csv"

def add_1to1_line(vars,pairplot):
    var1, var2 = vars
    for ax in pairplot.axes.flat:
        if ax is not None:
            if ax.get_xlabel()==var1 and ax.get_ylabel()==var2:
                # get limits
                xlims = ax.get_xlim()
                ylims = ax.get_ylim()
                # draw the line
                ax.plot(xlims,xlims,
                        zorder=-5,
                        ls='--',
                        c='forestgreen',
                        marker=None)
                # restore limits
                ax.set_xlim(xlims)
                ax.set_ylim(ylims)



def make_pairplot(results,
                  is_gt100=False,
                  is_gt1000=False,):
    if is_gt100 and is_gt1000:
        print("Conflicting arguments provided: >100 and >1000 plot requested simultaneously. Exiting the plotting function.")
        return
    
    # Rename columns in the plot
    cols_new = {
        'area': 'area',
        'program': 'program',
        'num_2026': 'N_2026',
        'expected_score_mean': 'Score 21-25',
        'expected_score_stdev': 'Score 21-25 stdev',
        'obtained_score_mean': 'Score 26',
        'obtained_score_stdev': 'Score 26 stdev',
        'inferred_atypical_mean': 'Score 26\nof atypical',
        'inferred_atypical_stdev': 'Score 26\nof atypical stdev',
        'fraction_atypical_mean': 'Fraction of\natypical 26',
        'fraction_atypical_stdev': 'Fraction of\natypical 26 stdev',
    }
    results_renamed = results.rename(columns=cols_new)
    if is_gt100:
        results_renamed = results_renamed[results_renamed['N_2026']>=100]
    if is_gt1000:
        results_renamed = results_renamed[results_renamed['N_2026']>=1000]

    # Adding interesting plots
    results_renamed["Boost naive"] = -results_renamed["Score 21-25"]+results_renamed["Score 26"]
    results_renamed["Boost inferred"] = results_renamed["Score 26\nof atypical"]-results_renamed["Score 26"]

    # Plot only columns that aren't stdev
    cols_all  = results_renamed.columns
    cols_plot = [e for e in cols_all if "stdev" not in e]

    # Remove column containing program names
    cols_plot.remove("program")

    # Columns to put in log-scale
    log_columns = ["N_2026"]


    pairplot = sns.pairplot(results_renamed, 
                 hue='area',
                 corner=True, 
                 kind='scatter',
                 diag_kind='kde',
                 vars=cols_plot,
                 height=1.4,
                 )

    for ax in pairplot.axes.flat:
        if ax is not None:
            if ax.get_xlabel() in log_columns:
                ax.set(xscale="log")
            if ax.get_ylabel() in log_columns:
                ax.set(yscale="log")

    # add 1 to 1 line
    add_1to1_line(["Score 21-25","Score 26"],pairplot)
    add_1to1_line(["Score 21-25","Score 26\nof atypical"],pairplot)
    add_1to1_line(["Score 26","Score 26\nof atypical"],pairplot)
    add_1to1_line(["Boost naive","Boost inferred"],pairplot)

    caption = '''
    All scores and fraction of atypical students are mean values.
    All values relative to "atypical" are obtained from the statistical analysis, i.e. inferred from a model.
    Boost naive: Score 2026 - average(scores 2021-2025), naive estimate of the 2026 anomaly.
    Boost inferred: Score 26 of atypical - average(2021-2025),
    \tmore accurate estimate of the value of the 2026 anomaly.
    '''
    if is_gt100:
        caption += "Same figure as 'pairplot_all.png', but removing programs where N_2026 < 100 to avoid small sample statistics."
    if is_gt1000:
        caption += "Same figure as 'pairplot_all.png', but removing programs where N_2026 < 1000 to avoid small sample statistics."

    plt.annotate(caption,
                 xy = (0.3,0.8),
                 xycoords='figure fraction',
                 )

    OUTPUT_FILE = DEFAULT_OUTPUT / "pairplot_all.png"
    if is_gt100:
        OUTPUT_FILE = DEFAULT_OUTPUT / "pairplot_all_gt100.png"
    if is_gt1000:
        OUTPUT_FILE = DEFAULT_OUTPUT / "pairplot_all_gt1000.png"
    plt.savefig(OUTPUT_FILE)
    # plt.show()



def main():
    results = pd.read_csv(PATH_RESULTS_ALL)

    make_pairplot(results)
    make_pairplot(results,is_gt100=True)
    make_pairplot(results,is_gt1000=True)


if __name__ == "__main__":
    main()
