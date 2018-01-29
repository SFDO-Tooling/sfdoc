import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils.timezone import now
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import PublishToProductionForm
from .models import EasyditaBundle
from .tasks import process_easydita_bundle
from .tasks import publish_drafts


@never_cache
@csrf_exempt
@require_POST
def webhook(request):
    """Receive webhook from easyDITA."""
    data = json.loads(request.body.decode('utf-8'))
    easydita_id = data['resource_id']
    mgr = EasyditaBundle.objects
    easydita_bundle, created = mgr.get_or_create(easydita_id=easydita_id)
    if created or easydita_bundle.status == EasyditaBundle.STATUS_PUBLISHED:
        easydita_bundle.time_last_received = now()
        easydita_bundle.status = EasyditaBundle.STATUS_NEW
        easydita_bundle.save()
        qs_other = mgr.exclude(pk=easydita_bundle.pk)
        qs_published = mgr.filter(status=EasyditaBundle.STATUS_PUBLISHED)
        if qs_other.count() == qs_published.count():
            # all other bundles are published, process this one immediately
            process_easydita_bundle.delay(easydita_bundle.pk)
        return HttpResponse('OK')
    else:
        return HttpResponseForbidden(
            'easyDITA bundle (ID={}) is already being processed.'.format(
                easydita_id=easydita_id,
            )
        )


@never_cache
@login_required
def publish_to_production(request, easydita_bundle_id):
    """Run the publish flow against the production Salesforce org."""
    easydita_bundle = get_object_or_404(
        EasyditaBundle,
        easydita_id=easydita_bundle_id,
    )
    context = {
        'easydita_bundle_id': easydita_bundle.easydita_id,
    }
    if easydita_bundle.status == EasyditaBundle.STATUS_NEW:
        template = 'publish_incomplete.html'
    elif easydita_bundle.status == EasyditaBundle.STATUS_DRAFT:
        template = 'publish_to_production.html'
        if request.method == 'POST':
            form = PublishToProductionForm(request.POST)
            if form.is_valid():
                publish_drafts.delay(easydita_bundle.pk)
                easydita_bundle.status = EasyditaBundle.STATUS_PUBLISHING
                easydita_bundle.save()
                return HttpResponseRedirect('confirmed/')
        else:
            form = PublishToProductionForm()
        context['form'] = form
    elif easydita_bundle.status == EasyditaBundle.STATUS_PUBLISHING:
        template = 'publishing.html'
    elif easydita_bundle.status == EasyditaBundle.STATUS_PUBLISHED:
        template = 'published.html'
    return render(request, template, context=context)


@never_cache
@login_required
def publish_to_production_confirmation(request, easydita_bundle_id):
    """Confirm the bundle is being published to production."""
    easydita_bundle = get_object_or_404(
        EasyditaBundle,
        easydita_id=easydita_bundle_id,
    )
    context = {
        'easydita_bundle_id': easydita_bundle.easydita_id,
    }
    if easydita_bundle.status == EasyditaBundle.STATUS_NEW:
        template = 'publish_incomplete.html'
    elif easydita_bundle.status == EasyditaBundle.STATUS_DRAFT:
        return HttpResponseRedirect('../')
    elif easydita_bundle.status == EasyditaBundle.STATUS_PUBLISHING:
        template = 'publishing.html'
    elif easydita_bundle.status == EasyditaBundle.STATUS_PUBLISHED:
        template = 'published.html'
    return render(request, template, context=context)


@never_cache
@login_required
def bundle_status(request, easydita_bundle_id):
    easydita_bundle = get_object_or_404(
        EasyditaBundle,
        easydita_id=easydita_bundle_id,
    )
    context = {'bundle': easydita_bundle}
    return render(request, 'status.html', context=context)


@never_cache
@login_required
def queue_status(request):
    mgr = EasyditaBundle.objects
    if not mgr.count():
        return render(request, 'no_bundles.html')
    qs = mgr.exclude(status=EasyditaBundle.STATUS_PUBLISHED)
    if not qs:
        return render(request, 'all_published.html')
    qs_new = qs.filter(status=EasyditaBundle.STATUS_NEW)
    qs_notnew = qs.exclude(status=EasyditaBundle.STATUS_NEW)
    if qs_notnew.count() > 1:
        raise Exception('Expected only 1 bundle processing')
    bundle = qs_notnew.get() if qs_notnew else None
    context = {
        'bundle': bundle,
        'queue': qs_new.order_by('time_last_received'),
    }
    return render(request, 'queue_status.html', context=context)
