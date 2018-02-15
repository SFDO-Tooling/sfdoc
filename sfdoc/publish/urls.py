from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^bundles/$',
        view=views.bundles,
        name='bundles',
    ),
    url(
        regex=r'^bundles/(?P<pk>\d+)/$',
        view=views.bundle,
        name='bundle',
    ),
    url(
        regex=r'^queue/$',
        view=views.queue,
        name='queue',
    ),
    url(
        regex=r'^webhook/$',
        view=views.webhook,
        name='webhook',
    ),
]
