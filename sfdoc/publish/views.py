import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import EasyditaBundle


@csrf_exempt
@require_POST
def webhook(request):
    data = json.loads(request.body.decode('utf-8'))
    EasyditaBundle.objects.get_or_create(easydita_id=data['resource_id'])
    return HttpResponse('OK')
