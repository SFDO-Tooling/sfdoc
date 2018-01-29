from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^(?P<easydita_bundle_id>\d+)/$',
        view=views.bundle_status,
        name='bundle_status',
    ),
    url(
        regex=r'^$',
        view=views.queue_status,
        name='queue_status',
    ),
    url(
        regex=r'^webhook/$',
        view=views.webhook,
        name='webhook',
    ),
]
