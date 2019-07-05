import factory
from .. import models


class BundleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Bundle
