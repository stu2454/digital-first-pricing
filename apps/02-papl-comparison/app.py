"""
PAPL Digital First - App 2: PAPL Comparison Tool (Comprehensive Enhanced Version)

Semantic comparison of PAPL .docx documents with AWS S3 integration
Enhanced with location tracking, detailed documentation, user feedback, and
structural anomaly detection for safer price comparisons.
"""

import streamlit as st
import sys
import os
from datetime import datetime
from io import BytesIO
import pandas as pd
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add shared modules to path
if os.path.exists("../../shared"):
    sys.path.append("../../shared")
elif os.path.exists("/app/shared"):
    sys.path.append("/app/shared")

from aws_storage import S3Storage
from papl_parser import PAPLParser
from semantic_comparer import SemanticComparer

# Load environment variables
from dotenv import load_dotenv

load_dotenv("../../.env")


# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="PAPL Digital First - Document Comparison",
    page_icon="📊",
    layout="wide",
)

# NDIA Brand Colors
NDIA_BLUE = "#003087"
NDIA_ACCENT = "#00B5E2"

# Custom CSS
st.markdown(
    f"""
<style>
    .main-header {{
        background: linear-gradient(135deg, {NDIA_BLUE} 0%, {NDIA_ACCENT} 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}

    .stTabs [data-baseweb="tab"] {{
        height: 60px;
        padding: 0px 24px;
        background-color: #f0f2f6;
        border-radius: 8px 8px 0px 0px;
        font-size: 18px;
        font-weight: 600;
        color: {NDIA_BLUE};
    }}

    .stTabs [aria-selected="true"] {{
        background-color: {NDIA_BLUE};
        color: white;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        background-color: {NDIA_ACCENT};
        color: white;
    }}

    .nav-helper {{
        background-color: #e7f3ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid {NDIA_BLUE};
        margin-bottom: 20px;
        font-size: 16px;
    }}
</style>
""",
    unsafe_allow_html=True,
)


# Helper function to format locations
def format_location(location: dict) -> str:
    if not location:
        return ""
    parts = []
    if "table_number" in location:
        parts.append(f"Table {location['table_number']}")
    if "row_number" in location:
        parts.append(f"Row {location['row_number']}")
    if "paragraph_number" in location:
        parts.append(f"Para {location['paragraph_number']}")
    return ", ".join(parts) if parts else ""


# AWS INITIALISATION
try:
    storage = S3Storage()
    storage_initialized = storage.ensure_bucket_exists()
    storage_error = None
except Exception as e:
    storage = None
    storage_initialized = False
    storage_error = str(e)


# SESSION STATE
if "comparison_complete" not in st.session_state:
    st.session_state.comparison_complete = False
if "old_parsed" not in st.session_state:
    st.session_state.old_parsed = None
if "new_parsed" not in st.session_state:
    st.session_state.new_parsed = None
if "comparison_results" not in st.session_state:
    st.session_state.comparison_results = None
if "old_s3_key" not in st.session_state:
    st.session_state.old_s3_key = None
if "new_s3_key" not in st.session_state:
    st.session_state.new_s3_key = None


# HEADER
st.markdown(
    """
<div class="main-header">
    <h1>📊 PAPL Digital First</h1>
    <h3>Semantic Document Comparison Tool</h3>
    <p>Transforming Static Documents into Structured, Intelligent Data</p>
</div>
""",
    unsafe_allow_html=True,
)


# NAVIGATION HELPER
st.markdown(
    """
<div class="nav-helper">
    <strong>👋 Welcome!</strong> Use the tabs below to navigate:
    <strong>Upload & Compare</strong> → <strong>Results</strong> → <strong>Export</strong> | 
    <strong>About</strong> for methodology | <strong>Feedback</strong> to help us improve
</div>
""",
    unsafe_allow_html=True,
)


# Introduction Section
with st.container():
    st.markdown("## 🎯 What This Tool Does")

    st.info(
        """
    The PAPL Comparison Tool automatically identifies and categorizes changes between two versions of PAPL documents. 
    Instead of manually comparing 100+ page Word documents, this tool:
    """
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**📊 Parses documents semantically**")
        st.caption("Understands tables, rules, and guidance separately")

        st.markdown("**🔍 Compares intelligently**")
        st.caption("Detects pricing changes, rule modifications, and content updates")

        st.markdown("**📍 Tracks locations precisely**")
        st.caption("Shows exact table numbers, row numbers, and paragraph numbers")

    with col2:
        st.markdown("**🔄 Provides context**")
        st.caption("Displays surrounding content to understand change impact")

        st.markdown("**📤 Generates reports**")
        st.caption("Exports structured data for stakeholder communications")

    st.markdown("### 💡 Why This Matters")

    st.warning(
        """
    PAPL documents change quarterly, affecting thousands of providers and participants. Manual comparison is:
    
    - ❌ **Time-consuming** (2-4 hours per comparison)
    - ❌ **Error-prone** (easy to miss changes in 100+ pages)
    - ❌ **Unstructured** (results in Word comments, not data)
    - ❌ **Not auditable** (no systematic record of what changed)
    """
    )

    st.success(
        """
    **This tool addresses these inefficiencies systematically:**
    
    - ⏱️ **Time Savings**: 85-95% reduction in comparison time (hours → minutes)
    - ✅ **Error Reduction**: Automated detection vs. manual review
    - 📊 **Structured Output**: Machine-readable data for downstream systems
    - 📝 **Audit Trail**: Complete, versioned record of all changes
    - 🎯 **Scalable Impact**: Benefits multiply across thousands of stakeholders
    
    **Pilot Evaluation:** This tool includes built-in measurement to quantify actual time savings 
    and value delivered during pilot deployment.
    """
    )


# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    # AWS Status
    st.markdown("#### AWS Connection")
    if storage_initialized:
        st.success("✅ AWS S3 Connected")
        st.caption(f"Bucket: `{storage.bucket_name}`")
    else:
        st.error("❌ AWS Connection Failed")
        if storage_error:
            st.caption(f"Error: {storage_error[:100]}")

    st.markdown("---")

    # Comparison Options
    st.markdown("#### Comparison Options")

    compare_pricing = st.checkbox(
        "Compare Pricing Data",
        value=True,
        help="Detect changes in support item prices",
    )
    compare_rules = st.checkbox(
        "Compare Business Rules",
        value=True,
        help="Identify new, removed, or modified claiming rules",
    )
    compare_guidance = st.checkbox(
        "Compare Guidance Text",
        value=True,
        help="Track updates to policy guidance sections",
    )
    compare_tables = st.checkbox(
        "Compare Table Structures",
        value=True,
        help="Detect changes in table dimensions",
    )

    upload_to_s3 = st.checkbox(
        "Upload to AWS S3",
        value=storage_initialized,
        help="Store documents and results in S3 for AI Assistant",
        disabled=not storage_initialized,
    )

    st.markdown("---")

    # Quick Guide
    st.markdown("#### 🚀 Quick Start")
    st.info(
        """
    1. Upload old & new PAPL .docx files
    2. Click "Parse and Compare"
    3. View results in Results tab
    4. Export reports as needed
    5. Provide feedback to improve!
    """
    )

    st.markdown("---")
    st.caption("Markets Delivery | NDIA")


# Main Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📤 Upload & Compare", "📊 Results", "💾 Export & Storage", "📖 About", "💬 Feedback"]
)


