import os
import multiprocessing

# Importar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

# Número de workers
workers = int(os.getenv('GUNICORN_WORKERS', '1'))

# Classe de worker - sync para compatibilidade com Flask async
worker_class = 'sync'

# Bind - endereço e porta para o servidor
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:5000')

# Timeout em segundos (10 minutos)
timeout = int(os.getenv('GUNICORN_TIMEOUT', '600'))

# Número máximo de requisições antes de reiniciar o worker
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '50'))

# Modo de execução
daemon = False

# Logging
accesslog = os.getenv('GUNICORN_ACCESS_LOG', 'logs/gunicorn_access.log')
errorlog = os.getenv('GUNICORN_ERROR_LOG', 'logs/gunicorn_error.log')
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# Preload aplicação para melhor performance
preload_app = True

# Funções de callback
def on_starting(server):
    print("Iniciando Gunicorn com configuração:")
    print(f"- Workers: {workers}")
    print(f"- Worker Class: {worker_class}")
    print(f"- Bind: {bind}")
    print(f"- Timeout: {timeout}s")

def post_fork(server, worker):
    print(f"Worker {worker.pid} inicializado") 