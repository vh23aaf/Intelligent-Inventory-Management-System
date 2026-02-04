"""
Custom middleware for handling proxy headers and CSRF in development.
"""


class ForwardedProtoMiddleware:
    """
    Middleware to handle X-Forwarded-Proto header from reverse proxies.
    This allows proper CSRF validation when running behind a proxy with HTTPS.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check for X-Forwarded-Proto header
        if 'HTTP_X_FORWARDED_PROTO' in request.META:
            if request.META['HTTP_X_FORWARDED_PROTO'].lower() == 'https':
                request.META['wsgi.url_scheme'] = 'https'
                request.is_secure = lambda: True

        response = self.get_response(request)
        return response
