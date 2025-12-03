# AWS Setup Guide

Complete guide to setting up AWS infrastructure for PAPL Digital First demonstration.

---

## 🎯 Overview

You'll need:
1. AWS Account with your credentials
2. S3 bucket for document storage
3. Bedrock access for Claude & Titan embeddings
4. OpenSearch Serverless (optional, for full RAG)

---

## 📋 Step 1: AWS Credentials

### Get Your Credentials

1. **Log into AWS Console:** https://console.aws.amazon.com
2. **Navigate to IAM** → Users → Your User
3. **Security Credentials** tab
4. **Create Access Key** → "Application running outside AWS"
5. **Download CSV** or copy:
   - Access Key ID (starts with AKIA...)
   - Secret Access Key (only shown once!)

### Configure Locally

**Option A: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-southeast-2
```

**Option B: .env File** (Recommended)
```bash
cd papl-digital-first
cp .env.example .env
# Edit .env with your credentials
```

**Option C: AWS CLI Config**
```bash
aws configure
# Follow prompts
```

---

## 📦 Step 2: Create S3 Bucket

### Via AWS Console

1. **Go to S3:** https://s3.console.aws.amazon.com
2. **Create Bucket**
3. **Settings:**
   - Name: `papl-digital-first` (or your preferred name)
   - Region: `ap-southeast-2` (Sydney) or your region
   - Block all public access: ✅ (keep private)
   - Versioning: Optional (recommended for demos)
   - Encryption: Server-side (default)
4. **Create**

### Via CLI

```bash
aws s3 mb s3://papl-digital-first --region ap-southeast-2
```

### Test Access

```python
import boto3

s3 = boto3.client('s3')
s3.list_buckets()
# Should see your bucket in the list
```

---

## 🔐 Step 3: IAM Permissions

### Required Permissions

Your IAM user/role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::papl-digital-first",
        "arn:aws:s3:::papl-digital-first/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:ap-southeast-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.titan-embed-text-v2:0"
      ]
    }
  ]
}
```

### Apply Policy

1. **IAM Console** → Users → Your User
2. **Permissions** tab → Add Permissions
3. **Attach policies directly** or **Create inline policy**
4. Paste JSON above (update bucket name if different)
5. **Add permissions**

---

## 🤖 Step 4: Enable Bedrock Access

### Request Model Access

1. **Bedrock Console:** https://console.aws.amazon.com/bedrock
2. **Model Access** (left sidebar)
3. **Request access for:**
   - ✅ Claude 3.5 Sonnet v2
   - ✅ Titan Embeddings V2
4. **Submit** (usually instant approval for AWS accounts)

### Verify Access

```python
import boto3

bedrock = boto3.client('bedrock-runtime', region_name='ap-southeast-2')

# Test Claude
response = bedrock.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body='{"messages":[{"role":"user","content":"Hello"}],"max_tokens":100,"anthropic_version":"bedrock-2023-05-31"}'
)
print("Bedrock access confirmed!")
```

---

## 🔍 Step 5: OpenSearch Setup (Optional - For Full RAG)

### Create OpenSearch Serverless Collection

1. **OpenSearch Console:** https://console.aws.amazon.com/opensearch
2. **Collections** → **Create collection**
3. **Settings:**
   - Name: `papl-documents`
   - Type: **Vectorsearch**
   - Deployment: Serverless
4. **Access:**
   - Data access policy: Allow your IAM user
5. **Create**

### Get Endpoint

After creation (takes ~5-10 minutes):
- Copy the endpoint URL
- Add to `.env`:
  ```
  OPENSEARCH_ENDPOINT=https://xxx.us-east-1.aoss.amazonaws.com
  ```

### Note on Cost

OpenSearch Serverless has minimum costs (~$85/month).  
**For demo:** You can skip OpenSearch and use in-memory search initially.

---

## ✅ Step 6: Verify Complete Setup

### Test Script

