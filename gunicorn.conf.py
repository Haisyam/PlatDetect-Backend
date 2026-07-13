# Configuration file for Gunicorn in aaPanel
# Place this in the root of your backend project directory

bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
keepalive = 2
