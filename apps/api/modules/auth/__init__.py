"""Auth module (ADR-014): guest credentials, access tokens, the current principal and
password hashing.

Other modules use only what is exported here.
"""

from modules.auth.activity import LastActivityMiddleware
from modules.auth.dependencies import CurrentPrincipal, Principal, current_principal
from modules.auth.hashing import PasswordHashing, create_hash_executor
from modules.auth.router import router
from modules.auth.service import AuthService
from modules.auth.tokens import TokenService

__all__ = [
    "AuthService",
    "CurrentPrincipal",
    "LastActivityMiddleware",
    "PasswordHashing",
    "Principal",
    "TokenService",
    "create_hash_executor",
    "current_principal",
    "router",
]
