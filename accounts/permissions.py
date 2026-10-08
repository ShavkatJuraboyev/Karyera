from functools import wraps

from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from accounts.models import Role

CANDIDATE_ROLES = (Role.STUDENT, Role.GRADUATE)
STAFF_ROLES = (Role.STAFF, Role.ADMIN)
ANALYTICS_ROLES = (Role.STAFF, Role.ADMIN, Role.MANAGEMENT, Role.DEAN)


class RoleRequiredMixin(UserPassesTestMixin):
    """allowed_roles ro'yxatidagi rollargagina ruxsat beradi."""

    allowed_roles = ()

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_active and user.role in self.allowed_roles


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator
