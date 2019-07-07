from datetime import datetime

import factory
from .. import models


class BundleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Bundle
    easydita_id = factory.Faker('first_name')
    easydita_resource_id = factory.Faker('last_name')
    time_queued = factory.LazyFunction(datetime.now)
