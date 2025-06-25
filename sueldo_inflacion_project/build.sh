#!/usr/bin/env bash
set -o errexit

# Instalar dependencias del sistema operativo para PostgreSQL (Render usa Ubuntu)
# No necesitamos 'sudo' aquí, ya que el entorno de build tiene permisos suficientes.
apt-get update
apt-get install -y libpq-dev

# Instalar dependencias de Python
pip install -r requirements.txt

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Ejecutar migraciones de la base de datos
# Render inyectará la DATABASE_URL, así que este comando funcionará con PostgreSQL
python manage.py migrate
