release: python manage.py migrate
web: gunicorn config.wsgi:application
worker: python manage.py rqworker default

