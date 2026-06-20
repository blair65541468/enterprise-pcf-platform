from app.config import settings
from app.engines.base import CalculationEngine
from app.engines.mock import MockCalculationEngine
from app.engines.openlca import OpenLcaRestEngine


def get_calculation_engine() -> CalculationEngine:
    if settings.openlca_engine == "rest":
        return OpenLcaRestEngine()
    return MockCalculationEngine()

