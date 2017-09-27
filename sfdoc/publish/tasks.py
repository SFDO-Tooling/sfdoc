from tempfile import TemporaryDirectory

import django_rq

from .models import EasyditaBundle


@django_rq.job
def process_easydita_bundle(pk):
    easydita_bundle = EasyditaBundle.objects.get(pk=pk)
    with TemporaryDirectory() as d:
        easydita_bundle.download(d)
