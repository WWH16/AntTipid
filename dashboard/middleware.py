import json
import base64


class ClerkAuthenticationMiddleware:
    """
    Middleware that reads the Clerk __session cookie or Authorization Bearer token
    and attaches request.clerk_user_id to incoming Django requests.
    Uses standard library base64 & json decoding (no external jwt library dependency required).
    """
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

        return self.get_response(request)
