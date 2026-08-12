import json
import base64
from django.shortcuts import redirect
from django.http import JsonResponse


class ClerkAuthenticationMiddleware:
    """
    Middleware that enforces Clerk authentication:
    1. Attaches request.clerk_user_id to incoming requests.
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
        
        request.clerk_user_id = None
        if session_token and '.' in session_token:
            try:
                parts = session_token.split('.')
                if len(parts) >= 2:
                    payload_b64 = parts[1]
                    padded = payload_b64 + '=' * (-len(payload_b64) % 4)
                    decoded_bytes = base64.urlsafe_b64decode(padded)
                    payload = json.loads(decoded_bytes.decode('utf-8'))
                    request.clerk_user_id = payload.get('sub')
            except Exception:
                pass

        # Route Protection Logic
        path = request.path
        is_exempt = any(path == p or path.startswith('/static/') or path.startswith('/media/') or path.startswith('/admin/') for p in self.EXEMPT_PATHS)

        if not is_exempt and not request.clerk_user_id:
            # If AJAX or API request, return HTTP 401 Unauthorized
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or path.startswith('/api/'):
                return JsonResponse({'error': 'Authentication required'}, status=401)
            # Redirect unauthenticated guests to landing page with auto-sign-in trigger
            return redirect('/?sign_in=true')

        return self.get_response(request)
