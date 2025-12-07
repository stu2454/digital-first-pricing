# Render Deployment Quick Reference

**App:** PAPL Comparison Tool (App 2)  
**Repo:** github.com/stu2454/digital-first-pricing  
**Status:** ✅ Production-Ready

---

## 🚀 Quick Deploy (5 Minutes)

### 1. Render Configuration

```yaml
Service Type: Web Service (Docker)
Root Directory: ./
Dockerfile Path: ./apps/02-papl-comparison/Dockerfile
Docker Build Context: ./
Auto-Deploy: Yes
Branch: main
```

### 2. Environment Variables

```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=ap-southeast-2
S3_BUCKET_NAME=papl-digital-first
PYTHONPATH=/app:/app/shared
```

### 3. Deploy

Click **Create Web Service** → Wait 3-5 minutes → Done!

---

## 📁 File Structure

```
digital-first-pricing/
├── apps/02-papl-comparison/
│   ├── Dockerfile          ← Render uses this
│   ├── app.py              ← Main app (S3 feedback)
│   └── requirements.txt    ← App dependencies
└── shared/
    ├── aws_storage.py      ← S3 operations + feedback
    ├── papl_parser.py
    ├── semantic_comparer.py
    └── requirements.txt    ← Shared dependencies
```

---

## 🔑 Key Differences: Local vs Render

| | Local | Render |
|---|---|---|
| **Build Context** | `apps/02-papl-comparison/` | `./` (repo root) |
| **Feedback** | Session state | S3 storage |
| **Environment** | `.env` file | Render dashboard |
| **URL** | localhost:8503 | your-app.onrender.com |

---

## 🐳 Dockerfile Key Points

```dockerfile
# Build from repo root, so paths are:
COPY apps/02-papl-comparison /app
COPY shared /app/shared

# Install BOTH requirements
RUN pip install -r /app/requirements.txt
RUN pip install -r /app/shared/requirements.txt

# Streamlit on 8501
ENV STREAMLIT_SERVER_PORT=8501
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

---

## 💾 S3 Feedback Implementation

### In `app.py` (line ~1105):
```python
if storage and storage_initialized:
    s3_key = storage.upload_feedback(feedback_data)
    st.success(f"Feedback saved to S3: {s3_key}")
```

### Add to `shared/aws_storage.py`:
```python
def upload_feedback(self, feedback_data: dict) -> str:
    """Upload feedback to S3"""
    import json
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    s3_key = f"feedback/papl-comparison/feedback_{timestamp}.json"
    
    feedback_json = json.dumps(feedback_data, indent=2)
    
    self.s3_client.put_object(
        Bucket=self.bucket_name,
        Key=s3_key,
        Body=feedback_json,
        ContentType='application/json'
    )
    
    return s3_key
```

### S3 Structure:
```
s3://papl-digital-first/
└── feedback/
    └── papl-comparison/
        ├── feedback_20241203_143025.json
        ├── feedback_20241203_150312.json
        └── feedback_20241204_091544.json
```

---

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| **Can't find app.py** | Root Directory = `./`<br>Dockerfile Path = `./apps/02-papl-comparison/Dockerfile` |
| **ModuleNotFoundError: aws_storage** | Add env var: `PYTHONPATH=/app:/app/shared` |
| **ModuleNotFoundError: boto3** | Verify Dockerfile installs shared requirements |
| **Feedback not saving** | Check AWS credentials in Render dashboard |
| **Build stuck** | Clear build cache in Render settings |

---

## 📊 Testing Checklist

- [ ] App loads at public URL
- [ ] Upload documents works
- [ ] Comparison runs
- [ ] Results display
- [ ] Submit feedback
- [ ] Check S3 for feedback file
- [ ] No errors in Render logs

---

## 📥 Download All Feedback

```bash
# AWS CLI
aws s3 cp s3://papl-digital-first/feedback/papl-comparison/ ./feedback/ --recursive

# Python
import boto3
s3 = boto3.client('s3')
response = s3.list_objects_v2(
    Bucket='papl-digital-first',
    Prefix='feedback/papl-comparison/'
)
```

---

## 🔐 IAM Permissions

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::papl-digital-first/feedback/*",
    "arn:aws:s3:::papl-digital-first"
  ]
}
```

---

## 🎯 Success Indicators

✅ Render build completes <5 min  
✅ App accessible at public URL  
✅ All features working  
✅ Feedback saves to S3  
✅ S3 key shows in success message  
✅ No errors in logs  

---

## 📚 Full Documentation

**Comprehensive Guides:**
- [RENDER_DEPLOYMENT_GUIDE.md](computer:///mnt/user-data/outputs/RENDER_DEPLOYMENT_GUIDE.md) - Complete deployment steps
- [S3_FEEDBACK_IMPLEMENTATION.md](computer:///mnt/user-data/outputs/S3_FEEDBACK_IMPLEMENTATION.md) - S3 feedback details

**Quick Setup:**
This reference card!

---

## 🆘 Quick Help

**Check Render logs:**
Dashboard → Service → Logs

**Test S3 locally:**
```python
from shared.aws_storage import S3Storage
storage = S3Storage()
test = {'timestamp': '2024-12-03', 'test': 'data'}
storage.upload_feedback(test)
```

**Verify environment:**
```bash
# In Render shell
echo $PYTHONPATH
echo $S3_BUCKET_NAME
```

---

**Ready to deploy?** Follow the 3 steps at the top! 🚀

---

*Last Updated: December 2024*  
*Quick Reference for: digital-first-pricing/apps/02-papl-comparison*
