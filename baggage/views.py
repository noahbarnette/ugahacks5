import base64
import time

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from app.mixins import TabsViewMixin
from app.slack import send_slack_message
from app.views import TabsView
from baggage import utils
from baggage.models import Bag, Room
from baggage.tables import BaggageListTable, BaggageListFilter, BaggageUsersTable
from baggage.tables import BaggageUsersFilter, BaggageCurrentHackerTable
from checkin.models import CheckIn
from user.mixins import IsVolunteerMixin
from user.models import User


def organizer_tabs(user):
    t = [('Search', reverse('baggage_search'), False),
         ('List', reverse('baggage_list'), False),
         ('Map', reverse('baggage_map'), False),
         ('History', reverse('baggage_history'), False)]
    return t


def hacker_tabs(user):
    t = [('Baggage', reverse('baggage_currenthacker'), False), ]
    return t


class BaggageList(IsVolunteerMixin, TabsViewMixin, SingleTableMixin, FilterView):
    template_name = 'baggage_list.html'
    table_class = BaggageListTable
    filterset_class = BaggageListFilter
    table_pagination = {'per_page': 100}

    def get_current_tabs(self):
        return organizer_tabs(self.request.user)

    def get_queryset(self):
        if 'user_id' in self.kwargs:
            id_ = self.kwargs['user_id']
            user = User.objects.filter(id=id_)
            return Bag.objects.filter(status=Bag.ADDED, owner=user)
        return Bag.objects.filter(status=Bag.ADDED)


class BaggageHacker(IsVolunteerMixin, TabsViewMixin, SingleTableMixin, FilterView):
    template_name = 'baggage_hacker.html'
    table_class = BaggageListTable
    filterset_class = BaggageListFilter
    table_pagination = {'per_page': 100}

    def get_back_url(self):
        return 'javascript:history.back()'

    def get_queryset(self):
        id_ = self.kwargs['user_id']
        user = User.objects.filter(id=id_)
        return Bag.objects.filter(status=Bag.ADDED, owner=user)


class BaggageUsers(IsVolunteerMixin, TabsViewMixin, SingleTableMixin, FilterView):
    template_name = 'baggage_users.html'
    table_class = BaggageUsersTable
    filterset_class = BaggageUsersFilter
    table_pagination = {'per_page': 100}

    def get_current_tabs(self):
        return organizer_tabs(self.request.user)

    def get_queryset(self):
        return CheckIn.objects.all()


class BaggageAdd(IsVolunteerMixin, TabsView):
    template_name = 'baggage_add.html'

    def get_back_url(self):
        return 'javascript:history.back()'

    def get_context_data(self, **kwargs):
        context = super(BaggageAdd, self).get_context_data(**kwargs)
        userid = kwargs['new_id']
        user = User.objects.filter(id=userid).first()
        if not user:
            raise Http404
        context.update({
            'user': user,
            'rooms': Room.objects.all()
        })
        return context

    def post(self, request, *args, **kwargs):
        bagtype = request.POST.get('bag_type')
        bagcolor = request.POST.get('bag_color')
        bagdesc = request.POST.get('bag_description')
        bagspe = request.POST.get('bag_special')
        userid = request.POST.get('user_id')
        bagimage = request.POST.get('bag_image')

        bag = Bag()
        bag.owner = User.objects.filter(id=userid).first()
        bag.inby = request.user
        bag.btype = bagtype
        bag.color = bagcolor
        bag.description = bagdesc
        bag.special = (bagspe == 'special')

        if bagimage:
            try:
                bagimageformat, bagimagefile = bagimage.split(';base64,')
                bagimageext = bagimageformat.split('/')[-1]
                bag.image = ContentFile(base64.b64decode(bagimagefile),
                                        name=(str(time.time()).split('.')[0] + '-' + userid + '.' + bagimageext))
            except:
                print("Error: Couldn't retrieve the image and decode it.")

        posmanual = request.POST.get('pos_manual')
        bagroom = request.POST.get('pos_room')
        bagrow = request.POST.get('pos_row')
        bagcol = request.POST.get('pos_col')
        position = ()
        if posmanual == 'manual' and bagspe != 'special' and bagroom and bagrow and bagcol:
            position = (3, bagroom, bagrow, bagcol)
            posempty = Bag.objects.filter(status=Bag.ADDED, room=bagroom, row=bagrow, col=bagcol).count()
            if posempty > 0:
                messages.success(self.request, 'Error! Position is already taken!')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        else:
            position = utils.get_position(bag.special)

        if position[0] != 0:
            bag.room = Room.objects.filter(room=position[1]).first()
            bag.row = position[2]
            bag.col = position[3]
            bag.save()
            messages.success(self.request, 'Bag checked-in!')
            send_slack_message(bag.owner.email, '*Baggage check-in* :handbag:\nYou\'ve just '
                                                'registered :memo: a bag with ID `' + str(bag.bid) + '` located '
                                                                                                     ':world_map: at `' +
                               position[1] + '-' + position[2] + str(position[3]) +
                               '`!\n_Remember to take it before leaving :woman-running::skin-tone-3:!_')
            return redirect('baggage_detail', id=(str(bag.bid, )), first='first/')
        messages.success(self.request, 'Error! Couldn\'t add the bag!')
        return redirect('baggage_list')