# ========================================
# TAB 1: Upload & Compare
# ========================================
with tab1:
    st.markdown("## Upload PAPL Documents")

    st.info(
        """
    **📝 Tips for Best Results:**
    
    - Use clean .docx files (not PDFs converted to Word)
    - Ensure both documents follow similar structure
    - Upload files in chronological order (older first, newer second)
    - File names help tracking - use meaningful names like "PAPL_2024Q1.docx"
    """
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 Version 1 (Older)")
        old_file = st.file_uploader(
            "Upload older PAPL version",
            type=["docx"],
            key="old_file",
            help="Upload the older/baseline PAPL document",
        )

        if old_file:
            st.success(f"✓ Loaded: {old_file.name}")
            st.caption(f"Size: {old_file.size / 1024:.1f} KB")

    with col2:
        st.markdown("### 📄 Version 2 (Newer)")
        new_file = st.file_uploader(
            "Upload newer PAPL version",
            type=["docx"],
            key="new_file",
            help="Upload the newer/updated PAPL document",
        )

        if new_file:
            st.success(f"✓ Loaded: {new_file.name}")
            st.caption(f"Size: {new_file.size / 1024:.1f} KB")

    st.markdown("---")

    # Compare button
    if old_file and new_file:
        st.markdown("### 🔍 Ready to Compare")
        st.info("Both documents loaded. Click below to begin semantic comparison.")

        if st.button("🔍 Parse and Compare Documents", type="primary", use_container_width=True):
            with st.spinner("🔄 Processing documents..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                try:
                    # Initialize components
                    parser = PAPLParser()
                    comparer = SemanticComparer()

                    # Save uploaded files to temporary location for PDF extraction
                    import tempfile
                    import shutil

                    # Create temp directory
                    temp_dir = tempfile.mkdtemp()

                    # Save old file
                    old_temp_path = os.path.join(temp_dir, old_file.name)
                    with open(old_temp_path, "wb") as f:
                        f.write(old_file.getvalue())

                    # Save new file
                    new_temp_path = os.path.join(temp_dir, new_file.name)
                    with open(new_temp_path, "wb") as f:
                        f.write(new_file.getvalue())

                    # Step 1: Upload to S3 (if enabled)
                    if upload_to_s3 and storage_initialized:
                        status_text.text("📤 Uploading documents to AWS S3...")
                        progress_bar.progress(10)

                        # Reset file pointers
                        old_file.seek(0)
                        new_file.seek(0)

                        st.session_state.old_s3_key = storage.upload_source_document(
                            file_data=old_file.read(),
                            document_type="papl",
                            filename=old_file.name,
                        )
                        st.session_state.new_s3_key = storage.upload_source_document(
                            file_data=new_file.read(),
                            document_type="papl",
                            filename=new_file.name,
                        )

                    # Step 2: Parse old document (using temp file path for PDF extraction)
                    status_text.text("📄 Parsing old document...")
                    progress_bar.progress(30)
                    st.session_state.old_parsed = parser.parse(
                        old_temp_path, extract_page_numbers=True
                    )

                    # Step 3: Parse new document (using temp file path for PDF extraction)
                    status_text.text("📄 Parsing new document...")
                    progress_bar.progress(60)
                    st.session_state.new_parsed = parser.parse(
                        new_temp_path, extract_page_numbers=True
                    )

                    # Step 4: Compare
                    status_text.text("🔍 Running semantic comparison...")
                    progress_bar.progress(80)
                    results = comparer.compare(
                        st.session_state.old_parsed,
                        st.session_state.new_parsed,
                    )

                    # Post-process price changes to suppress anomalous tables
                    old_anom = st.session_state.old_parsed.get("anomalous_tables", []) or []
                    new_anom = st.session_state.new_parsed.get("anomalous_tables", []) or []

                    price_changes = results.get("price_changes", {})
                    changes_list = price_changes.get("changes", [])

                    filtered_changes = []
                    suppressed_count = 0
                    inc_count = 0
                    dec_count = 0

                    for change in changes_list:
                        old_loc = change.get("old_location", {}) or {}
                        new_loc = change.get("new_location", {}) or {}

                        old_table = old_loc.get("table", None)
                        new_table = new_loc.get("table", None)

                        is_anomalous = False
                        if isinstance(old_table, int) and old_table in old_anom:
                            is_anomalous = True
                        if isinstance(new_table, int) and new_table in new_anom:
                            is_anomalous = True

                        if is_anomalous:
                            suppressed_count += 1
                            continue

                        filtered_changes.append(change)

                        diff = change.get("difference", 0) or 0
                        try:
                            diff_val = float(diff)
                        except Exception:
                            diff_val = 0.0
                        if diff_val > 0:
                            inc_count += 1
                        elif diff_val < 0:
                            dec_count += 1

                    price_changes["changes"] = filtered_changes
                    price_changes["count"] = len(filtered_changes)

                    summary = price_changes.get("summary", {}) or {}
                    summary["total_changes"] = len(filtered_changes)
                    summary["increases"] = inc_count
                    summary["decreases"] = dec_count
                    summary["suppressed_due_to_anomalous_tables"] = suppressed_count
                    price_changes["summary"] = summary
                    results["price_changes"] = price_changes

                    st.session_state.comparison_results = results

                    # Cleanup temp files
                    shutil.rmtree(temp_dir)

                    progress_bar.progress(100)
                    status_text.text("✅ Comparison complete!")

                    st.session_state.comparison_complete = True
                    st.success("✅ Comparison complete! View results in the 'Results' tab.")
                    st.balloons()

                    # Surface anomalous table information immediately
                    old_anom = st.session_state.old_parsed.get("anomalous_tables", []) or []
                    new_anom = st.session_state.new_parsed.get("anomalous_tables", []) or []
                    if old_anom or new_anom:
                        st.warning(
                            f"⚠️ Some tables were flagged as structurally anomalous and "
                            f"excluded from automated price comparison.\n\n"
                            f"- OLD document anomalous tables: {old_anom}\n"
                            f"- NEW document anomalous tables: {new_anom}\n\n"
                            "This avoids misleading % changes where table structures "
                            "do not align (e.g. state-grouped vs national/remote/very remote)."
                        )

                except Exception as e:
                    # Cleanup temp files on error
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception:
                        pass

                    st.error(f"❌ Error during comparison: {str(e)}")
                    st.exception(e)
                    progress_bar.empty()
                    status_text.empty()
    else:
        st.info("👆 Upload both documents to begin comparison")


# ========================================
# TAB 2: Results
# ========================================
with tab2:
    st.markdown("## Comparison Results")

    if not st.session_state.comparison_complete:
        st.info("👈 Complete a comparison first to view results")
    else:
        results = st.session_state.comparison_results

        # Show anomalous table warning at top of Results
        old_anom = (st.session_state.old_parsed or {}).get("anomalous_tables", []) or []
        new_anom = (st.session_state.new_parsed or {}).get("anomalous_tables", []) or []
        if old_anom or new_anom:
            st.warning(
                f"⚠️ The following tables were flagged as structurally anomalous and "
                f"were excluded from automated price comparison:\n\n"
                f"- OLD document anomalous tables: {old_anom}\n"
                f"- NEW document anomalous tables: {new_anom}\n\n"
                "Price deltas from these tables have been suppressed to avoid "
                "misinterpretation when column structures differ."
            )

        # Summary metrics
        st.markdown("### 📈 Summary Overview")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Pricing Changes",
                results["price_changes"]["count"],
                delta=(
                    f"↑{results['price_changes']['summary'].get('increases', 0)} "
                    f"↓{results['price_changes']['summary'].get('decreases', 0)}"
                ),
            )

        with col2:
            st.metric(
                "Rule Changes",
                results["summary"]["total_rule_changes"],
                delta=f"+{results['summary']['rules_added']} -{results['summary']['rules_removed']}",
            )

        with col3:
            st.metric(
                "Guidance Changes",
                results["summary"]["sections_modified"],
                delta=(
                    f"+{results['summary']['guidance_added']} "
                    f"-{results['summary']['guidance_removed']}"
                ),
            )

        with col4:
            st.metric(
                "Table Changes",
                results["summary"]["tables_modified"],
                delta=(
                    f"+{results['summary']['tables_added']} "
                    f"-{results['summary']['tables_removed']}"
                ),
            )

        st.markdown("---")

        # ------------------------------
        # PRICING CHANGES (SUMMARY + LIST)
        # ------------------------------
        if compare_pricing:
            with st.expander("💰 Pricing Changes", expanded=True):
                pricing = results["price_changes"]
                suppressed_count = pricing["summary"].get(
                    "suppressed_due_to_anomalous_tables", 0
                )

                st.markdown(
                    f"""
                **Summary:**
                - Total Price Changes (after filtering anomalies): {pricing['summary']['total_changes']}
                - Price Increases: {pricing['summary']['increases']}
                - Price Decreases: {pricing['summary']['decreases']}
                - Prices Changed (count): {pricing['count']}
                - Changes suppressed due to anomalous tables: {suppressed_count}
                """
                )

                # Show price changes - flat list structure
                st.markdown("#### 📈 Recent Price Changes")

                changes_list = pricing.get("changes", [])
                if changes_list:
                    for change in changes_list[:20]:
                        item_num = change.get("item_number", "Unknown")
                        old_price = change.get("old_price", 0)
                        new_price = change.get("new_price", 0)
                        diff = change.get("difference", 0)
                        pct = change.get("percent_change", 0)

                        # Get page and table locations
                        old_loc = change.get("old_location", {}) or {}
                        new_loc = change.get("new_location", {}) or {}

                        old_page = old_loc.get("page", 0)
                        new_page = new_loc.get("page", 0)
                        old_table = old_loc.get("table", "?")
                        new_table = new_loc.get("table", "?")

                        if old_page > 0 and new_page > 0:
                            old_loc_str = f"Table {old_table} (Page {old_page})"
                            new_loc_str = f"Table {new_table} (Page {new_page})"
                        elif old_page > 0:
                            old_loc_str = f"Table {old_table} (Page {old_page})"
                            new_loc_str = f"Table {new_table}"
                        elif new_page > 0:
                            old_loc_str = f"Table {old_table}"
                            new_loc_str = f"Table {new_table} (Page {new_page})"
                        else:
                            old_loc_str = f"Table {old_table}"
                            new_loc_str = f"Table {new_table}"

                        if diff > 0:
                            st.markdown(
                                f"🔺 **{item_num}**: ${old_price:.2f} → ${new_price:.2f} "
                                f"(+${diff:.2f}, +{pct:.1f}%)"
                            )
                        else:
                            st.markdown(
                                f"🔻 **{item_num}**: ${old_price:.2f} → ${new_price:.2f} "
                                f"(${diff:.2f}, {pct:.1f}%)"
                            )

                        if old_page > 0 or new_page > 0:
                            st.markdown(
                                f"&nbsp;&nbsp;&nbsp;&nbsp;📄 OLD: {old_loc_str} | NEW: {new_loc_str}"
                            )

                    if len(changes_list) > 20:
                        st.info(f"Showing 20 of {len(changes_list)} total price changes")
                else:
                    st.info("No price changes to display")

        # =============================================================================
        # PRICE CHANGE ANALYSIS (HISTOGRAM + DIAGNOSTICS)
        # =============================================================================
        if st.session_state.old_parsed is not None and st.session_state.new_parsed is not None:
            with st.expander("🔍 Price Change Analysis", expanded=False):
                st.markdown("### 📊 Price Change Summary")
                price_data = results.get("price_changes", {})
                total_count = price_data.get("count", 0)
                st.write(f"**Total Price Changes Found (after anomaly filtering):** {total_count}")

                if total_count > 0:
                    st.success("✅ Price changes are being detected!")
                    changes = price_data.get("changes", [])

                    # Quick textual sample
                    st.write("**First 3 changes:**")
                    for change in changes[:3]:
                        st.write(
                            f"  - Item {change.get('item_number')}: "
                            f"${change.get('old_price')} → ${change.get('new_price')}"
                        )

                    st.markdown("### 📈 Distribution of Percentage Price Changes")

                    import matplotlib.pyplot as plt

                    df_changes = pd.DataFrame(changes)
                    df_changes["percent_change"] = pd.to_numeric(
                        df_changes.get("percent_change", None),
                        errors="coerce",
                    )
                    valid_pct = df_changes["percent_change"].dropna()

                    if valid_pct.empty:
                        st.info("No valid percentage change data available to visualise.")
                    else:
                        # Filter slider for % change
                        min_pct = float(valid_pct.min())
                        max_pct = float(valid_pct.max())

                        st.markdown("#### 🔎 Filter by Percentage Change Range")
                        pct_min, pct_max = st.slider(
                            "Select % change window",
                            min_value=min_pct,
                            max_value=max_pct,
                            value=(min_pct, max_pct),
                            step=0.1,
                            help="Filter items to a specific price-change range",
                        )

                        filtered_pct = valid_pct[
                            (valid_pct >= pct_min) & (valid_pct <= pct_max)
                        ]

                        # Bin slider
                        st.markdown("#### 🧮 Histogram Resolution")
                        num_bins = st.slider(
                            "Number of histogram bins",
                            min_value=10,
                            max_value=60,
                            value=30,
                            step=5,
                            help="Use more bins for higher detail; fewer for a clean overview",
                        )

                        # Histogram
                        fig, ax = plt.subplots(figsize=(8, 4))
                        ax.hist(filtered_pct, bins=num_bins, edgecolor="black")
                        ax.set_title("Histogram of Percentage Price Changes (Filtered)")
                        ax.set_xlabel("Percentage Change (%)")
                        ax.set_ylabel("Number of Items")

                        median_pc = filtered_pct.median()
                        ax.axvline(median_pc, linestyle="dashed", linewidth=1.2)
                        ax.text(
                            median_pc,
                            ax.get_ylim()[1] * 0.9,
                            f"Median: {median_pc:.1f}%",
                        )

                        st.pyplot(fig)

                        # Summary
                        st.markdown("#### 🧾 Filter Summary")
                        st.write(f"Items within selected range: **{len(filtered_pct)}**")
                        st.write(f"Median % change: **{median_pc:.2f}%**")

                    # Simple search for price changes
                    st.markdown("### 🔍 Search by Support Item Number")

                    search_query = st.text_input(
                        "Enter support item number",
                        placeholder="e.g., 04_049_0104_1_1",
                    )

                    if search_query:
                        search_query_lower = search_query.lower()

                        matched = [
                            c
                            for c in changes
                            if search_query_lower in str(c.get("item_number", "")).lower()
                        ]

                        if not matched:
                            st.info("No price changes found for that support item number.")
                        else:
                            # Group by item_number
                            grouped = {}
                            for c in matched:
                                item = c.get("item_number", "Unknown")
                                if item not in grouped:
                                    grouped[item] = []
                                grouped[item].append(c)

                            # Render each group as a neat table
                            for item_num, rows in grouped.items():
                                desc = rows[0].get("item_description", "")

                                st.markdown(f"### **{item_num}**: {desc}")

                                display_rows = []
                                for r in rows:
                                    loc = r.get("location_label", r.get("location", ""))
                                    display_rows.append(
                                        {
                                            "Location": loc,
                                            "Old": f"${r.get('old_price', 0):,.2f}",
                                            "New": f"${r.get('new_price', 0):,.2f}",
                                            "Change": f"{r.get('difference', 0):+,.2f}",
                                            "(%)": f"{r.get('percent_change', 0):+,.1f}%",
                                        }
                                    )

                                df = pd.DataFrame(display_rows)
                                st.table(df)
                    else:
                        st.caption(
                            "Enter a support item number (e.g., 04_049_0104_1_1)"
                        )

                else:
                    # No price changes: diagnostics path
                    st.error("❌ No price changes detected - Let's investigate why...")

                    st.markdown("---")
                    st.markdown("### 🔍 Detailed Investigation")

                    # Check table counts
                    st.markdown("#### 1. Table Counts")
                    old_tables = st.session_state.old_parsed.get("raw_tables", [])
                    new_tables = st.session_state.new_parsed.get("raw_tables", [])
                    st.write(f"- OLD document tables: **{len(old_tables)}**")
                    st.write(f"- NEW document tables: **{len(new_tables)}**")

                    # Check pricing table detection
                    st.markdown("#### 2. Pricing Table Detection")
                    st.write("Checking which tables are identified as pricing tables...")

                    parser = PAPLParser()

                    # OLD tables
                    st.markdown("**OLD Document Tables:**")
                    for i in range(min(10, len(old_tables))):
                        table = old_tables[i]
                        is_pricing, confidence = parser._is_pricing_table(table)

                        headers = []
                        if table.get("data") and len(table["data"]) > 0:
                            headers = table["data"][0][:5]

                        icon = "✅" if is_pricing else "❌"
                        st.markdown(
                            f"**Table {i}:** {icon} "
                            f"{'PRICING' if is_pricing else 'NOT PRICING'} "
                            f"(confidence: {confidence}/100)"
                        )
                        st.text(f"  Headers: {headers}")

                        prices = parser._extract_prices_from_table(table)
                        if prices:
                            st.text(f"  Found {len(prices)} prices")

                    st.markdown("---")

                    # NEW tables
                    st.markdown("**NEW Document Tables:**")
                    for i in range(min(10, len(new_tables))):
                        table = new_tables[i]
                        is_pricing, confidence = parser._is_pricing_table(table)

                        headers = []
                        if table.get("data") and len(table["data"]) > 0:
                            headers = table["data"][0][:5]

                        icon = "✅" if is_pricing else "❌"
                        st.markdown(
                            f"**Table {i}:** {icon} "
                            f"{'PRICING' if is_pricing else 'NOT PRICING'} "
                            f"(confidence: {confidence}/100)"
                        )
                        st.text(f"  Headers: {headers}")

                        prices = parser._extract_prices_from_table(table)
                        if prices:
                            st.text(f"  Found {len(prices)} prices")

                    st.markdown("---")

                    # Matching pairs
                    st.markdown("#### 3. Matching Table Pairs")
                    st.write("Checking which table pairs are being compared...")

                    max_pairs = min(len(old_tables), len(new_tables))
                    pricing_pairs = []

                    for i in range(max_pairs):
                        old_is_pricing, old_conf = parser._is_pricing_table(old_tables[i])
                        new_is_pricing, new_conf = parser._is_pricing_table(new_tables[i])

                        if old_is_pricing and new_is_pricing:
                            pricing_pairs.append(i)
                            st.success(
                                f"✅ Table pair {i}: BOTH are pricing tables "
                                f"(old: {old_conf}, new: {new_conf})"
                            )

                            changes = parser._compare_table_prices(
                                old_tables[i], new_tables[i]
                            )
                            st.write(
                                f"   → Price changes found: **{len(changes)}**"
                            )

                            if len(changes) > 0:
                                st.write(f"   → Sample change: {changes[0]}")

                    if len(pricing_pairs) == 0:
                        st.error("❌ NO table pairs are both identified as pricing tables!")
                        st.write("**This is why no price changes are detected.**")

                        st.markdown("#### 💡 Possible Solutions:")
                        st.markdown(
                            """
                        1. **Lower the confidence threshold** (currently 60) in `papl_parser.py`
                        2. **Add more header keywords** to recognize pricing tables
                        3. **Check table headers** - do they contain "Price", "Rate", "Cost", "Fee"?
                        4. **Manually specify** which tables are pricing tables
                        """
                        )
                    else:
                        st.success(
                            f"✅ Found {len(pricing_pairs)} pricing table pairs"
                        )
                        st.write(f"Table indices: {pricing_pairs}")

                    st.markdown("---")

                    st.markdown("#### 📋 Information Needed")
                    st.info(
                        """
                    To fix this, we need to know:
                    
                    1. **What headers do your pricing tables have?**
                       (Look at the headers displayed above)
                       
                    2. **What is the confidence score for your pricing tables?**
                       (Look at the confidence numbers above)
                       
                    3. **Do the headers contain words like:** Price, Rate, Cost, Fee, Amount?
                       
                    4. **What do prices look like in the cells?**
                       (e.g., $50.00, 50.00, $50, etc.)
                    """
                    )

        # ------------------------------
        # BUSINESS RULE CHANGES
        # ------------------------------
        with st.expander("📋 Business Rule Changes", expanded=True):
            rules = results["business_rule_changes"]

            st.markdown(
                f"""
            **Summary:**
            - Rules Added: {results['summary']['rules_added']}
            - Rules Removed: {results['summary']['rules_removed']}
            - Rules Modified: {results['summary']['rules_modified']}
            - Total Rule Changes: {len(rules)}
            """
            )

            for detail in rules[:15]:
                loc_display = format_location(detail.get("location", {}))
                loc_str = f" ({loc_display})" if loc_display else ""

                if detail["type"] == "rule_added":
                    st.success(
                        f"""
**➕ Rule Added{loc_str}**

{detail['text']}

*Type: {detail['rule_type']} | Priority: {detail['priority']}*
"""
                    )
                elif detail["type"] == "rule_removed":
                    st.error(
                        f"""
**➖ Rule Removed{loc_str}**

{detail['text']}

*Type: {detail['rule_type']} | Priority: {detail['priority']}*
"""
                    )
                elif detail["type"] == "rule_modified":
                    st.warning(
                        f"""
**✏️ Rule Modified** (Similarity: {detail['similarity']})

**Old:** {detail['old_text']}

**New:** {detail['new_text']}
"""
                    )

        # ------------------------------
        # GUIDANCE CHANGES
        # ------------------------------
        if compare_guidance:
            with st.expander("📖 Guidance Changes", expanded=True):
                guidance = results.get("guidance_changes", [])

                st.markdown(
                    f"""
                **Summary:**
                - Guidance Added: {results['summary']['guidance_added']}
                - Guidance Removed: {results['summary']['guidance_removed']}
                - Guidance Modified: {results['summary']['guidance_modified']}
                - Total Changes: {len(guidance)}
                """
                )

                for detail in guidance[:10]:
                    if detail["type"] == "added":
                        guidance_item = detail.get("guidance", {})
                        section = guidance_item.get("section", "Unknown section")
                        text = guidance_item.get("text", "")
                        preview = (
                            text[:200] + "..." if len(text) > 200 else text
                        )

                        st.success(
                            f"""
**➕ Guidance Added:** {section}

{preview}
"""
                        )
                    elif detail["type"] == "removed":
                        guidance_item = detail.get("guidance", {})
                        section = guidance_item.get("section", "Unknown section")
                        text = guidance_item.get("text", "")
                        preview = (
                            text[:200] + "..." if len(text) > 200 else text
                        )

                        st.error(
                            f"""
**➖ Guidance Removed:** {section}

{preview}
"""
                        )
                    elif detail["type"] == "modified":
                        old_item = detail.get("old_guidance", {})
                        new_item = detail.get("new_guidance", {})
                        section = old_item.get(
                            "section", new_item.get("section", "Unknown section")
                        )
                        similarity = detail.get("similarity", 0)

                        st.warning(
                            f"""
**✏️ Guidance Modified:** {section}

Similarity: {similarity}%

Old: {old_item.get('text', '')[:150]}...
New: {new_item.get('text', '')[:150]}...
"""
                        )

        # ------------------------------
        # TABLE STRUCTURE CHANGES
        # ------------------------------
        if compare_tables:
            with st.expander("📋 Table Structure Changes", expanded=True):
                tables = results.get("table_changes", {})

                st.markdown(
                    f"""
                **Summary:**
                - Tables Added: {results['summary']['tables_added']}
                - Tables Removed: {results['summary']['tables_removed']}
                - Tables Modified: {results['summary']['tables_modified']}
                """
                )

                tables_added_list = tables.get("tables_added", [])
                if tables_added_list:
                    st.info(
                        f"**➕ Tables Added:** {len(tables_added_list)} "
                        f"table(s) (indices: {', '.join(map(str, tables_added_list))})"
                    )

                tables_removed_list = tables.get("tables_removed", [])
                if tables_removed_list:
                    st.info(
                        f"**➖ Tables Removed:** {len(tables_removed_list)} "
                        f"table(s) (indices: {', '.join(map(str, tables_removed_list))})"
                    )

                for detail in tables.get("tables_modified", []):
                    old_rows, old_cols = detail["old_dimensions"]
                    new_rows, new_cols = detail["new_dimensions"]

                    row_diff = new_rows - old_rows
                    col_diff = new_cols - old_cols

                    st.warning(
                        f"""
**⚠️ Table {detail['table_index'] + 1} Structure Changed**

Rows: {old_rows} → {new_rows} ({'+' if row_diff > 0 else ''}{row_diff})

Columns: {old_cols} → {new_cols} ({'+' if col_diff > 0 else ''}{col_diff})
"""
                    )


# ========================================
# TAB 3: Export & Storage
# ========================================
with tab3:
    st.markdown("## Export & Storage")

    if not st.session_state.comparison_complete:
        st.info("👈 Complete a comparison first to export results")
    else:
        st.markdown("### 💾 AWS S3 Storage")

        if st.session_state.get("old_s3_key") and st.session_state.get("new_s3_key"):
            st.success("✅ Documents stored in AWS S3")

            col1, col2 = st.columns(2)
            with col1:
                st.code(st.session_state.old_s3_key, language="text")
            with col2:
                st.code(st.session_state.new_s3_key, language="text")

            st.info("💡 These documents are now available to the AI Assistant for querying")

        st.markdown("---")
        st.markdown("### 📥 Export Options")

        col1, col2, col3 = st.columns(3)

        # JSON export
        with col1:
            if st.button("📄 Export as JSON", use_container_width=True):
                json_data = json.dumps(
                    st.session_state.comparison_results, indent=2, default=str
                )
                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name=f"papl_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )

        # CSV export (flat price_changes list)
        with col2:
            if st.button("📊 Export as CSV", use_container_width=True):
                price_changes = (
                    st.session_state.comparison_results.get("price_changes", {}).get(
                        "changes", []
                    )
                )

                if price_changes:
                    df = pd.DataFrame(price_changes)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"price_changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )
                else:
                    st.warning("No pricing changes to export")

        # Markdown summary export
        with col3:
            if st.button("📝 Export as Markdown", use_container_width=True):
                results = st.session_state.comparison_results
                md_report = f"""# PAPL Comparison Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

### Pricing Changes
- Tables Modified: {results['summary']['tables_modified']}
- Tables Added: {results['summary']['tables_added']}
- Tables Removed: {results['summary']['tables_removed']}
- Prices Changed (after anomaly filtering): {results['price_changes']['count']}
- Changes suppressed due to anomalous tables: {results['price_changes']['summary'].get('suppressed_due_to_anomalous_tables', 0)}

### Business Rules
- Rules Added: {results['summary']['rules_added']}
- Rules Removed: {results['summary']['rules_removed']}
- Rules Modified: {results['summary']['rules_modified']}
- Total Rule Changes: {results['summary']['total_rule_changes']}
- Sections Added: {results['summary']['sections_added']}
- Sections Removed: {results['summary']['sections_removed']}
- Sections Modified: {results['summary']['sections_modified']}
- Guidance Changes: {results['summary']['total_guidance_changes']} total

### Tables
- Tables Added: {results['summary']['tables_added']}
- Tables Removed: {results['summary']['tables_removed']}

---

*Generated by PAPL Digital First - Semantic Comparison Tool*
*Enhanced with Location Tracking, Context Display, and Structural Anomaly Detection*
"""
                st.download_button(
                    label="Download Markdown",
                    data=md_report,
                    file_name=f"papl_comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                )


# ========================================
# TAB 4: About
# ========================================
with tab4:
    st.markdown("## 📖 About This Tool")

    # Development Story
    st.markdown("### 🔨 How This Tool Was Developed")
    st.markdown(
        """
    This tool is part of the **PAPL Digital First** initiative at NDIA Markets Delivery, led by Stuart Smith. 
    The project aims to transform PAPL documents from static PDF/Word files into structured, machine-readable data.
    
    **Development Approach:**
    - **Problem Identification**: Manual PAPL comparison was taking 2-4 hours and missing critical changes
    - **Proof of Concept**: Built initial parser to extract tables and text from .docx files
    - **Semantic Analysis**: Developed classification system to distinguish pricing, rules, and guidance
    - **Enhanced Features**: Added location tracking, context display, AWS integration, and anomaly detection
    - **User Feedback**: Iteratively improved based on real-world usage and stakeholder input
    
    **Technology Stack:**
    - **Python** with `python-docx` for document parsing
    - **Streamlit** for interactive web interface
    - **AWS S3** for document storage and AI Assistant integration
    - **Docker** for consistent deployment across environments
    
    **Key Innovation:**
    Unlike simple text comparison tools, this analyzes PAPL documents **semantically** - understanding that:
    - Tables contain pricing data that needs price-specific comparison
    - Paragraphs with "must/shall/required" contain business rules
    - Descriptive sections contain guidance that needs different analysis
    """
    )

    st.markdown("---")

    # How Rules Are Defined
    st.markdown("### 🎯 How the Tool Defines 'Business Rules'")
    st.markdown(
        """
    The tool uses **keyword-based classification** combined with **structural analysis** to identify business rules.
    
    #### Rule Identification Criteria:
    
    **1. Keyword Detection**  
    Paragraphs containing these words are flagged as potential rules:
    - **Mandatory language**: must, shall, required, mandatory, obligation
    - **Conditional language**: if, when, where, provided that
    - **Threshold language**: minimum, maximum, threshold, limit
    - **Process language**: claiming, quote, evidence, approval
    
    **2. Rule Classification**  
    Once identified, rules are categorized by type:
    - **Claiming Rules**: Rules about how to claim support items
    - **Quoting Rules**: Requirements for obtaining quotes
    - **Evidence Rules**: Documentation requirements
    - **Approval Rules**: Pre-approval or authorization requirements
    - **Requirements**: General mandatory requirements
    - **Permissions**: What providers may (but aren't required to) do
    
    **3. Priority Assessment**  
    Rules are assigned priority levels based on language strength:
    - **High Priority**: Contains "must", "shall", "required", "mandatory"
    - **Medium Priority**: Contains "should", "recommended", "expected"
    - **Low Priority**: All other rule-like content
    
    **4. Entity Extraction**  
    The tool extracts specific details from rules:
    - **Dollar amounts**: $15,000, $5.00, etc.
    - **Percentages**: 10%, 25%, etc.
    - **Time periods**: 30 days, 2 weeks, etc.
    - **Dates**: Specific calendar dates or deadlines
    
    #### Example Rule Classification:
    
    ```
    Text: "Providers must obtain quotes for supports valued at $15,000 or more."
    
    Classification:
    - Type: quoting_rule
    - Priority: high (contains "must")
    - Conditions: ["if support value is $15,000 or more"]
    - Entities: {"amounts": ["$15,000"]}
    ```
    
    #### What Is NOT Considered a Rule:
    - Descriptive guidance text without mandatory language
    - Examples and illustrations
    - Historical context or background information
    - Tables (these are parsed as pricing data)
    - Headings and section titles
    
    #### Limitations:
    The rule detection is **heuristic-based**, not AI-powered, so it may:
    - Miss rules phrased unusually (e.g., "it is necessary that...")
    - Flag guidance that looks rule-like but isn't mandatory
    - Have difficulty with complex nested conditional logic
    
    Future versions may incorporate NLP/AI for more sophisticated rule detection.
    """
    )

    st.markdown("---")

    # Technical Methodology
    st.markdown("### 🔬 Technical Methodology")

    with st.expander("📄 Document Parsing Process"):
        st.markdown(
            """
        **Step 1: Load Document**
        - Uses `python-docx` library to read .docx files
        - Extracts raw paragraphs and tables
        
        **Step 2: Classify Content**
        - **Tables**: Identified by document structure → parsed as pricing data
        - **Paragraphs**: Analyzed by keywords → classified as rules or guidance
        - **Headings**: Tracked for section structure and navigation
        
        **Step 3: Extract Metadata**
        - Table numbers, row numbers (1-indexed for humans)
        - Paragraph numbers (absolute position in document)
        - Section hierarchy (Heading 1, Heading 2, etc.)
        
        **Step 4: Structure Data**
        - Pricing data → JSON with tables, items, prices
        - Business rules → YAML with conditions, priorities
        - Guidance → Markdown with headings and content
        
        **Step 5: Add Location & Anomaly Tracking**
        - Every item gets a `location` dict with precise coordinates
        - Tables are inspected for structural anomalies (e.g. state-grouped columns)
        - Anomalous tables are flagged for human review and excluded from automated price comparisons
        """
        )

    with st.expander("🔍 Comparison Algorithm"):
        st.markdown(
            """
        **Pricing Comparison:**
        1. Extract all pricing items from both documents
        2. Classify and match pricing tables
        3. Flag tables with structural anomalies (e.g. state-grouped vs national)
        4. Identify added/removed/modified items where structures align
        5. Calculate price changes (absolute and percentage)
        6. Suppress price deltas originating from anomalous tables
        7. Add surrounding context (2 items before/after)
        
        **Rule Comparison:**
        1. Extract all business rules from both documents
        2. Create lookup tables by rule text
        3. Identify added/removed rules
        4. Use fuzzy matching (70% similarity) to find modified rules
        5. Preserve priority and type information
        
        **Guidance Comparison:**
        1. Group paragraphs by section headings
        2. Compare sections by heading name
        3. Identify added/removed/modified sections
        4. Track word count changes
        5. Detect paragraph-level changes within sections
        
        **Table Structure Comparison:**
        1. Compare table dimensions (rows × columns)
        2. Detect structural changes (dimensions changed)
        3. Detect content changes (cell values changed)
        4. Flag tables that moved position
        """
        )

    with st.expander("🎨 Why Semantic vs. Text Comparison?"):
        st.markdown(
            """
        **Traditional text comparison** (like Word's "Compare Documents"):
        - ❌ Shows every formatting change as a "difference"
        - ❌ Doesn't understand context (can't tell pricing from rules)
        - ❌ Can't quantify changes (number of price increases)
        - ❌ Produces unstructured output (marked-up document)
        
        **Semantic comparison** (this tool):
        - ✅ Ignores pure formatting changes
        - ✅ Understands document structure (pricing vs. rules vs. guidance)
        - ✅ Quantifies changes (e.g., number of price increases/decreases)
        - ✅ Produces structured data (JSON, CSV, reports)
        - ✅ Explicitly flags tables whose structures are unsafe to compare
        - ✅ Enables analytics (average price increase, high-priority rule changes)
        
        **Example:**
        If a price changes from **$75.00** to **$80.00** in a structurally consistent table:
        - Reported as: "+$5.00 (+6.7%)" with location and context
        
        If the underlying table structure has changed (e.g. state-grouped vs national):
        - The tool flags the table as anomalous
        - Suppresses misleading % deltas
        - Surfaces a warning for human review
        """
        )

    st.markdown("---")

    # Project Context
    st.markdown("### 🎯 Project Context: PAPL Digital First")
    st.markdown(
        """
    This tool is one component of a larger initiative to transform NDIA's pricing information:
    
    **Current State (Problem):**
    - PAPL as 104-page Word document (83 tables, 162 sections, 1,235 paragraphs)
    - Pricing "locked up" in PDFs/Word - can't be queried or validated
    - Significant hidden costs from manual navigation and errors
    - No systematic change management or version control
    
    **Digital First Vision:**
    - **JSON** for structured pricing data (machine-readable)
    - **YAML** for business rules (validatable logic)
    - **Markdown** for human-readable guidance
    - **API access** for third-party software vendors
    - **Automated validation** to prevent claiming errors
    
    **This Comparison Tool:**
    - Makes the transition manageable by tracking changes systematically
    - Builds stakeholder confidence through transparency
    - Provides evidence for the value of structured data
    - Creates an audit trail for compliance and governance
    - Explicitly surfaces weaknesses in the current artefact structures
    
    **Next Steps:**
    - Integrate with AI Assistant (RAG) for natural language queries
    - Add OpenSearch for semantic search across all versions
    - Implement automated stakeholder notifications
    - Build provider-facing API for real-time pricing data
    
    **Pilot Evaluation Framework:**
    This tool includes built-in measurement capabilities to quantify value during pilot deployment:
    - **Time tracking**: Feedback form captures actual time saved per comparison
    - **User experience**: Rating scales measure usability and accuracy
    - **Error detection**: Tracks missed changes and false positives
    - **Adoption metrics**: Usage patterns and repeat usage rates
    - **Value calculation**: Data to support business case for broader rollout
    
    The pilot will establish baseline metrics and demonstrate measurable benefits before 
    requesting additional investment for enterprise deployment.
    
    **Learn More:**
    - GitHub: `github.com/stu2454/digital-first-pricing-artefacts`
    - Contact: Stuart Smith, Markets Delivery, NDIA
    """
    )


# ========================================
# TAB 5: Feedback
# ========================================
with tab5:
    st.markdown("## 💬 Feedback & Suggestions")

    st.info(
        """
    **📊 Pilot Evaluation:** Your feedback is essential for measuring the value of this tool!
    
    This data will help us:
    - Quantify actual time savings vs. manual comparison
    - Calculate return on investment for broader deployment
    - Identify improvements for enterprise rollout
    - Build evidence-based business case for digital-first transformation
    
    Please provide honest feedback - both positive and critical insights are valuable.
    """
    )

    with st.expander("📝 Share Your Feedback", expanded=True):
        feedback_cols = st.columns([1, 1])

        with feedback_cols[0]:
            st.markdown("### Comparison Quality")
            comparison_quality = st.radio(
                "How accurate was the comparison?",
                options=[
                    "⭐⭐⭐⭐⭐ Excellent - Caught all changes",
                    "⭐⭐⭐⭐ Good - Caught most changes",
                    "⭐⭐⭐ OK - Missed some changes",
                    "⭐⭐ Poor - Missed many changes",
                    "⭐ Very Poor - Not useful",
                ],
                index=None,
                key="comparison_quality",
            )

            missing_changes = st.checkbox(
                "The tool missed important changes", key="missing_changes"
            )

            if missing_changes:
                st.text_area(
                    "What changes were missed?",
                    placeholder=(
                        "E.g., Price change in Table 5, new paragraph in Section 3..."
                    ),
                    key="missed_details",
                )

            false_positives = st.checkbox(
                "The tool flagged things that weren't really changes",
                key="false_positives",
            )

            if false_positives:
                st.text_area(
                    "What was incorrectly flagged?",
                    placeholder="E.g., Formatting-only changes, unchanged content...",
                    key="false_positive_details",
                )

        with feedback_cols[1]:
            st.markdown("### Ease of Use")
            ease_of_use = st.radio(
                "How easy was the tool to use?",
                options=[
                    "⭐⭐⭐⭐⭐ Very Easy",
                    "⭐⭐⭐⭐ Easy",
                    "⭐⭐⭐ Moderate",
                    "⭐⭐ Difficult",
                    "⭐ Very Difficult",
                ],
                index=None,
                key="ease_of_use",
            )

            usefulness = st.radio(
                "Would you use this tool again?",
                options=[
                    "Definitely - Very useful",
                    "Probably - Somewhat useful",
                    "Maybe - Neutral",
                    "Probably not - Not very useful",
                    "Definitely not - Not useful",
                ],
                index=None,
                key="usefulness",
            )

            st.markdown("---")

            st.markdown("### Time Savings (Pilot Evaluation)")

            manual_time = st.radio(
                "How long would this comparison take you manually?",
                options=[
                    "15-30 minutes",
                    "30-60 minutes",
                    "1-2 hours",
                    "2-4 hours",
                    "4+ hours",
                    "I wouldn't do it manually",
                ],
                index=None,
                key="manual_time",
            )

            time_saved = st.select_slider(
                "Time saved using this tool vs. manual comparison:",
                options=[
                    "No time saved",
                    "Minimal (< 30 min)",
                    "Moderate (30-60 min)",
                    "Significant (1-2 hours)",
                    "Substantial (2-4 hours)",
                    "Exceptional (4+ hours)",
                ],
                key="time_saved",
            )

        st.markdown("---")

        st.markdown("### Additional Feedback")

        feedback_type = st.multiselect(
            "What would make this tool better? (Select all that apply)",
            options=[
                "Better accuracy in detecting changes",
                "Faster processing speed",
                "More export options",
                "Better visualization of changes",
                "Support for PDF documents",
                "Track formatting changes",
                "Compare 3+ versions at once",
                "Email notifications",
                "Integration with other tools",
                "Better mobile support",
                "More detailed reports",
                "Customizable change categories",
            ],
            key="feedback_type",
        )

        general_feedback = st.text_area(
            "Any other comments or suggestions?",
            placeholder=(
                "Tell us what worked well, what didn't, or what features you'd like to see..."
            ),
            height=100,
            key="general_feedback",
        )

        # Contact information (optional)
        st.markdown("### Contact (Optional)")
        col1, col2 = st.columns(2)

        with col1:
            user_name = st.text_input(
                "Your name", placeholder="e.g., Jane Smith", key="user_name"
            )

        with col2:
            user_email = st.text_input(
                "Your email",
                placeholder="e.g., jane.smith@ndis.gov.au",
                key="user_email",
            )

        st.caption("Contact info helps us follow up if needed, but it's optional.")

        # Submit button
        if st.button("📤 Submit Feedback", type="primary", use_container_width=True):
            # Collect all feedback
            feedback_data = {
                "timestamp": datetime.now().isoformat(),
                "comparison_quality": comparison_quality,
                "ease_of_use": ease_of_use,
                "usefulness": usefulness,
                "manual_time": manual_time,
                "time_saved": time_saved,
                "missing_changes": missing_changes,
                "missed_details": st.session_state.get("missed_details", ""),
                "false_positives": false_positives,
                "false_positive_details": st.session_state.get(
                    "false_positive_details", ""
                ),
                "feature_requests": feedback_type,
                "general_feedback": general_feedback,
                "user_name": user_name,
                "user_email": user_email,
            }

            # Store in session state
            if "feedback_submissions" not in st.session_state:
                st.session_state["feedback_submissions"] = []

            st.session_state["feedback_submissions"].append(feedback_data)

            # Create downloadable feedback file
            feedback_df = pd.DataFrame([feedback_data])
            feedback_csv = feedback_df.to_csv(index=False)

            # Save feedback to S3
            try:
                if storage and storage_initialized:
                    s3_key = storage.upload_feedback(feedback_data)
                    st.success(f"Feedback saved to S3: {s3_key}")
                else:
                    st.warning("S3 not initialised - feedback saved locally only.")
            except Exception as e:
                st.error(f"Failed to save feedback to S3: {e}")

            st.download_button(
                label="📥 Download Your Feedback (for records)",
                data=feedback_csv,
                file_name=f"papl_comparison_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

            st.info(
                """
            📊 **Your feedback helps quantify value:**
            
            This data will be aggregated across all pilot users to:
            - Calculate average time savings
            - Measure accuracy and usability
            - Identify improvement priorities
            - Build evidence-based business case for broader deployment
            """
            )

# Footer
st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #666; padding: 20px;'>
<p><strong>PAPL Digital First - App 2: PAPL Comparison Tool</strong></p>
<p>Version 2.0 - Enhanced with Location Tracking, Structural Anomaly Detection & Context Display</p>
<p>Markets Delivery | NDIA</p>
<p>Semantic comparison with AWS integration</p>
</div>
""",
    unsafe_allow_html=True,
)
