from django.conf.urls import url

from . import views

app_name = "publish"

urlpatterns = [
    url(
        regex=r"^$",
        view=views.index,
        name="index",
    ),
    url(
        regex=r"^bundles/$",
        view=views.bundles,
        name="bundles",
    ),
    url(
        regex=r"^bundles/(?P<pk>\d+)/$",
        view=views.bundle,
        name="bundle",
    ),
    url(
        regex=r"^bundles/(?P<pk>\d+)/logs/$",
        view=views.logs,
        name="logs",
    ),
    url(
        regex=r"^bundles/(?P<pk>\d+)/requeue/$",
        view=views.requeue,
        name="requeue",
    ),
    url(
        regex=r"^bundles/(?P<pk>\d+)/review/$",
        view=views.review,
        name="review",
    ),
    url(
        regex=r"^webhook/$",
        view=views.webhook,
        name="webhook",
    ),
]
