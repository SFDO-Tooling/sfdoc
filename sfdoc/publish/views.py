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
from .tasks import process_webhook
from .tasks import publish_drafts


@never_cache
@login_required
def bundle(request, pk):
    easydita_bundle = get_object_or_404(EasyditaBundle, pk=pk)
    context = {'bundle': easydita_bundle}
    if easydita_bundle.status == EasyditaBundle.STATUS_DRAFT:
        if request.method == 'POST':
            form = PublishToProductionForm(request.POST)
            if form.is_valid():
                if form.accepted():
                    publish_drafts.delay(easydita_bundle.pk)
                    easydita_bundle.status = EasyditaBundle.STATUS_PUBLISHING
                else:
                    easydita_bundle.status = EasyditaBundle.STATUS_REJECTED
                easydita_bundle.save()
            return HttpResponseRedirect('./')
        else:
            form = PublishToProductionForm()
        context['form'] = form
        return render(request, 'publish_form.html', context=context)
    else:
        return render(request, 'status.html', context=context)


@never_cache
@login_required
def queue(request):
    if not EasyditaBundle.objects.count():
        return render(request, 'no_bundles.html')
    if not EasyditaBundle.objects.exclude(status__in=(
        EasyditaBundle.STATUS_REJECTED,
        EasyditaBundle.STATUS_PUBLISHED,
    )):
        return render(request, 'all_complete.html')
    qs_queued = EasyditaBundle.objects.filter(
        status=EasyditaBundle.STATUS_QUEUED,
    )
    qs_processing = EasyditaBundle.objects.filter(status__in=(
        EasyditaBundle.STATUS_PROCESSING,
        EasyditaBundle.STATUS_DRAFT,
        EasyditaBundle.STATUS_PUBLISHING,
    ))
    qs_rejected = EasyditaBundle.objects.filter(
        status=EasyditaBundle.STATUS_REJECTED,
    )
    qs_published = EasyditaBundle.objects.filter(
        status=EasyditaBundle.STATUS_PUBLISHED,
    )
    if qs_processing.count() > 1:
        raise Exception('Expected only 1 bundle processing')
    context = {
        'bundle': qs_processing.get() if qs_processing else None,
        'queued': qs_queued.order_by('time_queued'),
        'rejected': qs_rejected.order_by('time_queued'),
        'published': qs_published.order_by('time_queued'),
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
