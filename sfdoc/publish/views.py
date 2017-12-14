import json

from django.http import HttpResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import EasyditaBundle
from .tasks import process_easydita_bundle


@csrf_exempt
@require_POST
def webhook(request):
    data = json.loads(request.body.decode('utf-8'))
    easydita_bundle, created = EasyditaBundle.objects.update_or_create(
        easydita_id=data['resource_id'],
        defaults={'last_received': now()},
    )
    process_easydita_bundle.delay(easydita_bundle.pk)
    return HttpResponse('OK')
