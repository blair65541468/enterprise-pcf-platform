from decimal import Decimal


class UnitConversionError(ValueError):
    pass


def convert_activity_amount(
    *,
    quantity: Decimal,
    weight_kg_each: Decimal,
    activity_unit: str,
    density_kg_m3: Decimal | None,
) -> Decimal:
    mass_kg = quantity * weight_kg_each
    normalized = activity_unit.strip().lower()
    if normalized in {"kg", "kilogram"}:
        return mass_kg
    if normalized in {"m³", "m3"}:
        if density_kg_m3 is None or density_kg_m3 <= 0:
            raise UnitConversionError("kg to m³ conversion requires positive density_kg_m3")
        return mass_kg / density_kg_m3
    raise UnitConversionError(f"no explicit conversion rule from kg to {activity_unit}")
