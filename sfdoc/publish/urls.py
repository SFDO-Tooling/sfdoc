from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^webhook/$',
        view=views.webhook,
        name='webhook',
    ),
]
