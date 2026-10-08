from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Direction, Faculty, Role
from accounts.permissions import ANALYTICS_ROLES
from api.serializers import (ApplicationSerializer, ApplicationStatusSerializer, DirectionSerializer, EventSerializer,
                             FacultySerializer, NewsSerializer, ProfileSerializer, UserSerializer, VacancySerializer)
from core.models import News
from events.models import Event
from events.services import cancel_registration, register_for_event
from reports.analytics import dashboard_data
from students.services import get_profile
from vacancies.models import Application, Vacancy
from vacancies.services import (BusinessError, apply_to_vacancy, set_application_status, withdraw_application)


class IsCandidate(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_candidate)


class IsAnalyticsRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ANALYTICS_ROLES)


class LoginTokenView(ObtainAuthToken):
    """POST {username, password} → {token, role}"""

    def post(self, request, *args, **kwargs):
        from django.conf import settings
        from django.core.cache import cache
        from core.services import get_client_ip
        key = f"api-login-fail:{get_client_ip(request)}:{str(request.data.get('username', '')).lower()}"
        if cache.get(key, 0) >= settings.LOGIN_MAX_ATTEMPTS:
            return Response({"detail": "Juda ko'p noto'g'ri urinish. Keyinroq urinib ko'ring."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = self.serializer_class(data=request.data, context={"request": request})
        if not serializer.is_valid():
            cache.set(key, cache.get(key, 0) + 1, settings.LOGIN_LOCKOUT_SECONDS)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        cache.delete(key)
        from rest_framework.authtoken.models import Token
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        from core.models import AuditLog
        from core.services import audit
        audit(AuditLog.Action.LOGIN, request=request, user=user, details="API orqali kirdi")
        return Response({"token": token.key, "role": user.role})


class FacultyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Faculty.objects.filter(is_active=True)
    serializer_class = FacultySerializer
    pagination_class = None


class DirectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DirectionSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Direction.objects.filter(is_active=True).select_related("faculty")
        faculty = self.request.query_params.get("faculty")
        return qs.filter(faculty_id=faculty) if faculty and faculty.isdigit() else qs


class VacancyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VacancySerializer

    def get_queryset(self):
        qs = Vacancy.objects.published().select_related("employer").prefetch_related("directions__faculty").order_by("-published_at", "-id")
        p = self.request.query_params
        if p.get("search"):
            s = p["search"]
            qs = qs.filter(Q(title__icontains=s) | Q(employer__name__icontains=s) | Q(requirements__icontains=s))
        if p.get("region"):
            qs = qs.filter(region=p["region"])
        if p.get("type"):
            qs = qs.filter(employment_type=p["type"])
        if p.get("employer", "").isdigit():
            qs = qs.filter(employer_id=int(p["employer"]))
        if p.get("direction", "").isdigit():
            qs = qs.filter(Q(directions__pk=int(p["direction"])) | Q(directions__isnull=True)).distinct()
        if p.get("salary", "").isdigit():
            s = int(p["salary"])
            qs = qs.filter(Q(salary_max__gte=s) | Q(salary_max__isnull=True, salary_min__gte=s))
        return qs


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventSerializer

    def get_queryset(self):
        qs = Event.objects.filter(is_published=True).order_by("start_at")
        if self.request.query_params.get("upcoming") == "1":
            qs = qs.filter(start_at__gte=timezone.now())
        return qs

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def register(self, request, pk=None):
        if request.user.role not in (Role.STUDENT, Role.GRADUATE, Role.EMPLOYER):
            raise PermissionDenied("Bu rol tadbirga ro'yxatdan o'ta olmaydi.")
        try:
            _, created = register_for_event(request.user, pk, request=request)
        except BusinessError as e:
            raise serializers.ValidationError({"detail": str(e)})
        return Response({"registered": True, "created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        try:
            cancel_registration(request.user, pk)
        except BusinessError as e:
            raise serializers.ValidationError({"detail": str(e)})
        return Response({"registered": False})


class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NewsSerializer

    def get_queryset(self):
        return News.objects.filter(is_published=True, published_at__lte=timezone.now())


class ApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Application.objects.select_related("vacancy", "vacancy__employer", "applicant")
        if user.is_candidate:
            return qs.filter(applicant=user)
        if user.role == Role.EMPLOYER:
            return qs.filter(vacancy__employer__user=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        if not request.user.is_candidate:
            raise PermissionDenied("Faqat talaba va bitiruvchilar ariza topshirishi mumkin.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            get_profile(request.user)
            application = apply_to_vacancy(request.user, serializer.validated_data["vacancy"],
                                           serializer.validated_data.get("cover_letter", ""), request=request)
        except BusinessError as e:
            raise serializers.ValidationError({"detail": str(e)})
        return Response(self.get_serializer(application).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        application = self.get_object()
        try:
            withdraw_application(application, request.user, request=request)
        except BusinessError as e:
            raise serializers.ValidationError({"detail": str(e)})
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        if request.user.role != Role.EMPLOYER:
            raise PermissionDenied("Faqat ish beruvchi ariza holatini o'zgartira oladi.")
        application = self.get_object()
        s = ApplicationStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            set_application_status(application, d["status"], request.user, interview_at=d.get("interview_at"),
                                   interview_place=d.get("interview_place", ""), comment=d.get("employer_comment", ""), request=request)
        except BusinessError as e:
            raise serializers.ValidationError({"detail": str(e)})
        return Response(self.get_serializer(application).data)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = {"user": UserSerializer(request.user).data}
        if request.user.is_candidate:
            data["profile"] = ProfileSerializer(get_profile(request.user)).data
        return Response(data)

    def patch(self, request):
        if not request.user.is_candidate:
            raise PermissionDenied("Profilni faqat talaba va bitiruvchi o'zgartira oladi.")
        serializer = ProfileSerializer(get_profile(request.user), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"user": UserSerializer(request.user).data, "profile": serializer.data})


class StatsView(APIView):
    permission_classes = [IsAnalyticsRole]

    def get(self, request):
        return Response(dashboard_data(request.user))
