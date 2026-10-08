from django.conf import settings


class SessionTimeoutMiddleware:
    """Administrator sessiyasini qisqaroq muddatga (qo'shimcha himoya) cheklaydi."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and getattr(user, "role", "") == "admin":
            request.session.set_expiry(settings.ADMIN_SESSION_AGE)
        return self.get_response(request)
