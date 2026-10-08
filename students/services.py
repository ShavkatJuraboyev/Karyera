from accounts.models import Role
from students.models import StudentProfile


def get_profile(user):
    profile, _ = StudentProfile.objects.get_or_create(user=user)
    return profile


def scope_profiles(user, qs):
    """Foydalanuvchi ko'ra oladigan talaba/bitiruvchi profillari (dekan — faqat o'z fakulteti)."""
    if user.role == Role.DEAN:
        if not user.faculty_id:
            return qs.none()
        return qs.filter(faculty_id=user.faculty_id)
    if user.role in (Role.STAFF, Role.ADMIN, Role.MANAGEMENT):
        return qs
    return qs.none()


def can_view_profile(user, profile):
    """Profilni kim ko'rishi mumkin: egasi, markaz xodimlari, o'z fakulteti dekani, nomzod ariza topshirgan ish beruvchi."""
    if not user.is_authenticated:
        return False
    if profile.user_id == user.pk:
        return True
    if user.role in (Role.STAFF, Role.ADMIN, Role.MANAGEMENT):
        return True
    if user.role == Role.DEAN:
        return bool(user.faculty_id) and user.faculty_id == profile.faculty_id
    if user.role == Role.EMPLOYER:
        from vacancies.models import Application
        return Application.objects.filter(applicant_id=profile.user_id, vacancy__employer__user=user).exists()
    return False
