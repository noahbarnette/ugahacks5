from workshops.models import Workshop, Timeslot, Attendance
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.views.generic import DetailView, TemplateView
from django.views.generic.edit import FormView, UpdateView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from app.mixins import TabsViewMixin
from checkin.models import CheckIn
from user.mixins import IsOrganizerMixin, IsVolunteerMixin
from workshops.models import Workshop, Timeslot, Attendance
from workshops.tables import WorkshopListTable, WorkshopListFilter
from .forms import AddWorkshopForm


## TODO:
# Better fronend...
class WorkshopAdd(IsOrganizerMixin, FormView):
    template_name = 'workshop_add.html'
    success_url = '/workshops/list/'
    form_class = AddWorkshopForm

    # use {% if is_available %} in html template to check if there are any timeslots available. If not, do not display the form.
    # This method is used to check whether or not there are timeslots available.
    def get_context_data(self, **kwargs):
        context = super(WorkshopAdd, self).get_context_data(**kwargs)
        if (Timeslot.objects.filter(workshop_one__isnull=True).count() + Timeslot.objects.filter(
            workshop_two__isnull=True).count()) > 0:
            context.update({
                'is_available': True,
            })
        else:
            context.update({
                'is_available': False,
            })
        return context

    def form_valid(self, form):
        workshop = form.save(commit=False)
        # form.cleaned_data['timeslot'] returns the unique id of the timeslot. this
        # id is then used to get the timeslow object.
        # timeslot = Timeslot.objects.get(pk=form.cleaned_data['timeslot'])
        timeslot = form.cleaned_data['timeslot']
        # Checks if workshop_one is filled first.
        workshop.save()
        if not timeslot.workshop_one:
            timeslot.workshop_one = workshop
        else:
            timeslot.workshop_two = workshop
        timeslot.save()
        return super().form_valid(form)


class WorkshopUpdate(IsOrganizerMixin, UpdateView):
    model = Workshop
    success_url = '/workshops/list/'
    fields = ['title', 'description', 'location', 'host', 'open', 'in_person']
    template_name = 'workshop_update_form.html'

    def get_context_data(self, **kwargs):
        context = super(WorkshopUpdate, self).get_context_data(**kwargs)
        timeslot_list = Timeslot.objects.filter(workshop_one__isnull=True) | Timeslot.objects.filter(
            workshop_two__isnull=True)
        context.update({
            'timeslot_list': timeslot_list,
        })
        return context

    def form_valid(self, form):
        workshop = form.save(commit=False)
        # clearing the workshop from the previous timeslot so there are no duplicate workshops
        old_timeslot = Timeslot.objects.filter(workshop_one=workshop).first()
        if old_timeslot:
            old_timeslot.workshop_one = None
        else:
            old_timeslot = Timeslot.objects.filter(workshop_two=workshop).first()
            old_timeslot.workshop_two = None
        old_timeslot.save()
        # adding workshop to new timeslot.
        timeslot = Timeslot.objects.filter(id=self.request.POST['workshop_timeslot']).first()
        if not timeslot.workshop_one:
            timeslot.workshop_one = workshop
        else:
            timeslot.workshop_two = workshop
        timeslot.save()
        workshop.save()
        return super(WorkshopUpdate, self).form_valid(form)


class WorkshopList(IsVolunteerMixin, TabsViewMixin, SingleTableMixin, FilterView):
    template_name = 'workshop_list.html'
    table_class = WorkshopListTable
    filterset_class = WorkshopListFilter
    table_pagination = {'per_page': 100}


## TODO:
# Make a better message for users when workshop/timeslot is not found.
# Better frontend...
class WorkshopDetail(IsVolunteerMixin, DetailView):
    model = Workshop
    template_name = 'workshop_detail.html'

    def get_context_data(self, **kwargs):
        context = super(WorkshopDetail, self).get_context_data(**kwargs)
        workshop = kwargs['object']
        # Since workshop is a ForeignKey in timeslot, the start and end attributes are retrieved from
        # the timeslot model.
        # There should only be two workshops per timeslot. Gets the timeslot related to the given workshop.
        timeslot = workshop.workshop_one_set.first() or workshop.workshop_two_set.first()
        # Recieves the total amount of people that attended this workshop
        attendance = workshop.attendance_set.count()
        # TODO: Make this statement more descriptive.
        if not workshop or not timeslot:
            raise Http404
        context.update({
            'title': workshop.title,
            'description': workshop.description,
            'location': workshop.location,
            'host': workshop.host,
            'start': timeslot.start,
            'end': timeslot.end,
            'attendance': attendance,  # This is an int
        })
        return context


class WorkshopCheckin(IsVolunteerMixin, TemplateView):
    template_name = 'workshop_checkin.html'

    def get_context_data(self, **kwargs):
        context = super(WorkshopCheckin, self).get_context_data(**kwargs)
        workshopid = kwargs['id']
        workshop = Workshop.objects.filter(id=workshopid).first()
        if not workshop:
            raise Http404

        if not workshop.open and not self.request.user.is_organizer:
            raise PermissionDenied('Meal is not active')

        context.update({
            'workshop': workshop,
        })
        if self.request.GET.get('success', False):
            context.update({
                'success': True,
            })
        if self.request.GET.get('error', False):
            context.update({
                'error': self.request.GET.get('error', 'Seems there\'s an error'),
            })
        return context

    def post(self, request, *args, **kwargs):
        workshop_id = request.POST.get('workshop_id', None)
        qr_id = request.POST.get('qr_code', None)

        if not qr_id or not workshop_id:
            messages.error(self.request, 'The QR code or workshop is not available.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        workshop = Workshop.objects.filter(id=workshop_id).first()

        if not workshop.open and not self.request.user.is_organizer:
            messages.error(self.request, 'This workshop is not open yet or it has ended.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        hacker_checkin = CheckIn.objects.filter(qr_identifier=qr_id).first()
        if not hacker_checkin:
            messages.error(self.request, 'Invalid QR code!')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        hacker = hacker_checkin.application.user
        if not hacker:
            messages.error(self.request, 'No user found for this QR code!')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        # Checks if the user has attended this workshop already. If they have, then a message is displayed.
        hacker_attended = workshop.attendance_set.filter(user=hacker).first()
        if hacker_attended:
            messages.error(self.request, 'This hacker has already been marked for attendance for this workshop!')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        # Logs user attendance to a workshop.
        attendance = Attendance(workshop=workshop, user=hacker)
        attendance.save()

        messages.success(self.request, 'Hacker attendance logged!')

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
