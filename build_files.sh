#!/bin/bash
echo "Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt --break-system-packages

echo "Building Tailwind CSS assets..."
npm install
npm run build:css

echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear
