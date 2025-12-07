# Render Deployment Guide - PAPL Comparison Tool

**Status:** ✅ Production-Ready - Tested and Working  
**Date:** December 2024  
**App:** App 2 - PAPL Comparison Tool  

---

## 📋 Overview

This guide documents the **working Render configuration** for deploying the PAPL Comparison Tool from the `digital-first-pricing` GitHub repository.

**Key Changes from Local Development:**
- ✅ S3 feedback storage (replaced email)
- ✅ Monorepo structure with shared modules
- ✅ Docker-based deployment
- ✅ Environment variable configuration

---

## 🏗️ Repository Structure

```
digital-first-pricing/              ← Repo root (Render clones here)
│
├── apps/
│   └── 02-papl-comparison/         ← App folder
│       ├── Dockerfile              ← Build instructions for Render
│       ├── app.py                  ← Main Streamlit app
│       ├── requirements.txt        ← App dependencies
│       └── docker-compose.yml      ← Local dev only (Render ignores)
│
├── shared/                         ← Shared modules
│   ├── aws_storage.py              ← S3 operations + feedback storage
│   ├── papl_parser.py              ← PAPL parsing logic
│   ├── semantic_comparer.py        ← Comparison engine
│   └── requirements.txt            ← Shared dependencies
│
└── README.md
```

**Critical Understanding:**
- Render builds from **repo root** (`/`)
- Dockerfile is in **app folder** (`apps/02-papl-comparison/`)
- Shared code must be **copied into container** from root

---

## 🐳 Dockerfile Configuration

**Location:** `apps/02-papl-comparison/Dockerfile`

### Key Features

```dockerfile
# 1. Base Image - Python 3.11 slim
FROM python:3.11-slim

# 2. Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# 3. System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Working Directory
WORKDIR /app

# 5. Copy App Code (from repo root)
COPY apps/02-papl-comparison /app

# 6. Copy Shared Modules (from repo root)
COPY shared /app/shared

# 7. Install Dependencies
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt
RUN pip install -r /app/shared/requirements.txt

# 8. Expose Port & Start
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

### Why This Works

1. **Build Context = Repo Root** → Can access both `apps/` and `shared/`
2. **Two requirements.txt files** → App dependencies + shared dependencies
3. **Explicit COPY paths** → From root to `/app` in container
4. **Streamlit ENV vars** → Configured for Render's environment

---

## ⚙️ Render Configuration

### Service Type
- **Type:** Web Service
- **Environment:** Docker

### Build Settings

| Setting | Value | Notes |
|---------|-------|-------|
| **Root Directory** | `./` | Repo root |
| **Dockerfile Path** | `./apps/02-papl-comparison/Dockerfile` | Path from root |
| **Docker Build Context** | `./` | Must be root to access shared/ |
| **Build Command** | *(leave blank)* | Uses Dockerfile |
| **Start Command** | *(leave blank)* | Uses Dockerfile CMD |

### Environment Variables

Add these in **Render Dashboard → Environment**:

```bash
# AWS Configuration (Required)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-southeast-2
S3_BUCKET_NAME=papl-digital-first

# Python Configuration (Required)
PYTHONPATH=/app:/app/shared

# Streamlit Configuration (Optional - set in Dockerfile)
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

**Note:** No email/SMTP variables needed - feedback goes to S3!

---

## 📦 Dependencies

### App Requirements (`apps/02-papl-comparison/requirements.txt`)

```
streamlit
boto3
python-dotenv
python-docx
pandas
numpy
fuzzywuzzy
python-Levenshtein
Pillow
requests
```

### Shared Requirements (`shared/requirements.txt`)

```
boto3
python-dotenv
python-docx
```

**Key Notes:**
- No `smtplib` needed (built-in to Python)
- `fuzzywuzzy` + `python-Levenshtein` for semantic comparison
- `Pillow` for image handling
- `requests` for web operations

---

