from django.contrib import admin

from .models import Article
from .models import Bundle
from .models import Image
from .models import Webhook
from .models import Docset


class ArticleAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'ka_id',
        'kav_id',
        'title',
        'url_name',
    ]
admin.site.register(Article, ArticleAdmin)


class BundleAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'easydita_zipfile_id',
        'easydita_resource_id',
        'status',
    ]
    list_filter = ('status',)
    view_on_site = False
admin.site.register(Bundle, BundleAdmin)


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


class DocsetAdmin(admin.ModelAdmin):
    list_display = [
        'docset_id',
        'display_name'
    ]
admin.site.register(Docset, DocsetAdmin)
