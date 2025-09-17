#!/bin/bash

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput --clear

echo "Build completed successfully!"