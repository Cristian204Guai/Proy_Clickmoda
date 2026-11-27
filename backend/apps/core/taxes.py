"""Utilidades tributarias compartidas (IVA incluido en el precio de venta)."""
from decimal import ROUND_HALF_UP, Decimal

IVA_TARIFA_GENERAL = 19


def base_sin_iva(monto_con_iva, tarifa=IVA_TARIFA_GENERAL, exponente: str = "0.01") -> Decimal:
    """Devuelve la base gravable de un monto que YA incluye IVA: monto / (1 + tarifa/100)."""
    monto = Decimal(monto_con_iva)
    if monto <= 0:
        return Decimal("0").quantize(Decimal(exponente))
    factor = Decimal("1") + Decimal(tarifa) / Decimal("100")
    return (monto / factor).quantize(Decimal(exponente), rounding=ROUND_HALF_UP)


def iva_incluido(monto_con_iva, tarifa=IVA_TARIFA_GENERAL, exponente: str = "1") -> Decimal:
    """IVA contenido en un monto con IVA incluido (monto - base)."""
    monto = Decimal(monto_con_iva)
    if monto <= 0:
        return Decimal("0").quantize(Decimal(exponente))
    return monto - base_sin_iva(monto, tarifa, exponente)
