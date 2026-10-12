# Data Processing Hub

A Streamlit website with two separate tools:

1. **Transaction Detail Extractor** — reads CSV/Excel files and extracts `TD_Amount` and `TD_Txn_ID` from the `Transaction Detail` column.
2. **File Comparison & Reconciliation** — compares two CSV/Excel files using user-selected matching columns and produces matched and unmatched reports.

## Run locally

Install Python 3.10 or newer, then run these commands in a terminal from this folder:

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install dependencies and launch:
```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will show a local URL, usually `http://localhost:8501`.

## Host online using Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload `app.py` and `requirements.txt` to the repository root.
3. Visit https://share.streamlit.io/ and connect GitHub.
4. Create an app from the repository and choose `app.py` as the main file.
5. Deploy and test the website URL.

## Important notes

- The extractor expects a column named exactly `Transaction Detail`.
- The comparison tool lets the user select a matching column from each file.
- Comparison keys are converted to trimmed text. Leading zeros should be preserved in source files by storing IDs as text where possible.
- Duplicate keys can produce multiple matched combinations in the matched report.
- This starter app does not include user accounts or role-based access. If files contain sensitive financial or customer information, restrict access and review hosting/privacy requirements before publishing it.
- Colab-specific `files.upload()`, `files.download()`, `input()`, and `display()` calls have been replaced with web upload controls, selectors, previews, and download buttons.
