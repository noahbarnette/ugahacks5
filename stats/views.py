from django.conf import settings
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone

from app.views import TabsView
from applications.models import Application, DraftApplication
from reimbursement.models import Reimbursement
from user.mixins import is_organizer, IsOrganizerMixin
from workshops.models import Workshop, Attendance

STATUS_DICT = dict(Application.STATUS)
GENDER_DICT = dict(Application.GENDERS)
CLASSSTATUS_DICT = dict(Application.CLASSSTATUS)
HEARABOUT_DICT = dict(Application.HEARABOUT)
ATTENDANCE_TYPE_DICT = dict(Application.ATTENDANCE)
RE_STATUS_DICT = dict(Reimbursement.STATUS)


def stats_tabs():
    tabs = [('Applications', reverse('app_stats'), False), ('Workshops', reverse('workshop_stats'), False)]
    if getattr(settings, 'REIMBURSEMENT_ENABLED', False):
        tabs.append(('Reimbursements', reverse('reimb_stats'), False))
    return tabs


@is_organizer
def reimb_stats_api(request):
    # Status analysis
    status_count = Reimbursement.objects.all().values('status') \
        .annotate(reimbursements=Count('status'))
    status_count = map(lambda x: dict(status_name=RE_STATUS_DICT[x['status']], **x), status_count)

    total_apps = Application.objects.count()
    reimb_count = Reimbursement.objects.count()

    amounts = Reimbursement.objects.all().exclude(status=Reimbursement.DRAFT).values('status') \
        .annotate(final_amount=Sum('reimbursement_money'), max_amount=Sum('assigned_money'))
    amounts = map(lambda x: dict(status_name=RE_STATUS_DICT[x['status']], **x), amounts)

    return JsonResponse(
        {
            'update_time': timezone.now(),
            'reimb_count': reimb_count,
            'reimb_apps': {'Reimbursement needed': reimb_count, 'No reimbursement': total_apps - reimb_count},
            'status': list(status_count),
            'amounts': list(amounts),
        }
    )


