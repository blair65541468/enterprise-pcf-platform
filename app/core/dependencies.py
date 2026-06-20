from app.core.clock import Clock, SystemClock
from app.engines import get_calculation_engine
from app.engines.base import CalculationEngine
from app.storage import ObjectStorage, get_storage


def calculation_engine() -> CalculationEngine:
    return get_calculation_engine()


def object_storage() -> ObjectStorage:
    return get_storage()


def clock() -> Clock:
    return SystemClock()
