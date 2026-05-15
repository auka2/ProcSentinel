# ==============================================================================
# ProcSentinel v3 — Memory Forensics Platform
# University of Hail · Graduation Project
# ==============================================================================
#
# BUILD & RUN:
#   docker-compose up --build        (first time)
#   docker-compose up -d             (background after first build)
#   docker-compose down              (stop — always use this, not Ctrl+C alone)
#   docker-compose down && docker-compose up --build   (full rebuild)
#
# ==============================================================================

FROM python:3.11-slim-bookworm

LABEL maintainer="ProcSentinel Team — University of Hail"
LABEL description="Memory forensics platform for masquerade and injection detection"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        git gcc make libssl-dev libffi-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir volatility3

# Application source
COPY app.py          .
COPY runner.py       .
COPY detections.yaml .
COPY baseline.yaml   .

# Runtime directories (memory dumps go in memory/, outputs go in out/)
RUN mkdir -p memory out

# ── Credentials (override in .env or docker-compose environment) ──────────────
ENV PROCSENTINEL_USER=admin
ENV PROCSENTINEL_PASS=procsentinel

# ── AbuseIPDB key — set here OR in .env (safer than CLI argument) ─────────────
ENV ABUSEIPDB_KEY=""

# ── Set to 1 for verbose DEBUG output from runner.py ─────────────────────────
ENV PROCSENTINEL_DEBUG=0

# ── Streamlit ─────────────────────────────────────────────────────────────────
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_THEME_BASE=dark

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
