# App 2: PAPL Comparison Tool

Semantic comparison of PAPL .docx documents with AWS S3 integration.

---

## 🎯 Features

### Semantic Parsing
- **Pricing Data** → JSON: Extract support items, prices, categories
- **Business Rules** → YAML: Extract claiming rules, conditions, requirements
- **Guidance Text** → Markdown: Extract policy explanations and context

### Intelligent Comparison
- **Pricing Changes**: Track price increases/decreases with percentages
- **Rule Changes**: Identify new/modified/removed requirements
- **Guidance Updates**: Detect section additions, removals, modifications
- **Table Structure**: Catch dimensional changes (1 row → 9 rows)

### AWS Integration
- **S3 Storage**: Upload source documents automatically
- **Processed Data**: Store JSON/YAML/MD for AI Assistant
- **Comparison History**: Save results for future reference
- **Knowledge Base**: Enable AI chatbot to query all data

### Export Options
- **JSON**: Full comparison results for systems
- **CSV**: Pricing changes for spreadsheets
- **Markdown**: Summary reports for humans

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- AWS credentials configured in `../../.env`
- Docker (optional)

### Option 1: Python (Local)

```bash
cd apps/02-papl-comparison

# Install dependencies
pip install -r requirements.txt

# Run app
streamlit run app.py
```

**Access:** http://localhost:8501

### Option 2: Docker Compose (Recommended)

```bash
cd apps/02-papl-comparison

# Build and start
docker-compose up --build
```

**Access:** http://localhost:8503

---

## 📋 Usage

### Step 1: Upload Documents
1. Upload older PAPL version (Version 1)
2. Upload newer PAPL version (Version 2)

### Step 2: Configure Options
- Enable/disable specific comparisons
- Toggle AWS S3 upload
- Adjust comparison sensitivity

### Step 3: Compare
Click "Parse and Compare Documents"

The tool will:
1. Upload documents to S3 (if enabled)
2. Parse both documents semantically
3. Extract pricing/rules/guidance
4. Store parsed data in S3
5. Perform semantic comparison
6. Save comparison results

### Step 4: Review Results
- **Summary Dashboard**: High-level overview
- **Pricing Changes**: See price increases/decreases
- **Rule Changes**: Review new/modified requirements
- **Guidance Updates**: Track policy changes
- **Table Structures**: Identify dimensional changes

### Step 5: Export
- Download JSON for systems
- Export CSV for analysis
- Generate Markdown reports

---

## 🏗️ Architecture

### Data Flow

```
User Uploads → Parse (PAPL Parser) → Store in S3
                                           ↓
                                   Compare (Semantic)
                                           ↓
                                   Store Results → Export
                                           ↓
                                   AI Assistant Can Query
```

### Components

**PAPLParser** (`../../shared/papl_parser.py`):
- Extracts structured data from .docx
- Classifies content (pricing/rules/guidance)
- Generates JSON/YAML/Markdown

**SemanticComparer** (`../../shared/semantic_comparer.py`):
- Compares parsed structures
- Identifies semantic changes
- Calculates impacts

**S3Storage** (`../../shared/aws_storage.py`):
- Manages S3 uploads/downloads
- Organizes folder structure
- Tracks document lineage

---

## 📊 Comparison Types

### 1. Pricing Comparison
**What it catches:**
- Price increases/decreases
- New support items
- Removed support items
- Category changes
- Percentage changes

**Example Output:**
```json
{
  "item_name": "Occupational Therapy",
  "old_price": "$193.99",
  "new_price": "$199.50",
  "change": {
    "absolute": "$5.51",
    "percentage": "+2.8%"
  }
}
```

### 2. Business Rules Comparison
**What it catches:**
- New requirements added
- Requirements removed
- Condition changes
- Priority shifts (must → should)
- Threshold modifications

**Example Output:**
```yaml
rule_change:
  type: requirement_added
  priority: high
  text: "Claims must be quoted for amounts exceeding $1,500"
  rule_type: claiming_rule
```

### 3. Guidance Comparison
**What it catches:**
- Section additions
- Section removals
- Content modifications
- Word count changes
- Tone shifts (guidance → requirement)

**Example Output:**
```markdown
## Section Modified: Assessment Requirements
- Change type: significant_change
- Old length: 245 words
- New length: 412 words
- Added emphasis on documentation requirements
```

