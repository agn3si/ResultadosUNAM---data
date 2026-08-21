import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

fname = "notes-exam.csv"
df = pd.read_csv(fname)

sns.histplot(data = df, x = "Final DS", hue="Cheating", multiple="stack")

plt.annotate(f"N = {len(df)}", xy = (0.05,0.9), xycoords= "axes fraction")
plt.xlabel("Final Exam Grade")
plt.savefig("L3-app-phys-exam-hist.pdf",dpi=150,bbox_inches="tight")

# plt.show()