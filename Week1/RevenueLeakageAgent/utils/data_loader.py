"""CSV loading, cleaning, and Pydantic validation."""

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
from pydantic import ValidationError

from utils.models import NUMERIC_COLUMNS, REQUIRED_COLUMNS, RevenueRecord


@dataclass
class DataLoadResult:
    dataframe: pd.DataFrame | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.dataframe is not None and not self.dataframe.empty


def load_revenue_csv(source: str | Path | bytes | BinaryIO) -> DataLoadResult:
    """Read a CSV, validate its schema and rows, and return clean data."""
    result = DataLoadResult()
    try:
        csv_source = BytesIO(source) if isinstance(source, bytes) else source
        # Keep literal labels such as the issue type "None" as strings. Numeric
        # blanks are still converted to NaN during the explicit coercion below.
        dataframe = pd.read_csv(csv_source, keep_default_na=False)
    except FileNotFoundError:
        result.errors.append("The default RevenueLeakage.csv file could not be found.")
        return result
    except (pd.errors.ParserError, UnicodeDecodeError, OSError, ValueError) as exc:
        result.errors.append(f"The CSV could not be read: {exc}")
        return result

    dataframe.columns = [str(column).strip().lower() for column in dataframe.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        result.errors.append("Missing required columns: " + ", ".join(missing))
        return result
    if dataframe.empty:
        result.errors.append("The CSV contains headers but no invoice rows.")
        return result

    dataframe = dataframe[REQUIRED_COLUMNS].copy()
    dataframe["billing_date"] = pd.to_datetime(dataframe["billing_date"], errors="coerce")
    for column in NUMERIC_COLUMNS:
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

    valid_indices: list[int] = []
    validation_messages: list[str] = []
    for index, row in dataframe.iterrows():
        record = row.to_dict()
        record["billing_date"] = (
            record["billing_date"].date()
            if pd.notna(record["billing_date"])
            else None
        )
        try:
            RevenueRecord.model_validate(record)
            valid_indices.append(index)
        except ValidationError as exc:
            first_error = exc.errors()[0]
            location = ".".join(str(part) for part in first_error["loc"])
            validation_messages.append(
                f"Row {index + 2}: {location} {first_error['msg'].lower()}"
            )

    if validation_messages:
        preview = validation_messages[:5]
        suffix = "" if len(validation_messages) <= 5 else f" (+{len(validation_messages) - 5} more)"
        result.warnings.append(
            f"Skipped {len(validation_messages)} invalid row(s): " + "; ".join(preview) + suffix
        )

    dataframe = dataframe.loc[valid_indices].reset_index(drop=True)
    if dataframe.empty:
        result.errors.append("No valid invoice rows remained after validation.")
        return result

    supplied_leakage = dataframe["leakage_amount"].copy()
    dataframe["leakage_amount"] = (
        dataframe["expected_amount"] - dataframe["billed_amount"]
    ).round(2)
    differences = (supplied_leakage - dataframe["leakage_amount"]).abs() > 0.01
    if differences.any():
        result.warnings.append(
            f"Recalculated leakage_amount for {int(differences.sum())} row(s) using expected minus billed."
        )

    dataframe["billing_difference_abs"] = dataframe["leakage_amount"].abs()
    result.dataframe = dataframe
    return result
