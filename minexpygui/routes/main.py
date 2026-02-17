"""Routes for static pages and shared template rendering helpers."""

from pathlib import Path
import html
from typing import Optional

from flask import Blueprint, current_app, render_template

try:
    import markdown as markdown_lib
except ImportError:  # pragma: no cover - fallback only used without optional dependency
    markdown_lib = None


main_bp = Blueprint("main", __name__)


def render_home(
    error_message: Optional[str] = None,
    info_message: Optional[str] = None,
    preview_table_html: Optional[str] = None,
    preview_row_count: Optional[int] = None,
    dataset_id: Optional[str] = None,
    available_columns=None,
    selected_columns=None,
    result_table_html: Optional[str] = None,
    result_id: Optional[str] = None,
    result_row_count: Optional[int] = None,
    source_filename: Optional[str] = None,
):
    """Render the home page with upload, selection, and analysis state."""
    return render_template(
        "home.html",
        error_message=error_message,
        info_message=info_message,
        preview_table_html=preview_table_html,
        preview_row_count=preview_row_count,
        dataset_id=dataset_id,
        available_columns=available_columns or [],
        selected_columns=selected_columns or [],
        result_table_html=result_table_html,
        result_id=result_id,
        result_row_count=result_row_count,
        source_filename=source_filename,
    )


@main_bp.get("/")
def home():
    """Render the main analysis page."""
    return render_home()


@main_bp.get("/about")
def about():
    """Render the project information page."""
    return render_template("about.html")


@main_bp.get("/changelog")
def changelog():
    """Render CHANGELOG.md as HTML if the file exists."""
    changelog_path = Path(current_app.root_path).parent / "CHANGELOG.md"
    if changelog_path.exists():
        changelog_text = changelog_path.read_text(encoding="utf-8")
        if markdown_lib is not None:
            changelog_html = markdown_lib.markdown(
                changelog_text,
                extensions=["fenced_code", "tables"],
            )
        else:
            changelog_html = f"<pre>{html.escape(changelog_text)}</pre>"
    else:
        changelog_html = "<p>Changelog not found.</p>"
    return render_template("changelog.html", changelog_html=changelog_html)
