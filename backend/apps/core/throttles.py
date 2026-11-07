import hashlib
from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "")).strip().lower()
        ident = hashlib.sha256(f"{self.get_ident(request)}:{email}".encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}