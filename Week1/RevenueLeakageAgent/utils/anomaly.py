"""IQR-based anomaly detection utilities."""

import pandas as pd


def detect_iqr_anomalies(
    dataframe: pd.DataFrame, column: str, multiplier: float = 1.5
) -> tuple[pd.DataFrame, float, float]:
    if column not in dataframe.select_dtypes(include="number").columns:
        raise ValueError(f"{column} is not a numeric column")

    values = dataframe[column].dropna()
    if values.empty:
        return dataframe.iloc[0:0].copy(), 0.0, 0.0
    q1, q3 = values.quantile([0.25, 0.75])
    spread = q3 - q1
    lower = float(q1 - multiplier * spread)
    upper = float(q3 + multiplier * spread)
    mask = (dataframe[column] < lower) | (dataframe[column] > upper)
    anomalies = dataframe.loc[mask].copy()
    anomalies["anomaly_direction"] = anomalies[column].apply(
        lambda value: "Low" if value < lower else "High"
    )
    return anomalies, lower, upper

