"""
Documentação do módulo limiter.py.

O que faz: Implementa a lógica estrutural e funcional para o módulo core/base limiter.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o módulo core/base limiter funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
