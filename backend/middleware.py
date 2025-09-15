from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin

class QueryStringAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        token = request.GET.get("token")
        if token:
            try:
                access = AccessToken(token)
                user_model = get_user_model()
                user = user_model.objects.get(id=access["user_id"])
                request.user = user
            except Exception:
                pass
