# MinexPy-GUI

MinexPy-GUI is a local Flask application that brings MinexPy statistical analysis into a browser-based workflow.
It is designed for researchers who want quick geochemical statistics without writing scripts.

## Current Scope (V1)

- Upload `.csv`, `.xlsx`, or `.xls` files.
- Preview the first rows of uploaded data.
- Select one or multiple columns for MinexPy statistical summary generation.
- Review results in a table where rows are selected elements and columns are statistical metrics.
- Download analysis results as CSV.
- Navigate project pages: `Home`, `About`, and `Changelog`.

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app locally:

```bash
python3 app.py
```

4. Open `http://127.0.0.1:5000` in your browser.

## Local Configuration

The app is local-first and does not require server deployment settings.
Optional environment variables:

- `MAX_CONTENT_LENGTH_MB` (default: `20`)
- `RESULT_TTL_SECONDS` (default: `3600`)
- `RESULT_CLEANUP_INTERVAL_SECONDS` (default: `300`)
- `RESULT_STORAGE_DIR` (default: system temp directory)
- `DATASET_STORAGE_DIR` (default: system temp directory)

## API Routes

- `POST /analysis/upload`: Upload and preview a dataset.
- `POST /analysis/statistics`: Generate MinexPy statistical summary for selected columns.
- `GET /analysis/download/<result_id>`: Download generated results as CSV.

Backward-compatible aliases are also kept:

- `POST /analyze`
- `POST /analyze/column`
- `GET /download/<result_id>`

## Project Structure

```text
app.py
minexpygui/
  __init__.py
  routes/
    main.py
    analysis.py
  services/
    file_parser.py
    dataset_store.py
    minexpy_adapter.py
    result_store.py
  templates/
  static/
```

## MinexPy References

- Repository: https://github.com/SupernovifieD/MinexPy
- Documentation: https://SupernovifieD.github.io/MinexPy/

## Roadmap Direction

The architecture uses capability-oriented naming so additional MinexPy modules can be added later, including:

- Correlation analysis
- Statistical visualization
- Geochemical mapping
- Extended data processing tools

## Manual Verification Checklist

1. Run `python3 app.py` and open the home page.
2. Upload a valid CSV/XLSX file and confirm preview rows appear.
3. Select one column and verify a one-row statistics result.
4. Select multiple columns and verify a multi-row statistics result.
5. Include a non-numeric column and confirm strict validation error is shown.
6. Download CSV and confirm it matches the rendered table.
7. Visit About page and verify MinexPy links are visible.
