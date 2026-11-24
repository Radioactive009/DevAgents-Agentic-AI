# DevAgents AGI — Complete Cloud Deployment Guide
**Requirement 11: Cloud Deployment & Containerization**

This guide provides end-to-end instructions for deploying DevAgents AGI to the cloud.

---

## 🚀 Deployment Options Summary

| Platform | Difficulty | Cost | Best For | Link/URL Type |
|---|---|---|---|---|
| **Option 1: Streamlit Community Cloud** | ⭐ Super Easy (2 mins) | 100% Free | Live demos, presentation to professor | `https://devagents.streamlit.app` |
| **Option 2: Google Cloud Platform (Cloud Run)** | ⭐⭐ Easy (5 mins) | Free Tier Eligible | Enterprise GCP, Google ADK showcase | `https://devagents-xyz.a.run.app` |
| **Option 3: Render / Railway** | ⭐ Easy (3 mins) | Free Tier Eligible | Zero-config Docker hosting | `https://devagents.onrender.com` |
| **Option 4: Microsoft Azure (Container Apps)** | ⭐⭐ Medium | Pay as you go | Azure enterprise deployment | `https://devagents.azurecontainerapps.io` |
| **Option 5: Amazon Web Services (AWS App Runner)** | ⭐⭐ Medium | Free Tier Eligible | AWS container hosting | `https://xyz.awsapprunner.com` |

---

## 🌟 Option 1: Streamlit Community Cloud (The Fastest & Free 1-Click Method)

Streamlit provides free cloud hosting directly from GitHub. This is the simplest way to give your professor a live public link.

### Step 1: Push latest code to GitHub
Make sure your GitHub repository is updated:
```bash
git add .
git commit -m "feat: complete full standardization and streamlit frontend"
git push origin main
```

### Step 2: Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
2. Click **"New app"**.
3. Select your repository: `Radioactive009/DevAgents-Agentic-AI`
4. Set **Branch**: `main`
5. Set **Main file path**: `app_streamlit.py`
6. Click **"Advanced settings"** -> **Secrets**, and paste your API key:
   ```toml
   GROQ_API_KEY = "your-groq-api-key-here"
   ```
7. Click **"Deploy!"**.
8. Within 2 minutes, your project is live with a public HTTPS link!

---

## ☁️ Option 2: Google Cloud Run (Recommended for Google ADK / GCP)

Google Cloud Run runs your container in a fully managed serverless environment with automatic HTTPS and scale-to-zero.

### Prerequisites:
- Google Cloud SDK (`gcloud`) installed, or run directly from the GCP Web Console Cloud Shell.
- A GCP project created.

### Step-by-Step Command Line Deployment:

1. **Log in and configure your project:**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_GCP_PROJECT_ID
   ```

2. **Enable necessary GCP APIs:**
   ```bash
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
   ```

3. **Build and deploy directly from source:**
   ```bash
   gcloud run deploy devagents-agi \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8501 \
     --set-env-vars GROQ_API_KEY="your-groq-api-key-here"
   ```

4. **Done!** Cloud Run will output a public Service URL, such as:
   `https://devagents-agi-6a84c2b9a-uc.a.run.app`

---

## 🐳 Option 3: Local or Server Docker Deployment

If you want to run the containerized system locally or on any Linux VPS:

### Using Docker Compose:
```bash
# 1. Ensure your .env has GROQ_API_KEY set
# 2. Build and start the container
docker compose up --build -d

# 3. View logs
docker compose logs -f

# 4. Open in browser:
# Streamlit App: http://localhost:8501
# Dashboard:     http://localhost:8080
```

### Using Plain Docker Commands:
```bash
# Build image
docker build -t devagents-agi:latest .

# Run container
docker run -d -p 8501:8501 -e GROQ_API_KEY="your-key" --name devagents devagents-agi:latest
```

---

## 🛡️ Option 4: Microsoft Azure (Azure Container Apps)

1. **Install Azure CLI and login:**
   ```bash
   az login
   ```
2. **Create a resource group and container environment:**
   ```bash
   az group create --name devagents-rg --location eastus
   az containerapp env create --name devagents-env --resource-group devagents-rg --location eastus
   ```
3. **Deploy from source:**
   ```bash
   az containerapp up \
     --name devagents-app \
     --resource-group devagents-rg \
     --environment devagents-env \
     --source . \
     --ingress external \
     --target-port 8501 \
     --env-vars GROQ_API_KEY="your-groq-api-key"
   ```

---

## 📦 Option 5: Amazon Web Services (AWS App Runner)

1. Push your container image to **Amazon ECR** (Elastic Container Registry).
2. Go to AWS App Runner Console -> **Create Service**.
3. Select **Container image** -> Choose your ECR image.
4. Set Port to `8501`.
5. Under Environment Variables, add `GROQ_API_KEY`.
6. Click **Deploy**. AWS provides an automatic `.awsapprunner.com` SSL domain.
