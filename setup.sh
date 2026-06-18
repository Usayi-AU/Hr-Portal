#!/bin/bash
# HR Portal – one-shot initialisation script.
#
# Runs database migrations and then executes the setup_portal management
# command which creates the admin user, auth groups, demo companies,
# employee profiles, and all supporting demo data.
#
# Usage:
#   bash setup.sh
#
# Environment variables (optional):
#   ADMIN_PASSWORD   – password for the "admin" superuser (default: admin123)

set -euo pipefail

cd /app

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Running portal setup (admin user, groups, demo data)..."
python manage.py setup_portal

echo "==> Done."
