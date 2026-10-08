from rest_framework import serializers

from accounts.models import Direction, Faculty, User
from core.models import News
from employers.models import Employer
from events.models import Event
from students.models import EmploymentStatus, StudentProfile
from vacancies.models import Application, Vacancy


class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ["id", "name", "code"]


class DirectionSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.name", read_only=True)

    class Meta:
        model = Direction
        fields = ["id", "name", "code", "faculty", "faculty_name"]


class EmployerBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employer
        fields = ["id", "name", "industry", "region", "website"]


class VacancySerializer(serializers.ModelSerializer):
    employer = EmployerBriefSerializer(read_only=True)
    employment_type_display = serializers.CharField(source="get_employment_type_display", read_only=True)
    salary = serializers.CharField(source="salary_display", read_only=True)
    directions = DirectionSerializer(many=True, read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Vacancy
        fields = ["id", "title", "employer", "region", "employment_type", "employment_type_display", "salary_min", "salary_max",
                  "salary", "requirements", "duties", "schedule", "deadline", "directions", "published_at", "is_open"]


class ApplicationSerializer(serializers.ModelSerializer):
    vacancy = serializers.PrimaryKeyRelatedField(queryset=Vacancy.objects.published())
    vacancy_title = serializers.CharField(source="vacancy.title", read_only=True)
    employer_name = serializers.CharField(source="vacancy.employer.name", read_only=True)
    applicant_name = serializers.CharField(source="applicant.full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Application
        fields = ["id", "vacancy", "vacancy_title", "employer_name", "applicant_name", "cover_letter", "status", "status_display",
                  "interview_at", "interview_place", "employer_comment", "created_at", "updated_at"]
        read_only_fields = ["status", "interview_at", "interview_place", "employer_comment", "created_at", "updated_at"]


class ApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[(s.value, s.label) for s in (Application.Status.REVIEWING, Application.Status.INTERVIEW,
                                                                            Application.Status.ACCEPTED, Application.Status.REJECTED)])
    interview_at = serializers.DateTimeField(required=False, allow_null=True)
    interview_place = serializers.CharField(required=False, allow_blank=True, max_length=250)
    employer_comment = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if attrs["status"] == Application.Status.INTERVIEW and not attrs.get("interview_at"):
            raise serializers.ValidationError({"interview_at": "Suhbat vaqtini ko'rsating."})
        return attrs


class EventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    registered_count = serializers.IntegerField(read_only=True)
    spots_left = serializers.IntegerField(read_only=True)
    registration_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = ["id", "title", "event_type", "event_type_display", "description", "location", "start_at", "end_at",
                  "capacity", "registered_count", "spots_left", "registration_open"]


class NewsSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = News
        fields = ["id", "title", "category", "category_display", "body", "published_at"]


class ProfileSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.name", read_only=True)
    direction_name = serializers.CharField(source="direction.name", read_only=True)
    employment_status_display = serializers.CharField(source="get_employment_status_display", read_only=True)
    completeness = serializers.IntegerField(read_only=True)

    class Meta:
        model = StudentProfile
        fields = ["faculty", "faculty_name", "direction", "direction_name", "course", "graduation_year", "birth_date", "region", "address",
                  "desired_position", "about", "employment_status", "employment_status_display", "employer_name", "position",
                  "employed_date", "completeness"]
        read_only_fields = ["faculty", "direction"]

    def validate(self, attrs):
        status = attrs.get("employment_status", getattr(self.instance, "employment_status", None))
        employer_name = attrs.get("employer_name", getattr(self.instance, "employer_name", ""))
        if status == EmploymentStatus.EMPLOYED and not employer_name:
            raise serializers.ValidationError({"employer_name": "Ishga joylashgan tashkilot nomini kiriting."})
        return attrs

    def update(self, instance, validated_data):
        profile = super().update(instance, validated_data)
        from datetime import date
        if profile.employment_status in (EmploymentStatus.EMPLOYED, EmploymentStatus.SELF_EMPLOYED):
            if not profile.employed_date:
                profile.employed_date = date.today()
        else:
            profile.employer_name, profile.position, profile.employed_date = "", "", None
        profile.save()
        return profile


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "patronymic", "email", "phone", "role", "role_display"]
        read_only_fields = fields
