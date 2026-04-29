# --- Dockerfile (scraper) ---
FROM python:3.11-slim-bullseye

# 1) System libs needed by headless Chrome
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip gnupg ca-certificates \
    libglib2.0-0 libnss3 libasound2 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libxkbcommon0 libxss1 libgtk-3-0 \
 && apt-get upgrade -y \
 && apt-get dist-upgrade -y \
 && rm -rf /var/lib/apt/lists/*

# 2) Allow Selenium Manager to cache Chrome/driver
ENV SE_DOWNLOADS=/opt/selenium
RUN mkdir -p /opt/selenium

# 3) Python deps
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# 4) App
COPY . /app

# 5) FastAPI entry
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
