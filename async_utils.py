import asyncio
import functools
import concurrent.futures
import os
from typing import Any, Callable, TypeVar, Coroutine
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar o logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/async_utils.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("async_utils")

# Pegar MAX_WORKERS do ambiente, ou usar um valor padrão
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '20'))

# Criar um executor global de threads
executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)
logger.info(f"ThreadPoolExecutor inicializado com {MAX_WORKERS} workers")

# Tipos genéricos para as funções
T = TypeVar('T')

def run_blocking_func(func: Callable[..., T], *args, **kwargs) -> Coroutine[Any, Any, T]:
    """
    Executa uma função bloqueante em um thread separado usando o ThreadPoolExecutor.
    
    Args:
        func: A função bloqueante a ser executada
        *args: Argumentos posicionais para a função
        **kwargs: Argumentos nomeados para a função
        
    Returns:
        Coroutine que pode ser aguardada com await
    """
    return asyncio.get_event_loop().run_in_executor(
        executor,
        functools.partial(func, *args, **kwargs)
    )

async def run_with_timeout(coro: Coroutine[Any, Any, T], timeout: float = 10.0) -> T:
    """
    Executa uma coroutine com um timeout.
    
    Args:
        coro: A coroutine a ser executada
        timeout: Tempo máximo de espera em segundos
        
    Returns:
        O resultado da coroutine
        
    Raises:
        asyncio.TimeoutError: Se a coroutine não completar dentro do timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Timeout de {timeout}s excedido ao executar coroutine")
        raise
    except Exception as e:
        logger.error(f"Erro ao executar coroutine: {str(e)}")
        raise

def cleanup():
    """
    Função para limpar recursos ao encerrar a aplicação.
    """
    try:
        logger.info("Encerrando ThreadPoolExecutor...")
        executor.shutdown(wait=True)
        logger.info("ThreadPoolExecutor encerrado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao encerrar ThreadPoolExecutor: {str(e)}") 