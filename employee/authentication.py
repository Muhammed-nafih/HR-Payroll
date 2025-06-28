import jwt
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from django.contrib.auth.models import User

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Skip token authentication for login page
        if request.path == '/login':
            return None
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise exceptions.AuthenticationFailed('Authorization header is expected with Bearer token.')

        token = auth_header.split(' ')[1]  # Extract the token from the header

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired.')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token.')
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found.')

        return (user, None)  # Return the user and None as no credentials are required