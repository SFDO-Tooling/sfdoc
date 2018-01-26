import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
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
    easydita_bundle, created = EasyditaBundle.objects.update_or_create(
        easydita_id=data['resource_id'],
        defaults={
            'status': EasyditaBundle.STATUS_NEW,
            'time_last_received': now(),
        },
    )
    process_easydita_bundle.delay(easydita_bundle.pk)
    return HttpResponse('OK')


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
    if easydita_bundle.status == easydita_bundle.STATUS_NEW:
        template = 'publish_incomplete.html'
    elif easydita_bundle.status == easydita_bundle.STATUS_DRAFT:
        template = 'publish_to_production.html'
        if request.method == 'POST':
            form = PublishToProductionForm(request.POST)
            if form.is_valid():
                publish_drafts.delay(easydita_bundle.pk)
                easydita_bundle.status = easydita_bundle.STATUS_PUBLISHING
                easydita_bundle.save()
                return HttpResponseRedirect('confirmed/')
        else:
            form = PublishToProductionForm()
        context['form'] = form
    elif easydita_bundle.status == easydita_bundle.STATUS_PUBLISHING:
        template = 'publishing.html'
    elif easydita_bundle.status == easydita_bundle.STATUS_PUBLISHED:
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
    if easydita_bundle.status == easydita_bundle.STATUS_NEW:
        template = 'publish_incomplete.html'
    elif easydita_bundle.status == easydita_bundle.STATUS_DRAFT:
        return HttpResponseRedirect('../')
    elif easydita_bundle.status == easydita_bundle.STATUS_PUBLISHING:
        template = 'publishing.html'
    elif easydita_bundle.status == easydita_bundle.STATUS_PUBLISHED:
        template = 'published.html'
    return render(request, template, context=context)