## 💾 S3 Feedback Implementation

### How It Works

**Old Approach (Email):**
```python
send_feedback_email(feedback_data)  # ❌ Removed
```

**New Approach (S3):**
```python
# In app.py, line ~1105
if storage and storage_initialized:
    s3_key = storage.upload_feedback(feedback_data)
    st.success(f"Feedback saved to S3: {s3_key}")
```

### S3 Storage Structure

```
s3://papl-digital-first/
├── source-documents/
├── processed-data/
├── comparisons/
└── feedback/                          ← NEW: Feedback storage
    └── papl-comparison/
        └── feedback_20241203_143025.json
```

### Feedback Data Format

```json
{
  "timestamp": "2024-12-03T14:30:25",
  "comparison_quality": "⭐⭐⭐⭐ Good - Caught most changes",
  "ease_of_use": "⭐⭐⭐⭐⭐ Very Easy",
  "usefulness": "Definitely - Very useful",
  "manual_time": "2-4 hours",
  "time_saved": "Substantial (2-4 hours)",
  "missing_changes": false,
  "missed_details": "",
  "false_positives": false,
  "false_positive_details": "",
  "feature_requests": ["Better visualization", "More export options"],
  "general_feedback": "Really helpful tool!",
  "user_name": "Jane Smith",
  "user_email": "jane.smith@ndis.gov.au"
}
```

### Required Method in `shared/aws_storage.py`

Add this method to your `S3Storage` class:

```python
def upload_feedback(self, feedback_data: dict) -> str:
    """
    Upload user feedback to S3
    
    Args:
        feedback_data: Dictionary containing feedback fields
        
    Returns:
        S3 key where feedback was stored
    """
    import json
    from datetime import datetime
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    s3_key = f"feedback/papl-comparison/feedback_{timestamp}.json"
    
    # Convert to JSON
    feedback_json = json.dumps(feedback_data, indent=2)
    
    # Upload to S3
    self.s3_client.put_object(
        Bucket=self.bucket_name,
        Key=s3_key,
        Body=feedback_json,
        ContentType='application/json'
    )
    
    return s3_key
```

---

## 🚀 Deployment Steps

### 1. Prerequisites

- [x] GitHub repo: `stu2454/digital-first-pricing`
- [x] Render account
- [x] AWS credentials (IAM user with S3 access)
- [x] S3 bucket: `papl-digital-first`

### 2. Create New Web Service

1. **Render Dashboard** → New → Web Service
2. **Connect Repository:**
   - Link GitHub account
   - Select: `stu2454/digital-first-pricing`
   - Branch: `main`

### 3. Configure Service

**Basic Settings:**
- Name: `papl-comparison-tool`
- Region: Choose closest to users
- Branch: `main`

**Build Settings:**
- Root Directory: `./`
- Environment: `Docker`
- Dockerfile Path: `./apps/02-papl-comparison/Dockerfile`

**Advanced Settings:**
- Docker Build Context: `./`
- Auto-Deploy: `Yes` (deploys on git push)

### 4. Add Environment Variables

In **Environment** tab, add:

```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=ap-southeast-2
S3_BUCKET_NAME=papl-digital-first
PYTHONPATH=/app:/app/shared
```

### 5. Deploy

1. Click **Create Web Service**
2. Wait for build (~3-5 minutes)
3. Check logs for errors
4. Access app at: `https://papl-comparison-tool.onrender.com`

### 6. Test Deployment

- [ ] App loads successfully
- [ ] Upload two PAPL documents
- [ ] Run comparison
- [ ] View results
- [ ] Export works
- [ ] Submit feedback → Check S3 for file
- [ ] AWS S3 integration works

---

## 🔍 Troubleshooting

### Common Issues & Solutions

#### ❌ "Cannot find /apps/02-papl-comparison/app.py"

**Cause:** Incorrect Dockerfile path or build context

