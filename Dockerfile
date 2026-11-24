# ==============================================================================
# DevAgents AGI - Production Docker Container
# Requirement 11: Cloud Deployment & Containerization
# Supports: GCP Cloud Run, AWS ECS, Azure Container Apps, or Local Docker
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8501

WORKDIR /app

# Install essential build tools, curl (for healthcheck), and git
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all project source code and assets
COPY . .

# Ensure data and logs directories exist
RUN mkdir -p logs generated_projects data

# Expose ports: 8501 (Streamlit Frontend) and 8080 (Architecture Dashboard)
EXPOSE 8501 8080

# Health check to ensure the application server is responsive
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/_stcore/health || exit 1

# Launch the Streamlit application by default
CMD streamlit run app_streamlit.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
