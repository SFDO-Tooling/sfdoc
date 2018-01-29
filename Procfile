release: python manage.py migrate --noinput
web: gunicorn config.wsgi:application
worker: python manage.py rqworker default
