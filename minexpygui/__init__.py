"""Flask application factory and runtime configuration for MinexPy-GUI."""

import os
import tempfile
import time
from pathlib import Path

from flask import Flask
from werkzeug.exceptions import RequestEntityTooLarge

from minexpygui.routes.analysis import analysis_bp
from minexpygui.routes.main import main_bp, render_home
from minexpygui.services.dataset_store import cleanup_expired_datasets
from minexpygui.services.result_store import cleanup_expired


def create_app() -> Flask:
    """Create and configure the Flask app for local execution."""
    app = Flask(__name__)

    max_content_mb = int(os.getenv("MAX_CONTENT_LENGTH_MB", "20"))
    app.config["MAX_CONTENT_LENGTH"] = max_content_mb * 1024 * 1024
    app.config["RESULT_TTL_SECONDS"] = int(os.getenv("RESULT_TTL_SECONDS", "3600"))
    app.config["RESULT_CLEANUP_INTERVAL_SECONDS"] = int(
        os.getenv("RESULT_CLEANUP_INTERVAL_SECONDS", "300")
    )
    app.config["RESULT_STORAGE_DIR"] = os.getenv(
        "RESULT_STORAGE_DIR",
        str(Path(tempfile.gettempdir()) / "minexpygui-results"),
    )
    app.config["DATASET_STORAGE_DIR"] = os.getenv(
        "DATASET_STORAGE_DIR",
        str(Path(tempfile.gettempdir()) / "minexpygui-datasets"),
    )

    Path(app.config["RESULT_STORAGE_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATASET_STORAGE_DIR"]).mkdir(parents=True, exist_ok=True)

    app.register_blueprint(main_bp)
    app.register_blueprint(analysis_bp)

    app.extensions["last_result_cleanup_at"] = 0.0

    with app.app_context():
        cleanup_expired(
            storage_dir=app.config["RESULT_STORAGE_DIR"],
            ttl_seconds=app.config["RESULT_TTL_SECONDS"],
        )
        cleanup_expired_datasets(
            storage_dir=app.config["DATASET_STORAGE_DIR"],
            ttl_seconds=app.config["RESULT_TTL_SECONDS"],
        )

    @app.before_request
    def _cleanup_expired_result_files() -> None:
        # Periodically clean temporary artifacts used for dataset/result storage.
        now = time.time()
        last_run = app.extensions.get("last_result_cleanup_at", 0.0)
        interval = app.config["RESULT_CLEANUP_INTERVAL_SECONDS"]
        if now - last_run >= interval:
            cleanup_expired(
                storage_dir=app.config["RESULT_STORAGE_DIR"],
                ttl_seconds=app.config["RESULT_TTL_SECONDS"],
            )
            cleanup_expired_datasets(
                storage_dir=app.config["DATASET_STORAGE_DIR"],
                ttl_seconds=app.config["RESULT_TTL_SECONDS"],
            )
            app.extensions["last_result_cleanup_at"] = now

    @app.errorhandler(RequestEntityTooLarge)
    def _handle_file_too_large(_error):
        """Return a friendly page when upload size exceeds the configured limit."""
        max_mb = int(app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024))
        return (
            render_home(error_message=f"File is too large. The maximum size is {max_mb} MB."),
            413,
        )

    return app
