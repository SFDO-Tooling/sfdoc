from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^$',
        view=views.index,
        name='index',
    ),
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
        regex=r'^bundles/(?P<pk>\d+)/review/$',
        view=views.review,
        name='review',
    ),
    url(
        regex=r'^webhook/$',
        view=views.webhook,
        name='webhook',
    ),
]
