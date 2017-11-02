import os
from tempfile import TemporaryDirectory

from django.core.files import File
import django_rq

from .models import EasyditaBundle


@django_rq.job
def process_easydita_bundle(pk):
    easydita_bundle = EasyditaBundle.objects.get(pk=pk)
    with TemporaryDirectory() as d:
        easydita_bundle.download(d)
        for dirpath, dirnames, filenames in os.walk(d):
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if ext.lower() in ('.jpg', '.png'):
                    with open(os.path.join(dirpath, filename), 'rb') as f:
                        image_data = f.read()
                        image_file = File(f)
                    image, created = Image.objects.get_or_create(
                        image_hash=hash(image_data),
                        defaults={'image_file': image_file},
                    )
    return 'Processed easyDITA bundle pk={}'.format(pk)
