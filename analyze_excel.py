import pandas as pd

try:
    df = pd.read_excel('Elite Premier Tutoring Dailysheet v1.xlsx')
    print("Columns:", df.columns.tolist())
    print("First few rows:")
    print(df.head())
except Exception as e:
    print("Error reading excel:", e)
