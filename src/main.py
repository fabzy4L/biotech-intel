from . import fda_cder, clinicaltrials, pubmed, biorxiv, sec_edgar
from .common import save_csv
import pandas as pd

def run_all():
    dfs = []
    for mod in (fda_cder, clinicaltrials, pubmed, biorxiv, sec_edgar):
        try:
            df = mod.run()
            if df is not None and not df.empty:
                dfs.append(df)
        except Exception as e:
            print(f"error in {mod.__name__}: {e}")
    if dfs:
        all_df = pd.concat(dfs, ignore_index=True, sort=False)
        save_csv(all_df, "biotech_events")
    else:
        print("no data pulled")

if __name__ == "__main__":
    run_all()
