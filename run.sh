#!/usr/bin/env bash
# Quick start: install deps and launch the dashboard
set -e

echo "==> Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "==> Installing dependencies..."
pip install --quiet -r requirements.txt

echo "==> Installing Playwright browsers..."
playwright install chromium --with-deps

echo "==> Copying .env.example to .env (if not exists)..."
[ -f .env ] || cp .env.example .env

echo "==> Starting JobBot dashboard on http://localhost:5000"
python app.py
