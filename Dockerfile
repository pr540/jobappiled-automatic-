FROM python:3.11-slim

WORKDIR /app

# System deps for Chrome + Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg unzip fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 \
    libnspr4 libnss3 libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 \
    libxrandr2 xdg-utils libx11-xcb1 libxcb-dri3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

COPY . .

RUN mkdir -p /app/data /app/logs /app/data/browser_profiles

EXPOSE 5000

CMD ["python", "app.py"]
