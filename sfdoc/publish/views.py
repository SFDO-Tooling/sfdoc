import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import PublishToProductionForm
from .models import EasyditaBundle
from .tasks import process_easydita_bundle


@csrf_exempt
@require_POST
def webhook(request):
    """Receive webhook from easyDITA."""
    data = json.loads(request.body.decode('utf-8'))
    easydita_bundle, created = EasyditaBundle.objects.update_or_create(
        easydita_id=data['resource_id'],
        defaults={
            'complete_production': False,
            'complete_review': False,
            'time_last_received': now(),
        },
    )
    process_easydita_bundle.delay(easydita_bundle.pk, production=False)
    return HttpResponse('OK')


@login_required
def publish_to_production(request, easydita_bundle_id):
    """Run the publish flow against the production Salesforce org."""
    easydita_bundle = get_object_or_404(
        EasyditaBundle,
        easydita_id=easydita_bundle_id,
    )
    if request.method == 'POST':
        form = PublishToProductionForm(request.POST)
        if form.is_valid():
            process_easydita_bundle.delay(easydita_bundle.pk, production=True)
            return HttpResponseRedirect('confirmed/')
    else:
        form = PublishToProductionForm()
    context = {
        'easydita_bundle_id': easydita_bundle.easydita_id,
        'form': form,
    }
    return render(request, 'publish_to_production.html', context=context)


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
    if not easydita_bundle.complete_review:
        return render(request, 'publish_incomplete.html', context=context)
    return render(request, 'publish_confirmed.html', context=context)
