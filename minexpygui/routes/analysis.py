"""HTTP routes for dataset upload, statistical analysis, and result download."""

import io
import logging

from flask import Blueprint, current_app, request, send_file

from minexpygui.routes.main import render_home
from minexpygui.services.dataset_store import (
    DatasetNotFoundError,
    load_dataset,
    save_dataset,
)
from minexpygui.services.file_parser import FileParsingError, parse_uploaded_file
from minexpygui.services.minexpy_adapter import (
    AnalysisError,
    run_statistical_summary_for_columns,
)
from minexpygui.services.result_store import (
    ResultNotFoundError,
    load_result_csv,
    save_result,
)


analysis_bp = Blueprint("analysis", __name__)
logger = logging.getLogger(__name__)


@analysis_bp.post("/analysis/upload")
def upload_dataset():
    """Upload a file, parse it, persist it temporarily, and render a data preview."""
    uploaded_file = request.files.get("data_file")
    if uploaded_file is None:
        return render_home(error_message="Please choose a CSV or Excel file before submitting."), 400

    try:
        source_df = parse_uploaded_file(uploaded_file)
        source_filename = uploaded_file.filename or "uploaded_file"
        dataset_id = save_dataset(
            source_df,
            source_filename=source_filename,
            storage_dir=current_app.config["DATASET_STORAGE_DIR"],
        )
        return render_home(
            info_message=(
                "File uploaded successfully. Select one or more columns to generate "
                "statistical analysis."
            ),
            preview_table_html=_build_preview_table_html(source_df),
            preview_row_count=min(len(source_df.index), 8),
            dataset_id=dataset_id,
            available_columns=list(source_df.columns),
            source_filename=source_filename,
        )
    except FileParsingError as error:
        return render_home(error_message=str(error)), 400
    except Exception:
        logger.exception("Unexpected error during analysis")
        return (
            render_home(
                error_message="Unexpected error while processing your file. Please try again."
            ),
            500,
        )


@analysis_bp.post("/analysis/statistics")
def generate_statistics():
    """Run MinexPy statistical summary for selected columns from an uploaded dataset."""
    dataset_id = (request.form.get("dataset_id") or "").strip()
    selected_columns = _extract_selected_columns_from_form()

    if not dataset_id:
        return render_home(error_message="Missing dataset context. Upload a file and try again."), 400

    try:
        source_df, source_filename = load_dataset(
            dataset_id=dataset_id,
            storage_dir=current_app.config["DATASET_STORAGE_DIR"],
            ttl_seconds=current_app.config["RESULT_TTL_SECONDS"],
        )
    except DatasetNotFoundError:
        return (
            render_home(
                error_message="Your uploaded data is unavailable or expired. Please upload the file again."
            ),
            404,
        )

    available_columns = list(source_df.columns)
    if not selected_columns:
        return (
            render_home(
                error_message="Please select at least one column to analyze.",
                preview_table_html=_build_preview_table_html(source_df),
                preview_row_count=min(len(source_df.index), 8),
                dataset_id=dataset_id,
                available_columns=available_columns,
                source_filename=source_filename,
            ),
            400,
        )

    missing_columns = [name for name in selected_columns if name not in available_columns]
    if missing_columns:
        missing_text = ", ".join(missing_columns)
        return (
            render_home(
                error_message=f"Selected columns are not available in the uploaded data: {missing_text}",
                preview_table_html=_build_preview_table_html(source_df),
                preview_row_count=min(len(source_df.index), 8),
                dataset_id=dataset_id,
                available_columns=available_columns,
                selected_columns=selected_columns,
                source_filename=source_filename,
            ),
            400,
        )

    try:
        result_df = run_statistical_summary_for_columns(source_df, selected_columns)
        result_id = save_result(
            result_df,
            storage_dir=current_app.config["RESULT_STORAGE_DIR"],
        )
    except AnalysisError as error:
        logger.warning("Analysis request failed: %s", error)
        return (
            render_home(
                error_message=str(error),
                preview_table_html=_build_preview_table_html(source_df),
                preview_row_count=min(len(source_df.index), 8),
                dataset_id=dataset_id,
                available_columns=available_columns,
                selected_columns=selected_columns,
                source_filename=source_filename,
            ),
            400,
        )
    except Exception:
        logger.exception("Unexpected error during statistical analysis")
        return (
            render_home(
                error_message=(
                    "Unexpected error while analyzing the selected columns. Please try again."
                ),
                preview_table_html=_build_preview_table_html(source_df),
                preview_row_count=min(len(source_df.index), 8),
                dataset_id=dataset_id,
                available_columns=available_columns,
                selected_columns=selected_columns,
                source_filename=source_filename,
            ),
            500,
        )

    selected_count = len(selected_columns)
    noun = "column" if selected_count == 1 else "columns"
    return render_home(
        info_message=(
            f"Statistical analysis generated successfully for {selected_count} {noun}. "
            "You can select another set and run again."
        ),
        preview_table_html=_build_preview_table_html(source_df),
        preview_row_count=min(len(source_df.index), 8),
        dataset_id=dataset_id,
        available_columns=available_columns,
        selected_columns=selected_columns,
        result_table_html=_build_result_table_html(result_df),
        result_id=result_id,
        result_row_count=len(result_df.index),
        source_filename=source_filename,
    )


@analysis_bp.get("/analysis/download/<result_id>")
def download_statistics(result_id: str):
    """Download a stored CSV artifact generated by a previous analysis run."""
    try:
        csv_bytes = load_result_csv(
            result_id=result_id,
            storage_dir=current_app.config["RESULT_STORAGE_DIR"],
            ttl_seconds=current_app.config["RESULT_TTL_SECONDS"],
        )
    except ResultNotFoundError:
        return (
            render_home(
                error_message="The requested result is unavailable or has expired. Upload again to regenerate."
            ),
            404,
        )

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"analysis_{result_id[:8]}.csv",
    )


@analysis_bp.post("/analyze")
def upload_dataset_legacy():
    """Backward-compatible alias for the original upload endpoint."""
    return upload_dataset()


@analysis_bp.post("/analyze/column")
def generate_statistics_legacy():
    """Backward-compatible alias for the original statistics endpoint."""
    return generate_statistics()


@analysis_bp.get("/download/<result_id>")
def download_statistics_legacy(result_id: str):
    """Backward-compatible alias for the original download endpoint."""
    return download_statistics(result_id)


def _extract_selected_columns_from_form():
    """Extract and normalize selected columns from form payload."""
    raw_values = request.form.getlist("column_names")
    selected = [value.strip() for value in raw_values if value and value.strip()]

    # Keep legacy support for old templates that submit a single `column_name`.
    legacy_column_name = (request.form.get("column_name") or "").strip()
    if legacy_column_name:
        selected.append(legacy_column_name)

    # Preserve selection order while removing duplicates.
    return list(dict.fromkeys(selected))


def _build_preview_table_html(source_df):
    """Render a small HTML preview table for the uploaded dataset."""
    return source_df.head(8).to_html(
        classes=["preview-table"],
        index=False,
        border=0,
        justify="left",
    )


def _build_result_table_html(result_df):
    """Render the statistical result DataFrame as an HTML table."""
    return result_df.to_html(
        classes=["result-table"],
        index=False,
        border=0,
        justify="left",
    )
