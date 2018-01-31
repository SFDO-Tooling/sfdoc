from django.contrib import admin

from .models import Article
from .models import EasyditaBundle
from .models import Image
from .models import Webhook


class ArticleAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'kav_id',
    ]
admin.site.register(Article, ArticleAdmin)


class EasyditaBundleAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'easydita_id',
        'status',
        'time_queued',
    ]
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
admin.site.register(Webhook, WebhookAdmin)
