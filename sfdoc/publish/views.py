import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import PublishToProductionForm
from .models import EasyditaBundle
from .models import Webhook
from .tasks import process_queue
from .tasks import process_webhook
from .tasks import publish_drafts

logger = logging.getLogger(__name__)


@never_cache
@login_required
def bundle(request, pk):
    easydita_bundle = get_object_or_404(EasyditaBundle, pk=pk)
    context = {'bundle': easydita_bundle}
    if easydita_bundle.status == EasyditaBundle.STATUS_DRAFT:
        if request.method == 'POST':
            form = PublishToProductionForm(request.POST)
            if form.is_valid():
                if form.approved():
                    easydita_bundle.status = EasyditaBundle.STATUS_PUBLISHING
                    easydita_bundle.save()
                    publish_drafts.delay(easydita_bundle.pk)
                else:
                    easydita_bundle.status = EasyditaBundle.STATUS_REJECTED
                    easydita_bundle.save()
                    process_queue.delay()
            return HttpResponseRedirect('./')
        else:
            form = PublishToProductionForm()
        context['articles'] = easydita_bundle.articles.all()
        context['form'] = form
        return render(request, 'publish_form.html', context=context)
    else:
        return render(request, 'bundle.html', context=context)


@never_cache
@login_required
def bundles(request):
    context = {'bundles': EasyditaBundle.objects.all().order_by('pk')}
    return render(request, 'bundles.html', context=context)


@never_cache
@login_required
def queue(request):
    qs_processing = EasyditaBundle.objects.filter(status__in=(
        EasyditaBundle.STATUS_PROCESSING,
        EasyditaBundle.STATUS_DRAFT,
        EasyditaBundle.STATUS_PUBLISHING,
    ))
    qs_queued = EasyditaBundle.objects.filter(
        status=EasyditaBundle.STATUS_QUEUED,
    )
    context = {
        'processing': qs_processing.order_by('time_queued'),
        'queued': qs_queued.order_by('time_queued'),
    }
    return render(request, 'queue.html', context=context)


@never_cache
@csrf_exempt
@require_POST
def webhook(request):
    """Receive webhook from easyDITA."""
    webhook = Webhook.objects.create(body=request.body)
    process_webhook.delay(webhook.pk)
    return HttpResponse('OK')
