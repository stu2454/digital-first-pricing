"""
PAPL Digital First - App 2: PAPL Comparison Tool (Comprehensive Enhanced Version)

Semantic comparison of PAPL .docx documents with AWS S3 integration
Enhanced with location tracking, detailed documentation, and user feedback
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
if os.path.exists('../../shared'):
    sys.path.append('../../shared')
elif os.path.exists('/app/shared'):
    sys.path.append('/app/shared')

from aws_storage import S3Storage
from papl_parser import PAPLParser
from semantic_comparer import SemanticComparer

# Load environment variables
from dotenv import load_dotenv
load_dotenv('../../.env')


# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="PAPL Digital First - Document Comparison",
    page_icon="📊",
    layout="wide"
)

# NDIA Brand Colors
NDIA_BLUE = "#003087"
NDIA_ACCENT = "#00B5E2"

# Custom CSS
st.markdown(f"""
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
""", unsafe_allow_html=True)

# Helper function to format locations
def format_location(location: dict) -> str:
    if not location:
        return ""
    parts = []
    if 'table_number' in location:
        parts.append(f"Table {location['table_number']}")
    if 'row_number' in location:
        parts.append(f"Row {location['row_number']}")
    if 'paragraph_number' in location:
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
if 'comparison_complete' not in st.session_state:
    st.session_state.comparison_complete = False
if 'old_parsed' not in st.session_state:
    st.session_state.old_parsed = None
if 'new_parsed' not in st.session_state:
    st.session_state.new_parsed = None
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = None
if 'old_s3_key' not in st.session_state:
    st.session_state.old_s3_key = None
if 'new_s3_key' not in st.session_state:
    st.session_state.new_s3_key = None

# HEADER
st.markdown("""
<div class="main-header">
    <h1>📊 PAPL Digital First</h1>
    <h3>Semantic Document Comparison Tool</h3>
    <p>Transforming Static Documents into Structured, Intelligent Data</p>
</div>
""", unsafe_allow_html=True)

# NAVIGATION HELPER
st.markdown("""
<div class="nav-helper">
    <strong>👋 Welcome!</strong> Use the tabs below to navigate:
    <strong>Upload & Compare</strong> → <strong>Results</strong> → <strong>Export</strong> | 
    <strong>About</strong> for methodology | <strong>Feedback</strong> to help us improve
