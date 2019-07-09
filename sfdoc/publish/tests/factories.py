from datetime import datetime

from django.utils import timezone

import factory
from .. import models

from faker.generator import random

random.seed(0xDEADBEEF)


class BundleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Bundle
    easydita_id = factory.Faker('first_name')
    easydita_resource_id = factory.Faker('last_name')
    time_queued = factory.LazyFunction(timezone.now)
