#!/usr/bin/env bash
set -o errexit

# Instalar dependencias de Python desde requirements.txt
pip install -r requirements.txt

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Ejecutar migraciones de la base de datos
# Render inyectará la DATABASE_URL, así que este comando funcionará con PostgreSQL
python manage.py migrate
