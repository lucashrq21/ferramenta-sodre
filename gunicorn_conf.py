import os
import multiprocessing

# Importar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

# Número de workers - padrão para 1 worker por ambiente ASGI
workers = int(os.getenv('GUNICORN_WORKERS', '1'))

# Classe de worker para Uvicorn
worker_class = 'uvicorn.workers.UvicornWorker'

# Bind - endereço e porta para o servidor
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:5000')

# Timeout em segundos (padrão é 30, mas aumentamos para operações mais longas)
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))

# Número máximo de requisições antes de reiniciar o worker
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '50'))

# Modo de execução
daemon = False  # Melhor deixar False e usar systemd para gerenciar

# Logging
accesslog = os.getenv('GUNICORN_ACCESS_LOG', 'logs/gunicorn_access.log')
errorlog = os.getenv('GUNICORN_ERROR_LOG', 'logs/gunicorn_error.log')
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# Preload aplicação para melhor performance
preload_app = True

# Hooks para processamento de inicialização/finalização
def on_starting(server):
    print("Iniciando Gunicorn com configuração:")
    print(f"- Workers: {workers}")
    print(f"- Worker Class: {worker_class}")
    print(f"- Bind: {bind}")
    print(f"- Timeout: {timeout}s")
    print(f"- Max Requests: {max_requests} (±{max_requests_jitter})")

def on_exit(server):
    print("Encerrando Gunicorn")

def post_fork(server, worker):
    print(f"Worker {worker.pid} inicializado") 