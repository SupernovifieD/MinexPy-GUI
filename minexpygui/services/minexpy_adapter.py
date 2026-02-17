"""Adapters that translate application data into MinexPy statistical summaries."""

from typing import Iterable, List

import pandas as pd


class AnalysisError(RuntimeError):
    """Raised when analysis requests cannot be fulfilled safely."""


def run_statistical_summary_for_columns(df: pd.DataFrame, column_names: Iterable[str]) -> pd.DataFrame:
    """Run MinexPy summary statistics for one or more selected columns.

    The returned table uses rows for element columns and columns for statistical metrics.
    """
    selected_columns = _normalize_column_names(column_names)
    _assert_columns_exist(df, selected_columns)

    numeric_df = df[selected_columns].apply(pd.to_numeric, errors="coerce")
    invalid_columns = [name for name in selected_columns if numeric_df[name].dropna().empty]
    if invalid_columns:
        invalid_text = ", ".join(invalid_columns)
        raise AnalysisError(
            "Analysis failed because these selected columns contain no numeric values: "
            f"{invalid_text}"
        )

    StatisticalAnalyzer = _load_statistical_analyzer()

    try:
        analyzer = StatisticalAnalyzer(numeric_df[selected_columns])
        summary = analyzer.summary(as_dataframe=True)
    except Exception as error:
        raise AnalysisError(
            "MinexPy StatisticalAnalyzer could not generate summary statistics for "
            "the selected columns."
        ) from error

    result_df = _summary_to_table(summary, selected_columns=selected_columns)
    if result_df.empty:
        raise AnalysisError("MinexPy returned an empty statistical summary.")
    return result_df


def _load_statistical_analyzer():
    """Import and return MinexPy's StatisticalAnalyzer class."""
    try:
        from minexpy.stats import StatisticalAnalyzer  # type: ignore
    except Exception as error:
        raise AnalysisError(
            "MinexPy is not installed or does not expose minexpy.stats.StatisticalAnalyzer."
        ) from error
    return StatisticalAnalyzer


def _normalize_column_names(column_names: Iterable[str]) -> List[str]:
    """Normalize incoming column names while preserving order and uniqueness."""
    selected = [name.strip() for name in column_names if name and name.strip()]
    selected = list(dict.fromkeys(selected))
    if not selected:
        raise AnalysisError("Please select at least one column to analyze.")
    return selected


def _assert_columns_exist(df: pd.DataFrame, selected_columns: List[str]) -> None:
    """Raise if any selected column is not available in the DataFrame."""
    missing_columns = [name for name in selected_columns if name not in df.columns]
    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise AnalysisError(
            f"Selected columns are not available in the uploaded data: {missing_text}"
        )


def _summary_to_table(summary, selected_columns: List[str]) -> pd.DataFrame:
    """Convert MinexPy summary output into a consistent table for UI and CSV output."""
    if isinstance(summary, pd.DataFrame):
        table = summary.copy()

        selected_set = set(selected_columns)
        column_name_set = {str(name) for name in table.columns}
        index_name_set = {str(name) for name in table.index}

        # Some analyzers return metrics on rows and columns on headers; transpose if needed.
        if selected_set.intersection(column_name_set) and not selected_set.intersection(index_name_set):
            table = table.transpose()

        table.index = [str(index_value) for index_value in table.index]
        table.columns = [str(column_name) for column_name in table.columns]
        table = table.reset_index().rename(columns={"index": "element"})
    elif isinstance(summary, pd.Series):
        metric_data = {str(metric): value for metric, value in summary.items()}
        table = pd.DataFrame([{"element": selected_columns[0], **metric_data}])
    elif isinstance(summary, dict):
        metric_data = {str(metric): value for metric, value in summary.items()}
        table = pd.DataFrame([{"element": selected_columns[0], **metric_data}])
    else:
        raise AnalysisError(
            "MinexPy returned an unsupported summary format for table rendering."
        )

    if "element" not in table.columns:
        table.insert(0, "element", selected_columns[0])

    table["element"] = table["element"].astype(str)
    order_lookup = {name: position for position, name in enumerate(selected_columns)}
    table["_selection_order"] = table["element"].map(lambda name: order_lookup.get(name, len(order_lookup)))
    table = table.sort_values(by="_selection_order").drop(columns="_selection_order")
    table.columns = [str(column_name) for column_name in table.columns]
    return table.reset_index(drop=True)
