# -*- encoding: utf-8 -*-
from decimal import Decimal
from faker import Factory
from geoposition import Geoposition


def generate_geoposition(latitude=None, longitude=None):
    """
    Generate a random geo-position or set the point from arguments
    """
    faker = Factory.create()

    try:
        latitude = Decimal(latitude)
        longitude = Decimal(longitude)
    except (ValueError, TypeError):
        latitude = faker.latitude()
        longitude = faker.longitude()
    return Geoposition(latitude, longitude)


MOMMY_GEO_FIELDS = {
    "geoposition.fields.GeopositionField": generate_geoposition,
}
