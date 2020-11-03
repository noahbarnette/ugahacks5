import django_filters
import django_tables2 as tables
from django import forms
from django.conf import settings
from django.db.models import Q

from applications.models import Application
from user.models import User


class ApplicationFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='search_filter', label='Search')
    status = django_filters.MultipleChoiceFilter('status', label='Status', choices=Application.STATUS,
                                                 widget=forms.CheckboxSelectMultiple)

    def search_filter(self, queryset, name, value):
        return queryset.filter(Q(user__email__icontains=value) | Q(user__name__icontains=value) |
                               Q(university__icontains=value) | Q(origin__icontains=value) | Q(participant__icontains=value))

    class Meta:
        model = Application
        fields = ['search', 'status']


class DubiousApplicationFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='search_filter', label='Search')

    def search_filter(self, queryset, name, value):
        return queryset.filter(Q(user__email__icontains=value) | Q(user__name__icontains=value) |
                               Q(university__icontains=value) | Q(origin__icontains=value) | Q(participant__icontains=value))

    class Meta:
        model = Application
        fields = ['search']


class InviteFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='search_filter', label='Search')

    def search_filter(self, queryset, name, value):
        return queryset.filter(Q(user__email__icontains=value) | Q(user__name__icontains=value) |
                               Q(university__icontains=value) | Q(origin__icontains=value) | Q(participant__icontains=value))

    class Meta:
        model = Application
        fields = ['search', 'first_timer', 'reimb'] if getattr(settings, 'REIMBURSEMENT_ENABLED', False) else \
            ['search', 'first_timer']


class ApplicationsListTable(tables.Table):
    detail = tables.TemplateColumn(
        "<a href='{% url 'app_detail' record.uuid %}'>Detail</a> ",
        verbose_name='Actions', orderable=False)
    origin = tables.Column(accessor='origin', verbose_name='Origin')

    class Meta:
        model = Application
        attrs = {'class': 'table table-hover'}
        template = 'django_tables2/bootstrap-responsive.html'
        fields = ['user.name', 'user.email', 'participant', 'attendance_type', 'university', 'degree', 'class_status', 'origin']
        empty_text = 'No applications available'
        order_by = '-participant'


class DubiousListTable(tables.Table):
    mark_as_read = tables.TemplateColumn(
        """ <form action="" method="post">
                {% csrf_token %}
                <button class="btn btn-info" value="set_contacted" name="set_contacted">Contacted</button>
                <input  type="hidden" value="{{ record.uuid }}" name="id"></input>
                {% csrf_token %}
            </form>
        """
    )
    conclusion = tables.TemplateColumn(
        """ <form action="" method="post">
                {% csrf_token %}
                <button class="btn btn-warning" value="unset_dubious" name="unset_dubious">Not dubious</button>
                <button class="btn btn-danger" value="reject" name="reject"> Reject </button>
                <input type="hidden" name="id" value="{{ record.uuid }}"></input>
                {% csrf_token %}
            </form>
        """
    )
    detail = tables.TemplateColumn(
        "<a href='{% url 'app_detail' record.uuid %}'>Detail</a> ",
        verbose_name='Actions', orderable=False)
    origin = tables.Column(accessor='origin', verbose_name='Origin')

    class Meta:
        model = Application
        attrs = {'class': 'table table-hover'}
        template = 'django_tables2/bootstrap-responsive.html'
        fields = ['user.name', 'user.email', 'university', 'origin', 'contacted_by', 'contacted']
        empty_text = 'No applications available'
        order_by = '-submission_date'


class AdminApplicationsListTable(tables.Table):
    selected = tables.CheckBoxColumn(accessor="pk", verbose_name='Select')
    counter = tables.TemplateColumn('{{ row_counter|add:1 }}', verbose_name='Position')
    review_count = tables.Column(accessor='vote_set.count', verbose_name='# of reviews')
    detail = tables.TemplateColumn(
        "<a href='{% url 'app_detail' record.uuid %}'>Detail</a> ",
        verbose_name='Actions', orderable=False)

    class Meta:
        model = Application
        attrs = {'class': 'table table-hover'}
        template = 'django_tables2/bootstrap-responsive.html'
        fields = ['selected', 'user.name', 'vote_avg', 'reimb_amount', 'university', 'origin'] \
            if getattr(settings, 'REIMBURSEMENT_ENABLED', False) else \
            ['selected', 'user.name', 'vote_avg', 'university', 'origin']
        empty_text = 'No applications available'
        order_by = '-vote_avg'


class RankingListTable(tables.Table):
    counter = tables.TemplateColumn('{{ row_counter|add:1 }}', verbose_name='Position')

    class Meta:
        model = User
        attrs = {'class': 'table table-hover'}
        template = 'django_tables2/bootstrap-responsive.html'
        fields = ['counter', 'email', 'vote_count', 'skip_count', 'total_count']
        empty_text = 'No organizers voted yet... Why? :\'('
        order_by = '-total_count'


class AdminTeamListTable(tables.Table):
    selected = tables.CheckBoxColumn(accessor="team", verbose_name='Select')

    class Meta:
        model = Application
        attrs = {'class': 'table table-hover'}
        template = 'django_tables2/bootstrap-responsive.html'
        fields = ['selected', 'team', 'vote_avg', 'members']
        empty_text = 'No pending teams'
        order_by = '-vote_avg'
