# PAPL Digital First Ecosystem

Transform NDIS Pricing Arrangements and Price Limits (PAPL) from static documents into an intelligent, accessible, digital-first platform.

## 🎯 Vision

**From this:**
- 104-page PDF documents
- Manual searches taking 30 minutes
- Unvalidatable business rules
- Static, inaccessible formats

**To this:**
- Structured, machine-readable data (JSON/YAML/Markdown)
- AI-powered assistance (3-second answers)
- Automated validation
- Multiple presentations (one source, infinite views)
- True accessibility (WCAG 2.1 AA compliant)

---

## 🏗️ Architecture

Three independent applications sharing AWS infrastructure:

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   APP 1:         │  │   APP 2:         │  │   APP 3:         │
│   Catalogue      │  │   PAPL           │  │   AI Assistant   │
│   Comparison     │  │   Comparison     │  │   (RAG Chatbot)  │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                      │
         └─────────────────────┴──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   AWS Infrastructure│
                    │                     │
                    │ • S3 Storage        │
                    │ • Bedrock (Claude)  │
                    │ • OpenSearch        │
                    └─────────────────────┘
```

### App 1: Support Catalogue Comparison
- Compare NDIS Support Catalogues (Excel) across states/versions
- Track price changes, identify additions/removals
- Export results as JSON to shared knowledge base

### App 2: PAPL Document Comparison
- Compare PAPL .docx documents with semantic understanding
- Parse structure (pricing → JSON, rules → YAML, guidance → MD)
- Track meaningful changes (not just text diffs)
- Export structured comparison results

### App 3: AI Assistant (RAG Chatbot)
- Multi-source document interrogation
- Query PAPL, catalogues, operational guides, "Would We Fund It" docs
- Claude 3.5 Sonnet via AWS Bedrock
- Expert validation interface
- Source citations

---

## 📦 Repository Structure

```
papl-digital-first/
├── shared/                      # Reusable packages
│   ├── aws_storage.py          # S3 operations
│   ├── papl_parser.py          # PAPL DOCX → JSON/YAML/MD
│   ├── catalogue_parser.py     # XLSX → JSON
│   ├── document_comparer.py    # Comparison logic
│   ├── bedrock_client.py       # AWS Bedrock wrapper
│   └── opensearch_client.py    # Vector DB operations
│
├── apps/
│   ├── 01-catalogue-comparison/
│   ├── 02-papl-comparison/
│   └── 03-ai-assistant/
│
├── infrastructure/
│   ├── s3-bucket-structure.md
│   ├── iam-policy.json
│   └── opensearch-setup.md
│
└── docs/
    ├── architecture.md
    ├── aws-setup.md
    └── deployment.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- AWS account with credentials
- Docker (optional, for containerized deployment)

### Setup

1. **Clone repository**
```bash
git clone https://github.com/stu2454/papl-digital-first.git
cd papl-digital-first
```

2. **Configure AWS credentials**
```bash
cp .env.example .env
# Edit .env with your AWS credentials
```

3. **Install shared dependencies**
```bash
pip install boto3 python-dotenv
```

4. **Run individual apps**
```bash
cd apps/02-papl-comparison
pip install -r requirements.txt
streamlit run app.py
```

---

## 🔧 AWS Infrastructure

### S3 Bucket Structure

```
s3://papl-digital-first/
├── source-documents/
│   ├── papl/
│   ├── catalogues/
│   ├── operational-guides/
│   ├── would-we-fund-it/
│   └── code-guides/
├── processed-data/
│   ├── papl-json/
│   ├── papl-yaml/
│   ├── papl-markdown/
│   └── catalogues-json/
├── comparisons/
│   ├── papl-comparisons/
│   └── catalogue-comparisons/
└── embeddings/
    └── metadata/
```

### Required AWS Services
- **S3** - Document storage
- **Bedrock** - Claude 3.5 Sonnet for AI generation
- **Bedrock** - Titan Embeddings V2 for vectors
- **OpenSearch Serverless** - Vector database for RAG

---

## 📚 Documentation

- **[Architecture Overview](docs/architecture.md)** - System design and data flow
- **[AWS Setup Guide](docs/aws-setup.md)** - IAM permissions, bucket creation
- **[Deployment Guide](docs/deployment.md)** - Deploy to Render/production
- **[Development Guide](docs/development.md)** - Local development workflow

---

## 🎯 Development Status

### Phase 1: Foundation ✅
- [x] Repository structure
- [x] Shared AWS storage module
- [x] Environment configuration

### Phase 2: App 1 - Catalogue Comparison (Week 1)
- [ ] Port existing xlsx comparison tool
- [ ] Integrate S3 storage
- [ ] JSON export functionality
- [ ] Deploy to Render

### Phase 3: App 2 - PAPL Comparison (Week 2-3)
- [ ] Semantic PAPL parser
- [ ] Structured comparison engine
- [ ] S3 integration
- [ ] Deploy to Render

### Phase 4: App 3 - AI Assistant (Week 4-6)
- [ ] Document ingestion pipeline
- [ ] Bedrock integration
- [ ] OpenSearch vector store
- [ ] Expert validation interface
- [ ] Deploy to Render

### Phase 5: Integration & Testing (Week 7)
- [ ] End-to-end testing
- [ ] User documentation
- [ ] Demo preparation

---

## 🤝 Contributing

This is currently a demonstration project by Stuart Smith (Markets Delivery, NDIA).

For questions or collaboration:
- **Email:** stuart.smith@ndis.gov.au
- **GitHub:** @stu2454

---

## 📊 Impact

### Current State (Problems)
- 30 minutes average search time per PAPL query
- $2.8M annual cost (100 coordinators × 5 queries/day × 30 min)
- Manual, error-prone claiming validation
- No version control or change tracking
- Inaccessible to screen readers

### Future State (Solutions)
- 3-second AI-powered answers
- $186K annual cost (93% reduction)
- Automated validation preventing errors
- Complete change history
- WCAG 2.1 AA accessible

**Annual savings: ~$2.6M**  
**Time savings: 90% reduction in search time**

---

## 📋 License

This project is for NDIA internal use and demonstration purposes.

---

## 🎉 Acknowledgments

Built on insights from:
- 2023 Markets Delivery study on AT information searches
- AWS Bedrock RAG architecture patterns
- NDIA digital transformation initiatives

---

**Status:** Demo/Proof of Concept  
**Version:** 0.1.0  
**Last Updated:** December 2024
