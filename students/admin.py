from django.contrib import admin

from students.models import Certificate, Experience, LanguageSkill, PortfolioItem, Skill, StudentProfile


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0


class LanguageInline(admin.TabularInline):
    model = LanguageSkill
    extra = 0


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "faculty", "direction", "course", "graduation_year", "employment_status")
    list_filter = ("faculty", "employment_status", "graduation_year", "user__role")
    search_fields = ("user__username", "user__first_name", "user__last_name", "external_id")
    inlines = [SkillInline, LanguageInline]


admin.site.register(Certificate)
admin.site.register(Experience)
admin.site.register(PortfolioItem)
