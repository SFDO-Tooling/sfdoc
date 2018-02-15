from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^queue/$',
        view=views.queue,
        name='queue',
    ),
    url(
        regex=r'^(?P<pk>\d+)/$',
        view=views.bundle,
        name='bundle',
    ),
    url(
        regex=r'^webhook/$',
        view=views.webhook,
        name='webhook',
    ),
]
