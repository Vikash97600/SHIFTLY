from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver
import math

def haversine_sql(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        R = 6371.0  # Earth's radius in km
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except Exception:
        return None

@receiver(connection_created)
def extend_sqlite(connection, **kwargs):
    if connection.vendor == 'sqlite':
        connection.connection.create_function("haversine", 4, haversine_sql)

class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jobs"

    def ready(self):
        pass