**Fix:**
```bash
# Render Dashboard → Settings
Root Directory: ./
Dockerfile Path: ./apps/02-papl-comparison/Dockerfile
Docker Build Context: ./
```

#### ❌ ModuleNotFoundError: No module named 'aws_storage'

**Cause:** Shared modules not in Python path

**Fix:**
```bash
# Add to Render environment variables
PYTHONPATH=/app:/app/shared
```

**And verify Dockerfile has:**
```dockerfile
COPY shared /app/shared
```

#### ❌ ModuleNotFoundError: No module named 'boto3'

**Cause:** Shared requirements not installed

**Fix in Dockerfile:**
```dockerfile
# Make sure BOTH requirements are installed
RUN pip install -r /app/requirements.txt
RUN pip install -r /app/shared/requirements.txt
```

#### ❌ COPY ../../shared fails during build

**Cause:** Invalid Docker path (going outside build context)

**Fix:**
```dockerfile
# From repo root, use:
COPY shared /app/shared

# NOT:
COPY ../../shared /app/shared  # ❌ Wrong
```

#### ❌ Render build stuck on "Downloading cache"

**Cause:** Previous failed build cached

**Fix:**
1. Render Dashboard → Settings
2. Clear Build Cache
3. Manual Deploy

#### ❌ Streamlit not accessible (connection refused)

**Cause:** Wrong port or address binding

**Fix in Dockerfile:**
```dockerfile
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
EXPOSE 8501
```

#### ❌ Feedback not saving to S3

**Cause 1:** AWS credentials not set

**Fix:** Verify environment variables in Render

**Cause 2:** `upload_feedback` method missing

**Fix:** Add method to `shared/aws_storage.py` (see code above)

**Cause 3:** S3 permissions insufficient

