import io
import re
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Data Processing Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px;}
    [data-testid="stSidebar"] {background: #123C32;}
    [data-testid="stSidebar"] * {color: #ffffff;}
    .hero {
        background: linear-gradient(120deg, #123C32, #216B50);
        padding: 1.6rem 1.8rem; border-radius: 18px; color: white;
        margin-bottom: 1.3rem;
    }
    .hero h1 {color: white; margin-bottom: .35rem;}
    .hero p {color: #D7EDE2; margin-bottom: 0;}
    div.stButton > button[kind="primary"] {
        background: #16734D; border-color: #16734D; border-radius: 9px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def read_uploaded_file(uploaded_file):
    """Read a CSV or Excel upload into a DataFrame."""
    name = uploaded_file.name.lower()
    content = uploaded_file.getvalue()
    if name.endswith(".csv"):
        # utf-8-sig handles CSVs exported with a UTF-8 BOM.
        try:
            return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(content), encoding="latin-1")
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    raise ValueError("Unsupported file format. Upload a CSV, XLSX, or XLS file.")


def to_excel_bytes(df, sheet_name="Processed"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    buffer.seek(0)
    return buffer.getvalue()


def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def extract_td_amount_txn(detail):
    if pd.isna(detail):
        return pd.Series([None, None])
    detail = str(detail)
    amount_match = re.search(r"M\s*([\d,.]+)", detail, flags=re.IGNORECASE)
    amount = (
        float(amount_match.group(1).replace(",", ""))
        if amount_match
        else None
    )
    txn_match = re.search(r"Txn ID[:\s]*([\w.-]+)", detail, flags=re.IGNORECASE)
    txn_id = txn_match.group(1) if txn_match else None
    return pd.Series([amount, txn_id])


def hero(title, subtitle):
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def page_home():
    hero("Data Processing Hub", "Simple tools for transaction processing and file reconciliation.")
    st.write(
        "Choose a tool from the sidebar. Upload your files, review the results, "
        "and download processed reports."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔎 Transaction Detail Extractor")
        st.write(
            "Extract the amount and transaction ID from a **Transaction Detail** "
            "column in a CSV or Excel file."
        )
        st.caption("Input: one CSV or Excel file · Output: processed Excel workbook")
        if st.button("Open Transaction Extractor", use_container_width=True):
            st.session_state["page"] = "Transaction Detail Extractor"
            st.rerun()
    with col2:
        st.subheader("⇄ File Comparison & Reconciliation")
        st.write(
            "Match records across two files using any selected columns and inspect "
            "matched and unmatched records."
        )
        st.caption("Input: two CSV or Excel files · Output: three reports")
        if st.button("Open File Comparison", use_container_width=True):
            st.session_state["page"] = "File Comparison & Reconciliation"
            st.rerun()
    st.divider()
    st.info(
        "Supported formats: CSV, XLSX, and XLS. Check the preview and selected "
        "columns before downloading your reports."
    )


def page_extractor():
    hero("Transaction Detail Extractor", "Extract amounts and transaction IDs from transaction descriptions.")
    st.write(
        "Upload a file containing a column named **Transaction Detail**. "
        "The tool adds `TD_Amount` and `TD_Txn_ID` columns."
    )
    uploaded = st.file_uploader(
        "Choose one CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        key="extract_upload",
    )
    if uploaded is None:
        st.caption("Your original file is not modified.")
        return

    try:
        df = read_uploaded_file(uploaded)
    except Exception as exc:
        st.error(f"Could not read this file: {exc}")
        return

    st.success(f"Loaded **{uploaded.name}** · {len(df):,} rows · {len(df.columns):,} columns")
    with st.expander("Preview original data", expanded=True):
        st.dataframe(df.head(10), use_container_width=True)

    if "Transaction Detail" not in df.columns:
        st.error(
            'Required column "Transaction Detail" was not found. '
            "Please check the spelling and spaces in your column heading."
        )
        st.write("Available columns:", ", ".join(map(str, df.columns)))
        return

    if st.button("Extract transaction details", type="primary", use_container_width=True):
        try:
            extracted = df["Transaction Detail"].apply(extract_td_amount_txn)
            extracted.columns = ["TD_Amount", "TD_Txn_ID"]
            result = df.copy()
            result[["TD_Amount", "TD_Txn_ID"]] = extracted
            st.session_state["extract_result"] = result
            st.session_state["extract_source_name"] = uploaded.name
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            return

    result = st.session_state.get("extract_result")
    if result is not None:
        st.divider()
        st.subheader("Processing results")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total rows", f"{len(result):,}")
        c2.metric("Amounts extracted", f"{result['TD_Amount'].notna().sum():,}")
        c3.metric("Transaction IDs extracted", f"{result['TD_Txn_ID'].notna().sum():,}")
        st.dataframe(result.head(20), use_container_width=True)
        output = to_excel_bytes(result, "Processed Transactions")
        base = st.session_state.get("extract_source_name", "transactions")
        safe_base = re.sub(r"[^A-Za-z0-9_-]+", "_", base.rsplit(".", 1)[0]).strip("_") or "transactions"
        st.download_button(
            "⬇ Download processed Excel",
            data=output,
            file_name=f"{safe_base}_processed.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )


def page_comparison():
    hero("File Comparison & Reconciliation", "Compare two files and separate matching from unmatched records.")
    st.write(
        "Upload both files, then select the column in each file that contains "
        "the values you want to match. Matching is based on trimmed text values."
    )
    col1, col2 = st.columns(2)
    with col1:
        upload1 = st.file_uploader(
            "File 1 — source records",
            type=["csv", "xlsx", "xls"],
            key="compare_upload1",
        )
    with col2:
        upload2 = st.file_uploader(
            "File 2 — comparison records",
            type=["csv", "xlsx", "xls"],
            key="compare_upload2",
        )

    if upload1 is None or upload2 is None:
        st.caption("Upload both files to choose matching columns.")
        return

    try:
        df1 = read_uploaded_file(upload1)
        df2 = read_uploaded_file(upload2)
    except Exception as exc:
        st.error(f"Could not read one of the files: {exc}")
        return

    if df1.empty or df2.empty:
        st.warning("One of the uploaded files has no data rows.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**File 1:** `{upload1.name}`")
        st.caption(f"{len(df1):,} rows · {len(df1.columns):,} columns")
        st.dataframe(df1.head(5), use_container_width=True)
    with c2:
        st.markdown(f"**File 2:** `{upload2.name}`")
        st.caption(f"{len(df2):,} rows · {len(df2.columns):,} columns")
        st.dataframe(df2.head(5), use_container_width=True)

    if len(df1.columns) == 0 or len(df2.columns) == 0:
        st.error("Both files must contain at least one column.")
        return

    st.subheader("Choose matching columns")
    m1, m2 = st.columns(2)
    with m1:
        match1 = st.selectbox("Column from File 1", options=list(df1.columns), key="match_column_1")
    with m2:
        match2 = st.selectbox("Column from File 2", options=list(df2.columns), key="match_column_2")

    st.caption(
        "Rows with blank matching values are treated as unmatched. If a value occurs "
        "more than once, all matching combinations may appear in the matched report."
    )

    if st.button("Compare files", type="primary", use_container_width=True):
        try:
            left = df1.copy()
            right = df2.copy()
            left[match1] = left[match1].astype("string").str.strip()
            right[match2] = right[match2].astype("string").str.strip()

            valid_left = left[match1].notna() & left[match1].ne("")
            valid_right = right[match2].notna() & right[match2].ne("")
            values2 = set(right.loc[valid_right, match2].tolist())
            values1 = set(left.loc[valid_left, match1].tolist())

            unmatched1 = left[~valid_left | ~left[match1].isin(values2)].copy()
            unmatched2 = right[~valid_right | ~right[match2].isin(values1)].copy()

            # Use non-empty keys for merging so blank cells cannot match each other.
            matched = pd.merge(
                left.loc[valid_left],
                right.loc[valid_right],
                left_on=match1,
                right_on=match2,
                how="inner",
                suffixes=("_file1", "_file2"),
            )

            st.session_state["comparison_result"] = {
                "matched": matched,
                "unmatched1": unmatched1,
                "unmatched2": unmatched2,
                "file1": upload1.name,
                "file2": upload2.name,
                "match1": str(match1),
                "match2": str(match2),
            }
        except Exception as exc:
            st.error(f"Comparison failed: {exc}")
            return

    results = st.session_state.get("comparison_result")
    if results is None:
        return

    matched = results["matched"]
    unmatched1 = results["unmatched1"]
    unmatched2 = results["unmatched2"]
    st.divider()
    st.subheader("Comparison summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Matched rows", f"{len(matched):,}")
    c2.metric("Unmatched in File 1", f"{len(unmatched1):,}")
    c3.metric("Unmatched in File 2", f"{len(unmatched2):,}")

    tab1, tab2, tab3 = st.tabs(["Matched", "Unmatched — File 1", "Unmatched — File 2"])
    with tab1:
        st.dataframe(matched.head(100), use_container_width=True)
    with tab2:
        st.dataframe(unmatched1.head(100), use_container_width=True)
    with tab3:
        st.dataframe(unmatched2.head(100), use_container_width=True)

    st.subheader("Download reports")
    st.download_button(
        "⬇ Download matched rows (CSV)",
        data=to_csv_bytes(matched),
        file_name="matched_rows.csv",
        mime="text/csv",
        use_container_width=True,
    )
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "⬇ Download unmatched File 1 (CSV)",
            data=to_csv_bytes(unmatched1),
            file_name="unmatched_file1.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "⬇ Download unmatched File 2 (CSV)",
            data=to_csv_bytes(unmatched2),
            file_name="unmatched_file2.csv",
            mime="text/csv",
            use_container_width=True,
        )

    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("matched_rows.csv", to_csv_bytes(matched))
        archive.writestr("unmatched_file1.csv", to_csv_bytes(unmatched1))
        archive.writestr("unmatched_file2.csv", to_csv_bytes(unmatched2))
    st.download_button(
        "⬇ Download all three reports (ZIP)",
        data=bundle.getvalue(),
        file_name="reconciliation_reports.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True,
    )


if "page" not in st.session_state:
    st.session_state["page"] = "Home"

with st.sidebar:
    st.markdown("## 📊 Data Processing Hub")
    st.caption("Transaction utilities")
    st.divider()
    pages = ["Home", "Transaction Detail Extractor", "File Comparison & Reconciliation"]
    selected_page = st.radio(
        "NAVIGATION",
        pages,
        index=pages.index(st.session_state["page"]) if st.session_state["page"] in pages else 0,
    )
    st.session_state["page"] = selected_page
    st.divider()
    st.caption("CSV · Excel · Reconciliation")

if st.session_state["page"] == "Home":
    page_home()
elif st.session_state["page"] == "Transaction Detail Extractor":
    page_extractor()
else:
    page_comparison()

st.divider()
st.caption("Data Processing Hub · Review output files before using them for financial reconciliation.")
