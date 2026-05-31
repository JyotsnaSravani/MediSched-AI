"""
Django settings for MediSched AI project.
Sprint 1 - Core Infrastructure & Data Management
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config
import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('DJANGO_SECRET_KEY', default='dev-secret-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'daphne',  # ASGI server for Channels (must be first)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'channels',
    
    # Local apps (Sprint 1)
    'config',  # For management commands
    'users',
    'patients',
    'doctors',
    
    # Local apps (Sprint 2+)
    'scheduling',
    'calling',
    'transcriptions',
    'reminders',
    'analytics',
    'realtime',
    'sms',  # SMS messaging
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.DatabaseConnectionMiddleware',  # Close DB connections after each request
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Add templates directory
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

# ASGI application (for Channels WebSocket support)
ASGI_APPLICATION = 'config.asgi.application'

# Database - PostgreSQL ONLY
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgresql://postgres:Teja@123@localhost:5432/medisched_db'),
        conn_max_age=60,  # Reduced from 600 to 60 seconds - more aggressive recycling
        conn_health_checks=True,  # Enable connection health checks
    )
}

# Database Connection Pooling Configuration
# Prevents "too many clients" error by limiting and reusing connections
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
    'options': '-c statement_timeout=30000',  # 30 second query timeout
}

# Set maximum connections per worker - AGGRESSIVE SETTINGS
DATABASES['default']['CONN_MAX_AGE'] = 60  # 1 minute (reduced from 10 minutes)
DATABASES['default']['ATOMIC_REQUESTS'] = True  # Wrap each request in a transaction
DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True  # Prevent cursor leaks

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Authentication Backends (Required for email login)
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default backend for email authentication
]

# Password validation
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Add static directory for custom admin files
]

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_TOKEN_LIFETIME', default=15, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=config('JWT_REFRESH_TOKEN_LIFETIME', default=10080, cast=int)),  # 7 days
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True  # Enabled for development
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Celery Configuration
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Celery Queues (Sprint 3+)
# Disabled for now - using default queue for all tasks
# CELERY_TASK_ROUTES = {
#     'calling.tasks.*': {'queue': 'calling_queue'},
#     'calling.auto_calling.*': {'queue': 'calling_queue'},
#     'transcriptions.tasks.*': {'queue': 'transcription_queue'},
#     'reminders.tasks.*': {'queue': 'reminder_queue'},
# }

# Celery Beat Schedule (Automatic Tasks)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Send appointment reminders every hour
    'send-appointment-reminders': {
        'task': 'calling.auto_calling.send_appointment_reminders',
        'schedule': crontab(minute=0),  # Every hour at :00
    },
    # Send appointment confirmations daily at 9 AM
    'send-appointment-confirmations': {
        'task': 'calling.auto_calling.send_appointment_confirmations',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9:00 AM
    },
    # Send follow-up calls daily at 10 AM
    'send-follow-up-calls': {
        'task': 'calling.auto_calling.send_follow_up_calls',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10:00 AM
    },
    # Offer slots to waitlist every 30 minutes
    'offer-slots-to-waitlist': {
        'task': 'calling.auto_calling.offer_slots_to_waitlist',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    # Cleanup old logs weekly on Sunday at 2 AM
    'cleanup-old-call-logs': {
        'task': 'calling.auto_calling.cleanup_old_call_logs',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2:00 AM
    },
}

# Twilio Configuration (Sprint 3)
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')

# Conversational AI Configuration
USE_CONVERSATIONAL_AI = config('USE_CONVERSATIONAL_AI', default=True, cast=bool)

# Real-Time AI Configuration (GPT-Realtime-2 + GPT-5.5 + GPT-Realtime-Whisper)
USE_REALTIME_AI = config('USE_REALTIME_AI', default=False, cast=bool)
AI_REASONING_LEVEL = config('AI_REASONING_LEVEL', default=3, cast=int)

# AI Voice Settings (for natural conversation)
AI_TEMPERATURE = config('AI_TEMPERATURE', default=0.9, cast=float)
AI_MAX_TOKENS = config('AI_MAX_TOKENS', default=60, cast=int)
AI_VAD_THRESHOLD = config('AI_VAD_THRESHOLD', default=0.4, cast=float)
AI_SILENCE_DURATION = config('AI_SILENCE_DURATION', default=700, cast=int)

# Speech Recognition Settings (Twilio) - OPTIMIZED FOR FAST RESPONSE
SPEECH_TIMEOUT = config('SPEECH_TIMEOUT', default=2, cast=int)  # How long to wait for patient to start speaking
SPEECH_TIMEOUT_MODE = config('SPEECH_TIMEOUT_MODE', default='auto')  # 'auto' or number of seconds
ENABLE_BARGE_IN = config('ENABLE_BARGE_IN', default=True, cast=bool)  # Allow patient to interrupt AI

# OpenAI Configuration (Sprint 3 - Whisper API)
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Site URL for webhooks
SITE_URL = config('SITE_URL', default='http://127.0.0.1:8000')

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Medshield AI <noreply@medshield.com>')
SERVER_EMAIL = config('SERVER_EMAIL', default='server@medshield.com')
EMAIL_TIMEOUT = 10  # seconds

# Django Channels Configuration (Real-Time AI with GPT-Realtime-2)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [config('REDIS_URL', default='redis://localhost:6379/0')],
            "capacity": 1500,  # Max messages in channel
            "expiry": 3600,  # Message expiry (1 hour)
        },
    },
}

# WebSocket Configuration (prevent call disconnections)
ASGI_APPLICATION_TIMEOUT = 3600  # 1 hour timeout for long calls
WEBSOCKET_ACCEPT_ALL = True
WEBSOCKET_TIMEOUT = 3600  # 1 hour WebSocket timeout

# API Documentation (drf-spectacular)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Medshield AI API',
    'DESCRIPTION': 'AI-powered appointment scheduling and patient engagement platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Security Settings (NFR-S-01, NFR-S-03, NFR-S-05)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# Session Configuration (NFR-S-03: 30-minute inactivity timeout)
SESSION_COOKIE_AGE = 1800  # 30 minutes in seconds
SESSION_SAVE_EVERY_REQUEST = True
