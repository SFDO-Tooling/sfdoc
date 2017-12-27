from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^production/(?P<easydita_bundle_id>\d+)/$',
        view=views.publish_to_production,
        name='production',
    ),
    url(
        regex=r'^production/(?P<easydita_bundle_id>\d+)/confirmed/$',
        view=views.publish_to_production_confirmation,
        name='production_confirm',
    ),
    url(
        regex=r'^webhook/$',
        view=views.webhook,
        name='webhook',
    ),
]
