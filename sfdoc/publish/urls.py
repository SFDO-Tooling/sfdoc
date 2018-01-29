from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^(?P<easydita_bundle_id>\d+)/$',
        view=views.publish_to_production,
        name='production',
    ),
    url(
        regex=r'^(?P<easydita_bundle_id>\d+)/confirmed/$',
        view=views.publish_to_production_confirmation,
        name='production_confirm',
    ),
    url(
        regex=r'^(?P<easydita_bundle_id>\d+)/status/$',
        view=views.bundle_status,
        name='bundle_status',
    ),
    url(
        regex=r'^webhook/$',
        view=views.webhook,
        name='webhook',
    ),
]