</div>
""", unsafe_allow_html=True)


# Introduction Section
with st.container():
    st.markdown("## 🎯 What This Tool Does")
    
    st.info("""
    The PAPL Comparison Tool automatically identifies and categorizes changes between two versions of PAPL documents. 
    Instead of manually comparing 100+ page Word documents, this tool:
    """)
    
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
    
    st.warning("""
    PAPL documents change quarterly, affecting thousands of providers and participants. Manual comparison is:
    
    - ❌ **Time-consuming** (2-4 hours per comparison)
    - ❌ **Error-prone** (easy to miss changes in 100+ pages)
    - ❌ **Unstructured** (results in Word comments, not data)
    - ❌ **Not auditable** (no systematic record of what changed)
    """)
    
    st.success("""
    **This tool addresses these inefficiencies systematically:**
    
    - ⏱️ **Time Savings**: 85-95% reduction in comparison time (hours → minutes)
    - ✅ **Error Reduction**: Automated detection vs. manual review
    - 📊 **Structured Output**: Machine-readable data for downstream systems
    - 📝 **Audit Trail**: Complete, versioned record of all changes
    - 🎯 **Scalable Impact**: Benefits multiply across thousands of stakeholders
    
    **Pilot Evaluation:** This tool includes built-in measurement to quantify actual time savings 
    and value delivered during pilot deployment.
    """)

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
    
    compare_pricing = st.checkbox("Compare Pricing Data", value=True,
                                  help="Detect changes in support item prices")
    compare_rules = st.checkbox("Compare Business Rules", value=True,
                                help="Identify new, removed, or modified claiming rules")
    compare_guidance = st.checkbox("Compare Guidance Text", value=True,
                                   help="Track updates to policy guidance sections")
    compare_tables = st.checkbox("Compare Table Structures", value=True,
                                 help="Detect changes in table dimensions")
    
    upload_to_s3 = st.checkbox("Upload to AWS S3", value=storage_initialized, 
                                help="Store documents and results in S3 for AI Assistant",
                                disabled=not storage_initialized)
    
    st.markdown("---")
    
    # Quick Guide
    st.markdown("#### 🚀 Quick Start")
    st.info("""
    1. Upload old & new PAPL .docx files
    2. Click "Parse and Compare"
    3. View results in Results tab
    4. Export reports as needed
    5. Provide feedback to improve!
    """)
    
    st.markdown("---")
    st.caption("Markets Delivery | NDIA")

# Main Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 Upload & Compare", 
    "📊 Results", 
    "💾 Export & Storage",
    "📖 About",
    "💬 Feedback"
])

# ========================================
# TAB 1: Upload & Compare
# ========================================
with tab1:
    st.markdown("## Upload PAPL Documents")
    
    st.info("""
    **📝 Tips for Best Results:**
    
    - Use clean .docx files (not PDFs converted to Word)
    - Ensure both documents follow similar structure
    - Upload files in chronological order (older first, newer second)
    - File names help tracking - use meaningful names like "PAPL_2024Q1.docx"
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📄 Version 1 (Older)")
        old_file = st.file_uploader(
            "Upload older PAPL version",
            type=['docx'],
            key='old_file',
            help="Upload the older/baseline PAPL document"
        )
        
        if old_file:
            st.success(f"✓ Loaded: {old_file.name}")
            st.caption(f"Size: {old_file.size / 1024:.1f} KB")
    
    with col2:
        st.markdown("### 📄 Version 2 (Newer)")
        new_file = st.file_uploader(
            "Upload newer PAPL version",
            type=['docx'],
            key='new_file',
            help="Upload the newer/updated PAPL document"
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
                    
                    # Step 1: Upload to S3 (if enabled)
                    if upload_to_s3 and storage_initialized:
                        status_text.text("📤 Uploading documents to AWS S3...")
                        progress_bar.progress(10)
                        
                        st.session_state.old_s3_key = storage.upload_source_document(
                            file_data=old_file.read(),
                            document_type='papl',
                            filename=old_file.name
                        )
                        st.session_state.new_s3_key = storage.upload_source_document(
                            file_data=new_file.read(),
                            document_type='papl',
                            filename=new_file.name
                        )
                        # Reset file pointers
                        old_file.seek(0)
                        new_file.seek(0)
                    
                    # Step 2: Parse old document
                    status_text.text("📄 Parsing old document...")
                    progress_bar.progress(30)
                    st.session_state.old_parsed = parser.parse(old_file)
                    
                    # Step 3: Parse new document
                    status_text.text("📄 Parsing new document...")
                    progress_bar.progress(60)
                    st.session_state.new_parsed = parser.parse(new_file)
                    
                    # Step 4: Compare
                    status_text.text("🔍 Running semantic comparison...")
                    progress_bar.progress(80)
                    st.session_state.comparison_results = comparer.compare(
                        st.session_state.old_parsed,
                        st.session_state.new_parsed
                    )
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Comparison complete!")
                    
                    st.session_state.comparison_complete = True
                    st.success("✅ Comparison complete! View results in the 'Results' tab.")
                    st.balloons()
                    
                except Exception as e:
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
        
        # Summary metrics
        st.markdown("### 📈 Summary Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Pricing Changes",
                results['pricing_changes']['summary']['prices_changed'],
                delta=f"+{results['pricing_changes']['summary']['items_added']} items"
            )
        
        with col2:
            st.metric(
                "Rule Changes",
                results['rule_changes']['summary']['rules_added'] + 
                results['rule_changes']['summary']['rules_removed'] +
                results['rule_changes']['summary']['rules_modified'],
                delta=f"{results['rule_changes']['summary']['high_priority_changes']} high priority"
            )
        
        with col3:
            st.metric(
                "Guidance Changes",
                results['guidance_changes']['summary']['sections_modified'],
                delta=f"{results['guidance_changes']['summary']['word_count_change']:+d} words"
            )
        
        with col4:
            st.metric(
                "Table Changes",
                results['table_structure_changes']['summary']['structure_changed'],
                delta=f"{results['table_structure_changes']['summary']['content_changed']} content"
            )
        
        st.markdown("---")
        
        # Detailed results
        if compare_pricing:
            with st.expander("💰 Pricing Changes", expanded=True):
                pricing = results['pricing_changes']
                
                st.markdown(f"""
                **Summary:**
                - Tables Modified: {pricing['summary']['tables_modified']}
                - Items Added: {pricing['summary']['items_added']}
                - Items Removed: {pricing['summary']['items_removed']}
                - Prices Changed: {pricing['summary']['prices_changed']}
                """)
                
                # Show price changes with locations
                for detail in pricing['details']:
                    if detail['type'] == 'table_modified' and 'changes' in detail:
                        st.subheader(f"Table {detail['table_index'] + 1}")
                        
                        changes = detail['changes']
                        
                        # Price changes
                        if changes.get('prices_changed'):
                            st.markdown("#### 📈 Price Changes")
                            for change in changes['prices_changed'][:20]:
                                loc_display = format_location(change.get('new_location', {}))
                                loc_str = f" ({loc_display})" if loc_display else ""
                                
                                st.warning(f"""
**{change['item_name']}{loc_str}**  
{change['old_price']} → {change['new_price']} ({change['change']['absolute']}, {change['change']['percentage']})
""")
                        
                        # Added items
                        if changes.get('added'):
                            st.markdown("#### ✅ Added Items")
                            for item in changes['added'][:10]:
                                loc_display = format_location(item.get('location', {}))
                                loc_str = f" ({loc_display})" if loc_display else ""
                                st.success(f"**{item['item_name']}{loc_str}**: {item['price']}")
                        
                        # Removed items
                        if changes.get('removed'):
                            st.markdown("#### ❌ Removed Items")
                            for item in changes['removed'][:10]:
                                loc_display = format_location(item.get('location', {}))
                                loc_str = f" ({loc_display})" if loc_display else ""
                                st.error(f"**{item['item_name']}{loc_str}**: {item['price']}")
        
        if compare_rules:
            with st.expander("📋 Business Rule Changes", expanded=True):
                rules = results['rule_changes']
                
                st.markdown(f"""
                **Summary:**
                - Rules Added: {rules['summary']['rules_added']}
                - Rules Removed: {rules['summary']['rules_removed']}
                - Rules Modified: {rules['summary']['rules_modified']}
                - High Priority Changes: {rules['summary']['high_priority_changes']}
                """)
                
                # Show rule changes
                for detail in rules['details'][:15]:
                    loc_display = format_location(detail.get('location', {}))
                    loc_str = f" ({loc_display})" if loc_display else ""
                    
                    if detail['type'] == 'rule_added':
                        st.success(f"""
**➕ Rule Added{loc_str}**

{detail['text']}

*Type: {detail['rule_type']} | Priority: {detail['priority']}*
""")
                    elif detail['type'] == 'rule_removed':
                        st.error(f"""
**➖ Rule Removed{loc_str}**

{detail['text']}

*Type: {detail['rule_type']} | Priority: {detail['priority']}*
""")
                    elif detail['type'] == 'rule_modified':
                        st.warning(f"""
**✏️ Rule Modified** (Similarity: {detail['similarity']})

**Old:** {detail['old_text']}

**New:** {detail['new_text']}
""")
        
        if compare_guidance:
            with st.expander("📖 Guidance Changes", expanded=True):
                guidance = results['guidance_changes']
                
                st.markdown(f"""
                **Summary:**
                - Sections Added: {guidance['summary']['sections_added']}
                - Sections Removed: {guidance['summary']['sections_removed']}
                - Sections Modified: {guidance['summary']['sections_modified']}
                - Word Count Change: {guidance['summary']['word_count_change']:+d} words
                """)
                
                # Show section changes
                for detail in guidance['details'][:10]:
                    loc_display = format_location(detail.get('location', {}))
                    loc_str = f" ({loc_display})" if loc_display else ""
                    
                    if detail['type'] == 'section_added':
                        st.success(f"""
**➕ Section Added{loc_str}:** {detail['heading']}

Paragraphs: {detail['paragraph_count']}
""")
                    elif detail['type'] == 'section_removed':
                        st.error(f"""
**➖ Section Removed{loc_str}:** {detail['heading']}

Paragraphs: {detail['paragraph_count']}
""")
                    elif detail['type'] == 'section_modified':
                        st.warning(f"""
**✏️ Section Modified:** {detail['heading']}

Change: {detail['change_type']} ({detail['old_length']} → {detail['new_length']} words)
""")
        
        if compare_tables:
            with st.expander("📋 Table Structure Changes", expanded=True):
                tables = results['table_structure_changes']
                
                st.markdown(f"""
                **Summary:**
                - Tables Added: {tables['summary']['tables_added']}
                - Tables Removed: {tables['summary']['tables_removed']}
                - Structure Changed: {tables['summary']['structure_changed']}
                - Content Changed: {tables['summary']['content_changed']}
                """)
                
                # Show structural changes
                for detail in tables['details']:
                    if detail['type'] == 'table_modified' and detail['structure_changed']:
                        st.warning(f"""
**⚠️ Table {detail['table_index'] + 1} Structure Changed**

Rows: {detail['old_dimensions']['rows']} → {detail['new_dimensions']['rows']} ({'+' if detail['row_diff'] > 0 else ''}{detail['row_diff']})

Columns: {detail['old_dimensions']['cols']} → {detail['new_dimensions']['cols']} ({'+' if detail['col_diff'] > 0 else ''}{detail['col_diff']})
""")

# ========================================
# TAB 3: Export & Storage
# ========================================
with tab3:
    st.markdown("## Export & Storage")
    
    if not st.session_state.comparison_complete:
        st.info("👈 Complete a comparison first to export results")
    else:
        st.markdown("### 💾 AWS S3 Storage")
        
        if st.session_state.get('old_s3_key') and st.session_state.get('new_s3_key'):
            st.success("✅ Documents stored in AWS S3")
            
            col1, col2 = st.columns(2)
            with col1:
                st.code(st.session_state.old_s3_key, language='text')
            with col2:
                st.code(st.session_state.new_s3_key, language='text')
            
            st.info("💡 These documents are now available to the AI Assistant for querying")
        
        st.markdown("---")
        st.markdown("### 📥 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export as JSON
            if st.button("📄 Export as JSON", use_container_width=True):
                json_data = json.dumps(st.session_state.comparison_results, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name=f"papl_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            # Export as CSV
            if st.button("📊 Export as CSV", use_container_width=True):
                pricing_data = []
                for detail in st.session_state.comparison_results['pricing_changes']['details']:
                    if detail['type'] == 'table_modified' and 'changes' in detail:
                        for price_change in detail['changes'].get('prices_changed', []):
                            pricing_data.append(price_change)
                
                if pricing_data:
                    df = pd.DataFrame(pricing_data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"pricing_changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No pricing changes to export")
        
        with col3:
            # Export as Markdown
            if st.button("📝 Export as Markdown", use_container_width=True):
                results = st.session_state.comparison_results
                md_report = f"""# PAPL Comparison Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

### Pricing Changes
- Tables Modified: {results['pricing_changes']['summary']['tables_modified']}
- Items Added: {results['pricing_changes']['summary']['items_added']}
- Items Removed: {results['pricing_changes']['summary']['items_removed']}
- Prices Changed: {results['pricing_changes']['summary']['prices_changed']}

### Business Rules
- Rules Added: {results['rule_changes']['summary']['rules_added']}
- Rules Removed: {results['rule_changes']['summary']['rules_removed']}
- Rules Modified: {results['rule_changes']['summary']['rules_modified']}
- High Priority Changes: {results['rule_changes']['summary']['high_priority_changes']}

### Guidance
- Sections Added: {results['guidance_changes']['summary']['sections_added']}
- Sections Removed: {results['guidance_changes']['summary']['sections_removed']}
- Sections Modified: {results['guidance_changes']['summary']['sections_modified']}
- Word Count Change: {results['guidance_changes']['summary']['word_count_change']} words

### Tables
- Structure Changed: {results['table_structure_changes']['summary']['structure_changed']}
- Content Changed: {results['table_structure_changes']['summary']['content_changed']}

---

*Generated by PAPL Digital First - Semantic Comparison Tool*
*Enhanced with Location Tracking and Context Display*
"""
                
                st.download_button(
                    label="Download Markdown",
                    data=md_report,
                    file_name=f"papl_comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )

# ========================================
# TAB 4: About
# ========================================
with tab4:
    st.markdown("## 📖 About This Tool")
    
    # Development Story
    st.markdown("### 🔨 How This Tool Was Developed")
    st.markdown("""
    This tool is part of the **PAPL Digital First** initiative at NDIA Markets Delivery, led by Stuart Smith. 
    The project aims to transform PAPL documents from static PDF/Word files into structured, machine-readable data.
    
    **Development Approach:**
    - **Problem Identification**: Manual PAPL comparison was taking 2-4 hours and missing critical changes
    - **Proof of Concept**: Built initial parser to extract tables and text from .docx files
    - **Semantic Analysis**: Developed classification system to distinguish pricing, rules, and guidance
    - **Enhanced Features**: Added location tracking, context display, and AWS integration
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
    """)
    
    st.markdown("---")
    
    # How Rules Are Defined
    st.markdown("### 🎯 How the Tool Defines 'Business Rules'")
    st.markdown("""
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
    """)
    
    st.markdown("---")
    
    # Technical Methodology
    st.markdown("### 🔬 Technical Methodology")
    
    with st.expander("📄 Document Parsing Process"):
        st.markdown("""
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
        
        **Step 5: Add Location Tracking**
        - Every item gets a `location` dict with precise coordinates
        - Enables exact references: "Table 3, Row 5", "Paragraph 42"
        """)
    
    with st.expander("🔍 Comparison Algorithm"):
        st.markdown("""
        **Pricing Comparison:**
        1. Extract all pricing items from both documents
        2. Create lookup tables by item name
        3. Identify added items (in new, not in old)
        4. Identify removed items (in old, not in new)
        5. Identify modified items (same name, different price/data)
        6. Calculate price changes (absolute and percentage)
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
        """)
    
    with st.expander("🎨 Why Semantic vs. Text Comparison?"):
        st.markdown("""
        **Traditional text comparison** (like Word's "Compare Documents"):
        - ❌ Shows every formatting change as a "difference"
        - ❌ Doesn't understand context (can't tell pricing from rules)
        - ❌ Can't quantify changes (number of price increases)
        - ❌ Produces unstructured output (marked-up document)
        
        **Semantic comparison** (this tool):
        - ✅ Ignores pure formatting changes
        - ✅ Understands document structure (pricing vs. rules vs. guidance)
        - ✅ Quantifies changes (23 price changes, 5 new rules)
        - ✅ Produces structured data (JSON, CSV, reports)
        - ✅ Enables analytics (average price increase, high-priority rule changes)
        
        **Example:**
        If a price changes from **$75.00** to **$80.00**:
        - Text diff: Shows strikethrough and insertion
        - Semantic diff: Reports "+$5.00 (+6.7%)" with location and context
        """)
    
    st.markdown("---")
    
    # Project Context
    st.markdown("### 🎯 Project Context: PAPL Digital First")
    st.markdown("""
    This tool is one component of a larger initiative to transform NDIA's pricing information:
    
    **Current State (Problem):**
    - PAPL as 104-page Word document (83 tables, 162 sections, 1,235 paragraphs)
    - Pricing "locked up" in PDFs/Word - can't be queried or validated
    - $25.56M annual hidden costs from manual navigation and errors
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
    - Creates audit trail for compliance and governance
    
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
    """)

# ========================================
# TAB 5: Feedback
# ========================================
with tab5:
    st.markdown("## 💬 Feedback & Suggestions")
    
    st.info("""
    **📊 Pilot Evaluation:** Your feedback is essential for measuring the value of this tool!
    
    This data will help us:
    - Quantify actual time savings vs. manual comparison
    - Calculate return on investment for broader deployment
    - Identify improvements for enterprise rollout
    - Build evidence-based business case for digital-first transformation
    
    Please provide honest feedback - both positive and critical insights are valuable.
    """)
    
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
                    "⭐ Very Poor - Not useful"
                ],
                index=None,
                key="comparison_quality"
            )
            
            missing_changes = st.checkbox(
                "The tool missed important changes",
                key="missing_changes"
            )
            
            if missing_changes:
                st.text_area(
                    "What changes were missed?",
                    placeholder="E.g., Price change in Table 5, new paragraph in Section 3...",
                    key="missed_details"
                )
            
            false_positives = st.checkbox(
                "The tool flagged things that weren't really changes",
                key="false_positives"
            )
            
            if false_positives:
                st.text_area(
                    "What was incorrectly flagged?",
                    placeholder="E.g., Formatting-only changes, unchanged content...",
                    key="false_positive_details"
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
                    "⭐ Very Difficult"
                ],
                index=None,
                key="ease_of_use"
            )
            
            usefulness = st.radio(
                "Would you use this tool again?",
                options=[
                    "Definitely - Very useful",
                    "Probably - Somewhat useful",
                    "Maybe - Neutral",
                    "Probably not - Not very useful",
                    "Definitely not - Not useful"
                ],
                index=None,
                key="usefulness"
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
                    "I wouldn't do it manually"
                ],
                index=None,
                key="manual_time"
            )
            
            time_saved = st.select_slider(
                "Time saved using this tool vs. manual comparison:",
                options=[
                    "No time saved",
                    "Minimal (< 30 min)",
                    "Moderate (30-60 min)",
                    "Significant (1-2 hours)",
                    "Substantial (2-4 hours)",
                    "Exceptional (4+ hours)"
                ],
                key="time_saved"
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
                "Customizable change categories"
            ],
            key="feedback_type"
        )
        
        general_feedback = st.text_area(
            "Any other comments or suggestions?",
            placeholder="Tell us what worked well, what didn't, or what features you'd like to see...",
            height=100,
            key="general_feedback"
        )
        
        # Contact information (optional)
        st.markdown("### Contact (Optional)")
        col1, col2 = st.columns(2)
        
        with col1:
            user_name = st.text_input(
                "Your name",
                placeholder="e.g., Jane Smith",
                key="user_name"
            )
        
        with col2:
            user_email = st.text_input(
                "Your email",
                placeholder="e.g., jane.smith@ndis.gov.au",
                key="user_email"
            )
        
        st.caption("Contact info helps us follow up if needed, but it's optional.")
        
        # Submit button
        if st.button("📤 Submit Feedback", type="primary", use_container_width=True):
            
            # Collect all feedback
            feedback_data = {
                'timestamp': datetime.now().isoformat(),
                'comparison_quality': comparison_quality,
                'ease_of_use': ease_of_use,
                'usefulness': usefulness,
                'manual_time': manual_time,
                'time_saved': time_saved,
                'missing_changes': missing_changes,
                'missed_details': st.session_state.get('missed_details', ''),
                'false_positives': false_positives,
                'false_positive_details': st.session_state.get('false_positive_details', ''),
                'feature_requests': feedback_type,
                'general_feedback': general_feedback,
                'user_name': user_name,
                'user_email': user_email
            }
            
            # Store in session state
            if 'feedback_submissions' not in st.session_state:
                st.session_state['feedback_submissions'] = []
            
            st.session_state['feedback_submissions'].append(feedback_data)
            
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
                mime="text/csv"
            )
            
            st.info("""
            📊 **Your feedback helps quantify value:**
            
            This data will be aggregated across all pilot users to:
            - Calculate average time savings
            - Measure accuracy and usability
            - Identify improvement priorities
            - Build evidence-based business case for broader deployment
            """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
<p><strong>PAPL Digital First - App 2: PAPL Comparison Tool</strong></p>
<p>Version 2.0 - Enhanced with Location Tracking & Context Display</p>
<p>Markets Delivery | NDIA</p>
<p>Semantic comparison with AWS integration</p>
</div>
""", unsafe_allow_html=True)