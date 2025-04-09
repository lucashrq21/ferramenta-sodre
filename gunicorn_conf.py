import os
import multiprocessing

# Bind 
bind = "0.0.0.0:5000"

# Workers - voltando para configuração mais confiável
workers = 1
worker_class = "sync"  # Voltando para sync para compatibilidade
threads = 4

# Timeout mantido alto
timeout = 1200  # 20 minutos
graceful_timeout = 60
keep_alive = 5

# Logging
accesslog = "/var/www/ferramenta-sodre/logs/gunicorn_access.log"
errorlog = "/var/www/ferramenta-sodre/logs/gunicorn_error.log"
loglevel = "info"

# Server
daemon = False
preload_app = True  # Voltando para True
max_requests = 1000
max_requests_jitter = 50
