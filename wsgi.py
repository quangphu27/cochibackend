"""WSGI entry for Gunicorn: gunicorn wsgi:app"""
from app import app as application

app = application