### 4. Table Structure Comparison
**What it catches:**
- Row additions/removals (e.g., 1 → 9 rows)
- Column additions/removals
- Cell content changes
- Dimension shifts

**Example Output:**
```
Table 1 Structure Changed:
- Rows: 1 → 9 (+8 rows)
- Columns: 5 → 5 (0)
- Type: Major expansion
```

---

## 🔧 Configuration

### Environment Variables

Required in `../../.env`:
```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-southeast-2
S3_BUCKET_NAME=papl-digital-first
```

### Comparison Options

**In Sidebar:**
- Compare Pricing Data (on/off)
- Compare Business Rules (on/off)
- Compare Guidance Text (on/off)
- Compare Table Structures (on/off)
- Upload to AWS S3 (on/off)

---

## 📁 S3 Storage Structure

Documents uploaded to:
```
s3://papl-digital-first/
├── source-documents/papl/
│   └── 20241202_153045_PAPL_2024Q1.docx
├── processed-data/
│   ├── papl-json/
│   ├── papl-yaml/
│   └── papl-markdown/
└── comparisons/papl-comparisons/
    └── papl_comparison_20241202_153045.json
```

---

## 💡 Use Cases

### 1. Quarterly PAPL Updates
**Scenario:** New PAPL published quarterly

**Workflow:**
1. Upload old and new PAPL
2. Run comparison
3. Review pricing changes (for provider communications)
4. Check rule changes (for compliance updates)
5. Export summary for stakeholders

### 2. Validation Before Publication
**Scenario:** Draft PAPL needs review

**Workflow:**
1. Compare draft vs. current
2. Verify intended changes present
3. Check for unintended changes
4. Generate change summary for approval

### 3. Coordinator Training
**Scenario:** New PAPL version released

**Workflow:**
1. Run comparison
2. Export pricing changes as CSV
3. Generate rule changes report
4. Use for training materials

### 4. Provider Communications
**Scenario:** Notify providers of changes

**Workflow:**
1. Compare versions
2. Extract pricing table
3. Filter by relevant categories
4. Generate bulletin content

---

## 🐛 Troubleshooting

### Issue: AWS Connection Failed

**Solution:**
- Check `.env` file exists in project root
- Verify AWS credentials are correct
- Test with: `aws s3 ls` in terminal
- Check IAM permissions

### Issue: Parse Failed

**Cause:** Document format issues

**Solution:**
- Ensure .docx format (not .doc)
- Check file isn't corrupted
- Verify not password-protected
- Try re-saving in Word

### Issue: Comparison Incomplete

**Cause:** Documents too different

**Solution:**
- Verify both are PAPL documents
- Check versions aren't too far apart
- Review parsing results first

### Issue: S3 Upload Slow

**Cause:** Large documents or slow connection

**Solution:**
- Normal for 100+ page documents
- Consider local-only mode
- Check network connection

---

## 📈 Performance

**Typical Processing Times:**
- Small PAPL (< 50 pages): 10-20 seconds
- Medium PAPL (50-150 pages): 30-60 seconds
- Large PAPL (150+ pages): 1-2 minutes

**Includes:**
- Document parsing
- S3 uploads
- Semantic comparison
- Result storage

---

## 🎯 Roadmap

**Phase 1 (Complete):** ✅
- Semantic parsing
- AWS integration
- Basic comparison
- Export options

**Phase 2 (Next):**
- [ ] PDF support
- [ ] Diff visualization
- [ ] Change timeline
- [ ] Smart matching (handle reordered tables)

**Phase 3 (Future):**
- [ ] Batch comparison (multiple versions)
- [ ] Change impact analysis
- [ ] Stakeholder notifications
- [ ] Integration with App 3 (AI Assistant)

---

## 📞 Support

**Issues or Questions:**
- Email: stuart.smith@ndis.gov.au
- GitHub: @stu2454
- Use in-app feedback form

---

## 🎉 Success!

You now have a production-ready PAPL comparison tool that:
- ✅ Parses documents semantically
- ✅ Compares intelligently
- ✅ Stores in AWS for AI chatbot
- ✅ Exports in multiple formats
- ✅ Runs locally or containerized

**Start comparing PAPLs!** 🚀
