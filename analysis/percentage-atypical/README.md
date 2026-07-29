# Percentage of atypical results

`analyze_program.py` fits the 2021–2025 usual score distributions and estimates
the atypical fraction in 2026 for one UNAM program.

Run it from the repository root and provide the exact `carrera` label plus a new
output folder:

```bash
python3 analysis/percentage-atypical/analyze_program.py \
  --program "MATEMATICAS" \
  --output-dir analysis/percentage-atypical/results_program_matematicas
```

The folder is created automatically and contains the fitted parameters, summary
tables, and diagnostic plots.

For ACTUARIA, using the default settings is enough:

```bash
python3 analysis/percentage-atypical/analyze_program.py
```
