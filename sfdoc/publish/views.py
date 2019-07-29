from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django import template

from .forms import PublishToProductionForm
from .forms import RequeueBundleForm
from .logger import get_logger
from .models import Article
from .models import Bundle
from .models import Image
from .models import Webhook
from .salesforce import get_community_base_url
from .tasks import process_bundle_queues
from .tasks import process_webhook
from .tasks import publish_drafts

common_context = {
        'env_color': settings.ENV_COLOR,
        'env_name': settings.ENV_NAME,
}


@never_cache
@staff_member_required
def bundle(request, pk):
    bundle = get_object_or_404(Bundle, pk=pk)
    logs = reversed(bundle.logs.all().order_by('-time')[:10])
    context = {
        'bundle': bundle,
        'logs': logs,
        'ready_for_review': bundle.status == Bundle.STATUS_DRAFT,
        **common_context,
    }
    return render(request, 'bundle.html', context=context)


@never_cache
@staff_member_required
def bundles(request):
    qs = Bundle.objects.all().order_by('-time_last_modified')
    count = request.GET.get('count', 25)
    page = request.GET.get('page')
    paginator = Paginator(qs, count)
    try:
        bundles = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        bundles = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        bundles = paginator.page(paginator.num_pages)
    context = {'bundles': bundles,
                **common_context,
               }
    if bundles.has_previous():
        context['link_previous'] = '?page={}&count={}'.format(
            bundles.previous_page_number(),
            count,
        )
    if bundles.has_next():
        context['link_next'] = '?page={}&count={}'.format(
            bundles.next_page_number(),
            count,
        )
    return render(request, 'bundles.html', context=context)


@never_cache
@staff_member_required
def index(request):
    context = {
        'processing': Bundle.objects.filter(
            status=Bundle.STATUS_PROCESSING,
        ),
        'draft': Bundle.objects.filter(
            status=Bundle.STATUS_DRAFT,
        ),
        'waiting': Bundle.objects.filter(
            status=Bundle.STATUS_PUBLISH_WAIT,
        ),
        'publishing': Bundle.objects.filter(
            status=Bundle.STATUS_PUBLISHING,
        ),
        'queued': Bundle.objects.filter(
            status=Bundle.STATUS_QUEUED,
        ).order_by('time_queued'),
        **common_context,
    }
    return render(request, 'index.html', context=context)


@never_cache
@staff_member_required
def logs(request, pk):
    bundle = get_object_or_404(Bundle, pk=pk)
    logs = bundle.logs.all().order_by('time')
    context = {
        'bundle': bundle,
        'logs': logs,
        **common_context,
    }
    return render(request, 'logs.html', context=context)


@never_cache
@staff_member_required
def requeue(request, pk):
    bundle = get_object_or_404(Bundle, pk=pk)
    if not bundle.is_complete():
        return HttpResponseRedirect('../')
    context = {'bundle': bundle,
                **common_context,
               }
    if request.method == 'POST':
        form = RequeueBundleForm(request.POST)
        if form.is_valid() and request.POST['choice'] == 'Requeue':
            newbundle = Bundle.objects.create(
                easydita_id=bundle.easydita_id,
                easydita_resource_id=bundle.easydita_resource_id,
            )

            newbundle.enqueue()
            logger = get_logger(newbundle)
            logger.info('Requeued %s', newbundle)
            process_bundle_queues.delay()
        return HttpResponseRedirect('../')
    else:
        form = RequeueBundleForm()
    return render(request, 'requeue.html', context=context)


@never_cache
@staff_member_required
def review(request, pk):
    bundle = get_object_or_404(Bundle, pk=pk)
    logger = get_logger(bundle)
    if bundle.status != Bundle.STATUS_DRAFT:
        return HttpResponseRedirect('../')
    context = {'bundle': bundle,
                **common_context,
               }
    if request.method == 'POST':
        form = PublishToProductionForm(request.POST)
        if form.is_valid():
            if form.approved():
                logger.info('Approved %s', bundle)
                bundle.status = Bundle.STATUS_PUBLISH_WAIT
                bundle.save()
                publish_drafts.delay(bundle.pk)
            else:
                logger.info('Rejected %s', bundle)
                bundle.status = Bundle.STATUS_REJECTED
                bundle.save()
                process_bundle_queues.delay()
        return HttpResponseRedirect('../')
    else:
        form = PublishToProductionForm()

    base_url = get_community_base_url()
    assert base_url is not None

    def get_articles_for_view(collection):
        return [{
            'preview_url': f'{base_url}{article.preview_url}',
            'url_name': article.url_name,
        } for article in collection]

    context = {
        'bundle': bundle,
        **common_context,
        'form': form,
        'articles_new': get_articles_for_view(bundle.articles.filter(
            status=Article.STATUS_NEW
        ).order_by('url_name')),
        'articles_changed': get_articles_for_view(bundle.articles.filter(
            status=Article.STATUS_CHANGED
        ).order_by('url_name')),
        'articles_deleted': get_articles_for_view(bundle.articles.filter(
            status=Article.STATUS_DELETED
        ).order_by('url_name')),
        'images_new': bundle.images.filter(
            status=Image.STATUS_NEW
        ).order_by('filename'),
        'images_changed': bundle.images.filter(
            status=Image.STATUS_CHANGED
        ).order_by('filename'),
        'images_deleted': bundle.images.filter(
            status=Image.STATUS_DELETED
        ).order_by('filename'),
    }
    return render(request, 'publish.html', context=context)


@never_cache
@csrf_exempt
@require_POST
def webhook(request):
    """Receive webhook from easyDITA."""
    webhook = Webhook.objects.create(body=request.body.decode('utf-8'))
    process_webhook.delay(webhook.pk)
    return HttpResponse('OK')
