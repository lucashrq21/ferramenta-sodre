import json
import time
import hashlib
import logging
from typing import Any, Dict, Optional, Tuple, List, Union
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/cache.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cache_utils")

class CacheManager:
    """
    Classe para gerenciar cache de dados, com suporte para operações com e sem Redis.
    Quando Redis não estiver disponível, usa cache em memória.
    """
    
    def __init__(self, app=None):
        """
        Inicializa o gerenciador de cache.
        
        Args:
            app: Instância do Flask (opcional, pode ser inicializada posteriormente)
        """
        self.redis_client = None
        self.memory_cache = {}
        self.ttl_info = {}  # Para armazenar TTLs quando usando cache em memória
        
        if app is not None:
            self.init_app(app)
        else:
            # Tentar inicializar Redis mesmo sem app Flask
            self._initialize_redis()
            
        logger.info("CacheManager inicializado")
    
    def init_app(self, app):
        """
        Inicializa o cache com uma aplicação Flask.
        
        Args:
            app: Instância do Flask
        """
        self.app = app
        self._initialize_redis()
    
    def _initialize_redis(self):
        """
        Inicializa a conexão com Redis, se disponível.
        """
        redis_url = os.getenv('CACHE_REDIS_URL')
        
        if not redis_url:
            logger.warning("CACHE_REDIS_URL não configurado, usando cache em memória")
            return
        
        try:
            import redis
            self.redis_client = redis.from_url(redis_url)
            # Testar a conexão
            self.redis_client.ping()
            logger.info(f"Conexão com Redis estabelecida: {redis_url}")
        except ImportError:
            logger.warning("Pacote 'redis' não encontrado, usando cache em memória")
        except Exception as e:
            logger.error(f"Erro ao conectar ao Redis: {str(e)}, usando cache em memória")
            self.redis_client = None
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Gera uma chave de cache consistente baseada nos argumentos.
        
        Args:
            prefix: Prefixo para a chave (ex: nome da função)
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados
            
        Returns:
            str: Chave de cache
        """
        # Criar uma representação dos argumentos
        key_parts = [prefix]
        
        # Adicionar args
        for arg in args:
            if isinstance(arg, (str, int, float, bool, type(None))):
                key_parts.append(str(arg))
            else:
                # Para objetos complexos, usar seu hash em vez de str completo
                try:
                    key_parts.append(str(hash(arg)))
                except:
                    key_parts.append(str(id(arg)))
        
        # Adicionar kwargs (ordenados por chave para consistência)
        for k in sorted(kwargs.keys()):
            v = kwargs[k]
            key_parts.append(f"{k}={v}")
        
        # Criar um hash MD5 da string combinada para ter um tamanho fixo
        combined = ":".join(key_parts)
        hashed = hashlib.md5(combined.encode()).hexdigest()
        
        return f"{prefix}:{hashed}"
    
    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """
        Armazena um valor no cache.
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado
            ttl: Tempo de vida em segundos
            
        Returns:
            bool: True se armazenado com sucesso, False caso contrário
        """
        try:
            # Serializar o valor para JSON
            serialized = json.dumps(value)
            
            if self.redis_client:
                return self.redis_client.setex(key, ttl, serialized)
            else:
                # Cache em memória com TTL
                self.memory_cache[key] = serialized
                self.ttl_info[key] = (time.time() + ttl, ttl)
                return True
        except Exception as e:
            logger.error(f"Erro ao armazenar no cache: {str(e)}")
            return False
    
    def get(self, key: str) -> Tuple[bool, Any]:
        """
        Recupera um valor do cache.
        
        Args:
            key: Chave do cache
            
        Returns:
            tuple: (hit, value) onde hit é True se encontrado, e value é o valor ou None
        """
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return True, json.loads(value)
                return False, None
            else:
                # Verificar expiração para cache em memória
                if key in self.memory_cache:
                    expiry_time, _ = self.ttl_info.get(key, (0, 0))
                    if time.time() < expiry_time:
                        return True, json.loads(self.memory_cache[key])
                    else:
                        # Remover item expirado
                        del self.memory_cache[key]
                        del self.ttl_info[key]
                return False, None
        except Exception as e:
            logger.error(f"Erro ao recuperar do cache: {str(e)}")
            return False, None
    
    def delete(self, key: str) -> bool:
        """
        Remove um valor do cache.
        
        Args:
            key: Chave do cache
            
        Returns:
            bool: True se removido com sucesso, False caso contrário
        """
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    if key in self.ttl_info:
                        del self.ttl_info[key]
                    return True
                return False
        except Exception as e:
            logger.error(f"Erro ao remover do cache: {str(e)}")
            return False
    
    def clear(self, pattern: str = "*") -> bool:
        """
        Limpa o cache com um padrão específico.
        
        Args:
            pattern: Padrão de chaves a serem removidas
            
        Returns:
            bool: True se a operação foi bem-sucedida
        """
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return bool(self.redis_client.delete(*keys))
                return True
            else:
                # Para cache em memória, filtrar chaves que correspondem ao padrão
                pattern = pattern.replace("*", "")  # Simplificação básica
                keys_to_delete = [k for k in self.memory_cache if pattern in k]
                for k in keys_to_delete:
                    del self.memory_cache[k]
                    if k in self.ttl_info:
                        del self.ttl_info[k]
                return True
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {str(e)}")
            return False
    
    def cached(self, prefix: str = None, ttl: int = 60):
        """
        Decorador para cache de função.
        
        Args:
            prefix: Prefixo opcional para a chave de cache
            ttl: Tempo de vida em segundos
            
        Returns:
            Decorator
        """
        def decorator(func):
            func_prefix = prefix or func.__name__
            
            def wrapper(*args, **kwargs):
                # Gerar chave de cache baseada nos argumentos
                cache_key = self._generate_key(func_prefix, *args, **kwargs)
                
                # Tentar obter do cache
                hit, cached_value = self.get(cache_key)
                if hit:
                    logger.debug(f"Cache hit para {func_prefix}")
                    return cached_value
                
                # Executar função se não estiver no cache
                logger.debug(f"Cache miss para {func_prefix}")
                result = func(*args, **kwargs)
                
                # Armazenar resultado no cache
                self.set(cache_key, result, ttl)
                return result
            
            return wrapper
        
        return decorator
    
    def cleanup(self):
        """
        Limpa recursos ao encerrar a aplicação.
        """
        try:
            if self.redis_client:
                self.redis_client.close()
                logger.info("Conexão Redis fechada")
        except Exception as e:
            logger.error(f"Erro ao fechar conexão Redis: {str(e)}")
            
        # Limpar caches em memória
        self.memory_cache.clear()
        self.ttl_info.clear()


# Instância global do gerenciador de cache
cache_manager = CacheManager() 