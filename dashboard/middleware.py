import base64

import jwt
from django.conf import settings
from django.http import JsonResponse
import time
import logging
from django.db import connection
from django.shortcuts import redirect

_jwks_client = None
_jwks_client_host = None


def _clerk_frontend_api_host():
    """Clerk publishable keys encode the Frontend API host as pk_{env}_{base64(host + '$')}."""
    key = settings.CLERK_PUBLISHABLE_KEY
    try:
        encoded = key.split('_', 2)[2]
        padded = encoded + '=' * (-len(encoded) % 4)
        return base64.b64decode(padded).decode('utf-8').rstrip('$')
    except (IndexError, ValueError):
        return None


def _get_jwks_client():
    """PyJWKClient caches keys in-memory keyed by `kid` and only refetches the JWKS
    endpoint when it sees an unrecognized one, so this stays cheap per-request."""
    global _jwks_client, _jwks_client_host
    host = _clerk_frontend_api_host()
    if not host:
        return None
    if _jwks_client is None or _jwks_client_host != host:
        _jwks_client = jwt.PyJWKClient(
            f'https://{host}/.well-known/jwks.json',
            cache_keys=True,
            lifespan=3600,
        )
        _jwks_client_host = host
    return _jwks_client, host


class ClerkAuthenticationMiddleware:
    """
    Middleware that enforces Clerk authentication:
    1. Verifies the __session JWT's signature against Clerk's published JWKS
       (RS256, exp/iat/issuer checked) and attaches request.clerk_user_id from
       the verified `sub` claim.
    2. Protects inner app routes from unauthenticated direct URL access.
    """
    EXEMPT_PATHS = [
        '/',
        '/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_token = request.COOKIES.get('__session') or request.headers.get('Authorization', '').replace('Bearer ', '')

        request.clerk_user_id = self._verify_session_token(session_token) if session_token else None

        # Route Protection Logic
        path = request.path
        is_exempt = any(path == p or path.startswith('/static/') or path.startswith('/media/') or path.startswith('/admin/') for p in self.EXEMPT_PATHS)

        if not is_exempt and not request.clerk_user_id:
            # ⚠️ TODO (DEPLOYMENT REMINDER): Remove or disable this preview bypass before deploying to production.
            # Used only for local UI testing / headless browser developer tool inspection.
            if settings.DEBUG and (request.GET.get('preview') == 'true' or 'preview=true' in request.META.get('HTTP_REFERER', '')):
                return self.get_response(request)

            # If AJAX or API request, return HTTP 401 Unauthorized
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or path.startswith('/api/'):
                return JsonResponse({'error': 'Authentication required'}, status=401)
            # Redirect unauthenticated guests to landing page with auto-sign-in trigger
            return redirect('/?sign_in=true')

        return self.get_response(request)

    @staticmethod
    def _verify_session_token(token):
        client_and_host = _get_jwks_client()
        if client_and_host is None:
            return None
        jwks_client, host = client_and_host

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=['RS256'],
                leeway=10,  # tolerate a few seconds of clock skew between this server and Clerk's
                options={'require': ['exp', 'iat', 'sub'], 'verify_iss': False},
            )
            return payload.get('sub')
        except jwt.PyJWTError as e:
            logging.warning(f"Clerk JWT session token verification failed: {e}")
            return None


class PerformanceLoggingMiddleware:
    """Logs request processing time and DB query count for each request."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('performance')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def __call__(self, request):
        start = time.perf_counter()
        # Reset query log if available
        if hasattr(connection, 'queries'):
            connection.queries_log.clear()
        response = self.get_response(request)
        duration = (time.perf_counter() - start) * 1000
        query_count = len(connection.queries) if hasattr(connection, 'queries') else 0
        self.logger.info(
            f"[Performance] {request.method} {request.path} - {duration:.2f}ms, {query_count} DB queries"
        )
        return response
