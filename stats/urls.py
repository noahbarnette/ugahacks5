from django.conf import settings
from django.conf.urls import url
from django.views.decorators.cache import cache_page

from stats import views

urlpatterns = [
    url(r'^api/apps/$', cache_page(5 * 60)(views.app_stats_api), name='api_app_stats'),
    url(r'^api/reimb/$', cache_page(5 * 60)(views.reimb_stats_api), name='api_reimb_stats'),
    url(r'^api/workshops/$', cache_page(5 * 60)(views.workshop_stats_api), name='api_workshop_stats'),
    url(r'^apps/$', views.AppStats.as_view(), name='app_stats'),
    url(r'^workshops/$', views.WorkshopStats.as_view(), name='workshop_stats'),
]

if getattr(settings, 'REIMBURSEMENT_ENABLED', False):
    urlpatterns.append(url(r'^reimb/$', views.ReimbStats.as_view(), name='reimb_stats'))