```python
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# Test 1: S3 Access
print("Testing S3 access...")
s3 = boto3.client('s3')
buckets = s3.list_buckets()
bucket_names = [b['Name'] for b in buckets['Buckets']]
assert os.getenv('S3_BUCKET_NAME') in bucket_names
print("✅ S3 access confirmed")

# Test 2: Bedrock Access
print("\nTesting Bedrock access...")
bedrock = boto3.client('bedrock-runtime', region_name='ap-southeast-2')
response = bedrock.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body='{"messages":[{"role":"user","content":"Test"}],"max_tokens":10,"anthropic_version":"bedrock-2023-05-31"}'
)
print("✅ Bedrock access confirmed")

# Test 3: Upload test file
print("\nTesting S3 upload...")
s3.put_object(
    Bucket=os.getenv('S3_BUCKET_NAME'),
    Key='test/test.txt',
    Body=b'Hello from PAPL Digital First!'
)
print("✅ S3 upload confirmed")

# Test 4: Download test file
print("\nTesting S3 download...")
response = s3.get_object(
    Bucket=os.getenv('S3_BUCKET_NAME'),
    Key='test/test.txt'
)
content = response['Body'].read()
assert content == b'Hello from PAPL Digital First!'
print("✅ S3 download confirmed")

# Cleanup
s3.delete_object(
    Bucket=os.getenv('S3_BUCKET_NAME'),
    Key='test/test.txt'
)

print("\n🎉 All AWS services configured correctly!")
```

Save as `verify_aws_setup.py` and run:
```bash
python verify_aws_setup.py
```

---

## 💰 Cost Estimates (Demo Usage)

### S3 Storage
- First 50 TB: $0.023 per GB/month
- Your use: ~1 GB = **$0.02/month**

### Bedrock (Pay per use)
- Claude 3.5 Sonnet: $3 per 1M input tokens, $15 per 1M output
- Titan Embeddings: $0.0001 per 1K tokens
- Demo usage (1000 queries): **~$5-10/month**

### OpenSearch Serverless (Optional)
- Minimum: 2 OCUs × 24 hours
- Cost: **~$85/month minimum**
- **Recommendation:** Skip for demo, use in-memory search

**Total Demo Cost: ~$5-10/month** (without OpenSearch)

---

## 🔒 Security Best Practices

### Do's
✅ Use environment variables for credentials  
✅ Keep S3 bucket private (block public access)  
✅ Use least-privilege IAM policies  
✅ Enable S3 versioning for important data  
✅ Rotate access keys periodically  

### Don'ts
❌ Never commit credentials to git  
❌ Don't use root account credentials  
❌ Don't make S3 bucket public  
❌ Don't share access keys via email  
❌ Don't use overly permissive policies  

---

## 🆘 Troubleshooting

### Issue: "InvalidAccessKeyId"

**Cause:** Wrong credentials or not set

**Fix:**
```bash
# Check environment
echo $AWS_ACCESS_KEY_ID
# Should show AKIA...

# Re-export or check .env file
```

### Issue: "Access Denied" on S3

**Cause:** IAM permissions missing

**Fix:**
- Check IAM policy includes S3 permissions
- Verify bucket name matches
- Check region matches

### Issue: "Model not found" in Bedrock

**Cause:** Model access not requested

**Fix:**
- Go to Bedrock Console → Model Access
- Request access to required models
- Wait for approval (usually instant)

### Issue: Rate limits

**Cause:** Too many requests

**Fix:**
- Add delays between requests
- Use exponential backoff
- Check Bedrock quotas in AWS Console

---

## 📞 Support

**AWS Documentation:**
- S3: https://docs.aws.amazon.com/s3/
- Bedrock: https://docs.aws.amazon.com/bedrock/
- OpenSearch: https://docs.aws.amazon.com/opensearch-service/

**Project Support:**
- Email: stuart.smith@ndis.gov.au
- GitHub Issues: github.com/stu2454/papl-digital-first

---

## ✅ Setup Checklist

- [ ] AWS account created
- [ ] Access keys generated
- [ ] Credentials configured locally (.env file)
- [ ] S3 bucket created
- [ ] IAM permissions configured
- [ ] Bedrock model access granted
- [ ] Test script run successfully
- [ ] OpenSearch created (optional)

**Once all checked, you're ready to build the apps!** 🚀