**Fix:** IAM policy needs `s3:PutObject` permission:
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::papl-digital-first/*",
    "arn:aws:s3:::papl-digital-first"
  ]
}
```

---

## 📊 Render Build Process

### What Happens During Deployment

```
1. Render clones repo → /opt/render/project/src/
2. Changes to build context → /opt/render/project/src/
3. Loads Dockerfile → apps/02-papl-comparison/Dockerfile
4. Executes build steps:
   ├─ FROM python:3.11-slim
   ├─ COPY apps/02-papl-comparison → /app
   ├─ COPY shared → /app/shared
   ├─ pip install -r /app/requirements.txt
   └─ pip install -r /app/shared/requirements.txt
5. Builds container image
6. Starts container:
   └─ CMD ["streamlit", "run", "app.py"]
7. Exposes on port 8501
8. Maps to public URL
```

**Build Time:** ~3-5 minutes  
**Rebuild triggers:** Git push to `main` branch

---

## 🔐 Security Best Practices

### Environment Variables

✅ **DO:**
- Store AWS credentials in Render environment variables
- Use IAM user with minimal permissions
- Rotate credentials periodically
- Use different credentials for dev/prod

❌ **DON'T:**
- Commit credentials to Git
- Use root AWS credentials
- Share credentials between apps
- Store credentials in Dockerfile

### S3 Bucket Security

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:user/papl-app-user"
      },
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::papl-digital-first/*"
    }
  ]
}
```

---

## 📈 Monitoring & Logs

### Viewing Logs

**Render Dashboard:**
1. Select service: `papl-comparison-tool`
2. Click **Logs** tab
3. Filter by: Error, Warning, Info

**Useful log patterns:**
```bash
# Successful startup
Streamlit running on: http://0.0.0.0:8501

# S3 feedback saved
Feedback saved to S3: feedback/papl-comparison/feedback_20241203_143025.json

# Errors to watch for
ModuleNotFoundError
boto3.exceptions
StreamlitError
```

### Health Checks

Render automatically checks: `https://your-app.onrender.com`

Expected response: 200 OK (Streamlit loads)

---

## 🔄 Continuous Deployment

### Auto-Deploy on Git Push

**Setup (already configured):**
1. Render Dashboard → Settings
2. Auto-Deploy: **Yes**
3. Branch: `main`

**Workflow:**
```bash
# Local development
git add .
git commit -m "Update app"
git push origin main

# Render automatically:
1. Detects push
2. Pulls latest code
3. Rebuilds Docker image
4. Deploys new version
5. ~3-5 minutes total
```

### Manual Deploy

If auto-deploy disabled:
1. Render Dashboard
2. Manual Deploy → Deploy latest commit

---

## 📝 Key Differences: Local vs Render

| Aspect | Local Development | Render Production |
|--------|-------------------|-------------------|
| **Environment** | docker-compose | Render managed |
| **Port** | localhost:8503 | HTTPS public URL |
| **Environment vars** | `.env` file | Render dashboard |
| **Feedback storage** | Session state | S3 bucket |
| **Build context** | `apps/02-papl-comparison/` | Repo root `./` |
| **Shared modules** | Relative import | Copied to `/app/shared` |
| **Logs** | Terminal output | Render logs UI |
| **SSL** | None | Automatic HTTPS |
| **Scaling** | Single container | Auto-scaling |

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] GitHub repo accessible
- [ ] AWS credentials ready (IAM user)
- [ ] S3 bucket created: `papl-digital-first`
- [ ] IAM policy allows S3 PutObject
- [ ] `upload_feedback` method added to `aws_storage.py`

### Render Configuration
- [ ] Service type: Web Service (Docker)
- [ ] Root directory: `./`
- [ ] Dockerfile path: `./apps/02-papl-comparison/Dockerfile`
- [ ] Docker build context: `./`
- [ ] Environment variables added (AWS + Python)
- [ ] Auto-deploy enabled

### Post-Deployment Testing
- [ ] App loads at public URL
- [ ] Upload documents works
- [ ] Comparison runs successfully
- [ ] Results display correctly
- [ ] Export functionality works
- [ ] Feedback submission works
- [ ] S3 feedback file created
- [ ] No errors in Render logs

### Ongoing
- [ ] Monitor Render logs daily
- [ ] Check S3 feedback folder weekly
- [ ] Review deployment metrics monthly
- [ ] Update dependencies quarterly

---

## 🎯 Success Metrics

**Deployment Success:**
- Build completes in <5 minutes
- No errors in Render logs
- App accessible at public URL
- All features working
- S3 feedback files created

**Production Ready:**
- Uptime: >99.5%
- Response time: <2 seconds
- Error rate: <0.1%
- Successful comparisons: >95%
- Feedback submission rate: >50%

---

## 📚 Additional Resources

**Render Documentation:**
- [Docker Deploys](https://render.com/docs/docker)
- [Environment Variables](https://render.com/docs/environment-variables)
- [Build Configuration](https://render.com/docs/docker#build-time-configuration)

**AWS Documentation:**
- [S3 Bucket Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

**Streamlit:**
- [Deploy Streamlit Apps](https://docs.streamlit.io/knowledge-base/tutorials/deploy)

---

## 🆘 Support

**Issues with deployment?**
1. Check Render logs for specific errors
2. Review troubleshooting section above
3. Verify all environment variables set
4. Test S3 credentials with AWS CLI
5. Compare your Dockerfile with working version above

**Contact:**
- Stuart Smith - stuart.smith@ndis.gov.au
- GitHub: @stu2454
- Repo: https://github.com/stu2454/digital-first-pricing

---

## 📄 Summary

✅ **Render deployment working with:**
- Docker-based build from monorepo
- Shared modules copied from repo root
- S3 feedback storage (no email)
- Automatic HTTPS and scaling
- Environment variables for AWS credentials
- Production-ready configuration

✅ **Ready to deploy!** Follow the steps above for successful Render deployment.

---

*Last Updated: December 2024*  
*Status: Production-Ready*  
*Version: 2.0*
