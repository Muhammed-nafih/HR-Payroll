from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.deprecation import MiddlewareMixin
from rest_framework.exceptions import AuthenticationFailed

class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if 'Authorization' in request.headers:
            auth = JWTAuthentication()
            try:
                request.user, request.auth = auth.authenticate(request)
            except AuthenticationFailed:
                request.user = None