@is_organizer
def app_stats_api(request):
    # Status analysis
    status_count = Application.objects.all().values('status') \
        .annotate(applications=Count('status'))
    status_count = map(lambda x: dict(status_name=STATUS_DICT[x['status']], **x), status_count)

    gender_count = Application.objects.all().values('gender') \
        .annotate(applications=Count('gender'))
    gender_count = map(lambda x: dict(gender_name=GENDER_DICT[x['gender']], **x), gender_count)

    gender_count_attended = Application.objects.filter(status=Application.ATTENDED).values('gender').annotate(
        applications=Count('gender'))
    gender_count_attended = map(lambda x: dict(gender_name=GENDER_DICT[x['gender']], **x), gender_count_attended)

    class_count = Application.objects.all().exclude(participant=Application.P_MENTOR).values('class_status').annotate(
        applications=Count('class_status'))
    class_count = map(lambda x: dict(class_name=CLASSSTATUS_DICT[x['class_status']], **x), class_count)

    class_count_attended = Application.objects.filter(status=Application.ATTENDED).exclude(
        participant=Application.P_MENTOR).values('class_status').annotate(applications=Count('class_status'))
    class_count_attended = map(lambda x: dict(class_name=CLASSSTATUS_DICT[x['class_status']], **x),
                               class_count_attended)

    major_count = Application.objects.all().values('degree').annotate(applications=Count('degree'))
    major_count = map(lambda x: dict(**x), major_count)
    major_count = [major for major in major_count if major['applications'] > 5]

    major_count_attended = Application.objects.filter(status=Application.ATTENDED).values('degree').annotate(
        applications=Count('degree'))
    major_count_attended = map(lambda x: dict(**x), major_count_attended)
    major_count_attended = [major for major in major_count_attended if major['applications'] > 5]

    hear_about_count = Application.objects.all().values('hearabout').annotate(applications=Count('hearabout'))
    hear_about_count = map(lambda x: dict(**x), hear_about_count)

    attendance_type_count = Application.objects.all().values('attendance_type').annotate(applications=Count('attendance_type'))
    attendance_type_count = map(lambda x: dict(**x), attendance_type_count)

    first_timer_count = Application.objects.all().values('first_timer').annotate(applications=Count('first_timer'))
    first_timer_count = map(lambda x: dict(**x), first_timer_count)

    first_timer_count_attended = Application.objects.filter(status=Application.ATTENDED).values(
        'first_timer').annotate(applications=Count('first_timer'))
    first_timer_count_attended = map(lambda x: dict(**x), first_timer_count_attended)

    tshirt_dict = dict(Application.TSHIRT_SIZES)
    shirt_count = map(
        lambda x: {'tshirt_size': tshirt_dict.get(x['tshirt_size'], 'Unknown'), 'applications': x['applications']},
        Application.objects.values('tshirt_size').annotate(applications=Count('tshirt_size'))
    )

    shirt_count_confirmed = map(
        lambda x: {'tshirt_size': tshirt_dict.get(x['tshirt_size'], 'Unknown'), 'applications': x['applications']},
        Application.objects.filter(status=Application.CONFIRMED).values('tshirt_size')
            .annotate(applications=Count('tshirt_size'))
    )

    diet_count = Application.objects.values('diet') \
        .annotate(applications=Count('diet'))
    diet_count_confirmed = Application.objects.filter(status=Application.CONFIRMED).values('diet') \
        .annotate(applications=Count('diet'))
    other_diets = Application.objects.filter(status=Application.CONFIRMED).values('other_diet')

    hardware_count = Application.objects.filter(hardware__isnull=False).exclude(hardware__icontains="N/A").exclude(
        hardware__icontains="na") \
        .exclude(hardware__icontains="NA").exclude(hardware__icontains="n/a").exclude(
        hardware__icontains="None").exclude(hardware__icontains="Nothing").values('hardware')

    timeseries = Application.objects.all().annotate(date=TruncDate('submission_date')).values('date').annotate(
        applications=Count('date'))
    return JsonResponse(
        {
            'update_time': timezone.now(),
            'app_count': Application.objects.count(),
            'draft_app_count': DraftApplication.objects.count(),
            'status': list(status_count),
            'shirt_count': list(shirt_count),
            'shirt_count_confirmed': list(shirt_count_confirmed),
            'timeseries': list(timeseries),
            'gender': list(gender_count),
            'gender_attended': list(gender_count_attended),
            'major_count': major_count,
            'major_count_attended': major_count_attended,
            'class': list(class_count),
            'class_attended': list(class_count_attended),
            'hearabout_count': list(hear_about_count),
            'attendance_type_count': list(attendance_type_count),
            'firsttimer_count': list(first_timer_count),
            'firsttimer_count_attended': list(first_timer_count_attended),
            'diet': list(diet_count),
            'diet_confirmed': list(diet_count_confirmed),
            'other_diet': '<br>'.join([el['other_diet'] for el in other_diets if el['other_diet']]),
            'hardware': '<br>'.join([equip['hardware'] for equip in hardware_count])
        }
    )


@is_organizer
def workshop_stats_api(request):
    workshops = Workshop.objects.all()
    workshop_attendance = [
        {"title": workshop.title, "attendance": Attendance.objects.filter(workshop=workshop).count()} for workshop in
        workshops]
    return JsonResponse(
        {
            'update_time': timezone.now(),
            'workshops': workshop_attendance
        }
    )


class AppStats(IsOrganizerMixin, TabsView):
    template_name = 'application_stats.html'

    def get_current_tabs(self):
        return stats_tabs()


class ReimbStats(IsOrganizerMixin, TabsView):
    template_name = 'reimbursement_stats.html'

    def get_current_tabs(self):
        return stats_tabs()


class WorkshopStats(IsOrganizerMixin, TabsView):
    template_name = 'workshop_stats.html'

    def get_current_tabs(self):
        return stats_tabs()
