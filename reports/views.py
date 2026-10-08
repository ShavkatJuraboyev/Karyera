from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render

from accounts.models import Role
from accounts.permissions import ANALYTICS_ROLES, role_required
from core.exporters import pdf_response, xlsx_response
from core.models import AuditLog
from core.services import audit
from reports.analytics import dashboard_data
from reports.forms import ReportFilterForm
from reports.registry import REPORTS


@role_required(*ANALYTICS_ROLES)
def dashboard(request):
    user = request.user
    scope = user.faculty.name if user.role == Role.DEAN and user.faculty else ""
    return render(request, "reports/dashboard.html", {"d": dashboard_data(user), "scope": scope})


@role_required(*ANALYTICS_ROLES)
def report_index(request):
    items = [(key, r) for key, r in REPORTS.items() if request.user.role in r["roles"]]
    return render(request, "reports/index.html", {"items": items})


@role_required(*ANALYTICS_ROLES)
def report_view(request, key):
    report = REPORTS.get(key)
    if report is None:
        raise Http404
    if request.user.role not in report["roles"]:
        raise PermissionDenied
    form = ReportFilterForm(request.GET or None)
    for name in list(form.fields):
        if name not in report["filters"]:
            del form.fields[name]
    if request.user.role == Role.DEAN and "faculty" in form.fields:
        del form.fields["faculty"]
    params = {}
    headers, rows = [], []
    valid = True
    if request.GET:
        valid = form.is_valid()
        if valid:
            params = {k: v for k, v in form.cleaned_data.items() if v not in (None, "")}
    if valid:
        headers, rows = report["func"](request.user, params)
    export = request.GET.get("export")
    if valid and export in ("xlsx", "pdf"):
        audit(AuditLog.Action.EXPORT, request=request, details=f"Hisobot: {report['title']} ({export})")
        fn = xlsx_response if export == "xlsx" else pdf_response
        return fn(report["title"], headers, rows, filename_prefix=key.replace("-", "_"))
    query = request.GET.copy()
    query.pop("export", None)
    return render(request, "reports/report.html", {
        "key": key, "report": report, "form": form, "headers": headers, "rows": rows,
        "querystring": query.urlencode(),
    })