class BaggageDetail(IsVolunteerMixin, TabsView):
    template_name = 'baggage_detail.html'

    def get_back_url(self):
        if self.kwargs['first'] != 'first/':
            return 'javascript:history.back()'

    def get_context_data(self, **kwargs):
        context = super(BaggageDetail, self).get_context_data(**kwargs)
        bagid = kwargs['id']
        bagfirst = (kwargs['first'] == 'first/')
        bag = Bag.objects.filter(bid=bagid).first()
        if not bag:
            raise Http404
        context.update({
            'bag': bag,
            'position': bag.position(),
            'checkedout': bag.status == Bag.REMOVED,
            'first': bagfirst
        })
        return context

    def post(self, request, *args, **kwargs):
        bagid = request.POST.get('bag_id')
        bag = Bag.objects.filter(bid=bagid).first()
        bag.status = Bag.REMOVED
        bag.outby = request.user
        bag.save()
        messages.success(self.request, 'Bag checked-out!')
        send_slack_message(bag.owner.email, '*Baggage check-out* :handbag:\nYour bag with ID `' +
                           str(bagid) + '` has been checked-out :truck:!')
        return redirect('baggage_search')


class BaggageMap(IsVolunteerMixin, TabsView):
    template_name = 'baggage_map.html'

    def get_current_tabs(self):
        return organizer_tabs(self.request.user)

    def get_context_data(self, **kwargs):
        context = super(BaggageMap, self).get_context_data(**kwargs)
        rooms = Room.objects.all()
        bags = Bag.objects.filter(status=Bag.ADDED)
        context.update({
            'rooms': rooms,
            'bags': bags
        })
        return context


class BaggageHistory(IsVolunteerMixin, TabsView):
    template_name = 'baggage_history.html'

    def get_current_tabs(self):
        return organizer_tabs(self.request.user)

    def get_context_data(self, **kwargs):
        context = super(BaggageHistory, self).get_context_data(**kwargs)
        bags = Bag.objects.all().order_by('-time', '-updated')
        context.update({
            'bags': bags
        })
        return context


class BaggageCurrentHacker(LoginRequiredMixin, TabsViewMixin, SingleTableMixin, FilterView):
    template_name = 'baggage_currenthacker.html'
    table_class = BaggageCurrentHackerTable
    filterset_class = BaggageListFilter
    table_pagination = {'per_page': 100}

    def get_current_tabs(self):
        return hacker_tabs(self.request.user)

    def get_queryset(self):
        user = self.request.user
        return Bag.objects.filter(status=Bag.ADDED, owner=user)
