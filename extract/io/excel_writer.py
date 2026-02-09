import pandas as pd

def write_excel(rows: list[dict], excel_path: str):
    df = pd.DataFrame(rows)
    df.to_excel(excel_path, index=False)
