from django.contrib import admin

from .models import Article
from .models import EasyditaBundle
from .models import Image
from .models import Webhook


class ArticleAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'kav_id',
        'title',
        'url_name',
    ]
admin.site.register(Article, ArticleAdmin)


class EasyditaBundleAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'easydita_id',
        'easydita_resource_id',
        'status',
        'time_queued',
        'time_processed',
    ]
    list_filter = ('status',)
    view_on_site = False
admin.site.register(EasyditaBundle, EasyditaBundleAdmin)


class ImageAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'filename',
    ]
admin.site.register(Image, ImageAdmin)


class WebhookAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'status',
        'time',
    ]
    list_filter = ('status',)
admin.site.register(Webhook, WebhookAdmin)
