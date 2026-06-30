"""
core/ — Motor de ronda, configuração de NVRs e autenticação.

Não depende do Flask request context.
Operações de banco usam session_scope() para segurança em threads.
"""
