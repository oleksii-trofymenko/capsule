"""Auth module (ADR-014): guest credentials, access tokens and the current principal.

Other modules use only what is exported here.
"""

from modules.auth.activity import LastActivityMiddleware
from modules.auth.dependencies import CurrentPrincipal, Principal, current_principal
from modules.auth.router import router
from modules.auth.tokens import TokenService

__all__ = [
    "CurrentPrincipal",
    "LastActivityMiddleware",
    "Principal",
    "TokenService",
    "current_principal",
    "router",
]
