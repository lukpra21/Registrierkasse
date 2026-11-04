"""Geldbeträge werden intern ausschließlich als ganzzahlige Cent geführt."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def euro_zu_cent(wert: float | str | Decimal) -> int:
    """Wandelt einen Eurobetrag (z. B. 12.5, "12,50") kaufmännisch gerundet in Cent um."""
    if isinstance(wert, str):
        wert = wert.strip().replace(".", "").replace(",", ".") if "," in wert else wert.strip()
    d = Decimal(str(wert)) * 100
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def rksv_betrag(cent: int) -> str:
    """Format laut RKSV-Detailspezifikation: Komma als Dezimaltrenner, zwei Nachkommastellen."""
    vorzeichen = "-" if cent < 0 else ""
    cent = abs(cent)
    return f"{vorzeichen}{cent // 100},{cent % 100:02d}"


def anzeige(cent: int) -> str:
    """Anzeige für Bon/Rechnung, z. B. 1.234,50."""
    vorzeichen = "-" if cent < 0 else ""
    cent = abs(cent)
    euro = f"{cent // 100:,}".replace(",", ".")
    return f"{vorzeichen}{euro},{cent % 100:02d}"


def netto_aus_brutto(brutto_cent: int, prozent: Decimal | float) -> int:
    p = Decimal(str(prozent))
    netto = Decimal(brutto_cent) * 100 / (100 + p)
    return int(netto.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
