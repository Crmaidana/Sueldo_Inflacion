"""
Django settings for sueldo_inflacion_project project.
"""

from pathlib import Path
import os
from decouple import config
import dj_database_url # Importa dj_database_url si aún no lo está

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Carga la SECRET_KEY de las variables de entorno (preferiblemente de un .env local)
SECRET_KEY = config('DJANGO_SECRET_KEY', default='your-default-secret-key-for-development')

# SECURITY WARNING: don't run with debug turned on in production!
# ¡IMPORTANTE! Carga DEBUG desde el archivo .env.
# Esto permite que sea True en desarrollo y False en Render.
DEBUG = config('DEBUG', default=False, cast=bool)

# Define los hosts permitidos.
# En desarrollo, puede ser localhost/127.0.0.1.
# En producción, será el dominio de Render.com (Render lo inyecta).
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')
# Si tu ALLOWED_HOSTS en .env es una cadena como "host1,host2", split(',') la convierte en lista.


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'comparador',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise Middleware debe ir justo después de SecurityMiddleware
    # y antes de otros middleware de Django.
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sueldo_inflacion_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'comparador' / 'templates'], # Usando Pathlib para unir rutas
        'APP_DIRS': True, 
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sueldo_inflacion_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Configuración de la base de datos dual: MySQL local y PostgreSQL en Render
if DEBUG:
    # Configuración para MySQL en desarrollo local
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME_LOCAL', default='tu_bd_mysql_local'), # Nombre de tu base de datos MySQL local
            'USER': config('DB_USER_LOCAL', default='root'), # Usuario de tu MySQL local
            'PASSWORD': config('DB_PASSWORD_LOCAL', default=''), # Contraseña de tu MySQL local
            'HOST': config('DB_HOST_LOCAL', default='127.0.0.1'), # Host de tu MySQL local (normalmente localhost o 127.0.0.1)
            'PORT': config('DB_PORT_LOCAL', default='3306'), # Puerto de MySQL
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'", # Opcional, si lo necesitas
                'charset': 'utf8mb4',
            }
        }
    }
else:
    # Configuración para PostgreSQL en Render (cuando DEBUG sea False en Render)
    # Render inyectará la variable de entorno DATABASE_URL
    DATABASES = {
        'default': dj_database_url.config(
            default=config('DATABASE_URL') # Esta variable la inyecta Render
        )
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# ESTO DEBE ESTAR SIEMPRE DEFINIDO, FUERA DE CUALQUIER CONDICIONAL DEBUG
STATIC_URL = 'static/'

# Directorio donde Django recolectará todos los archivos estáticos con 'collectstatic'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Directorios adicionales donde Django buscará archivos estáticos durante el desarrollo
STATICFILES_DIRS = [
    #BASE_DIR / 'static', # Si tienes una carpeta 'static' en la raíz del proyecto
    # BASE_DIR / 'comparador' / 'static', # Si tuvieras estáticos de app directamente aquí (menos común con app_name/static/app_name)
]

# Configuración de WhiteNoise para servir archivos estáticos comprimidos y con cache
# Esto se usará tanto en collectstatic como en el servidor de producción.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'