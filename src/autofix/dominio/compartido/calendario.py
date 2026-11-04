"""Domain Service: cálculo de días hábiles (BRD: plazo de 3 días hábiles para refacciones)."""
from __future__ import annotations

from datetime import date, timedelta


class CalendarioHabil:
    """Cuenta días hábiles (lunes a viernes). Los días festivos quedan fuera de esta fase."""

    def dias_habiles_entre(self, inicio: date, fin: date) -> int:
        if fin <= inicio:
            return 0
        dias, actual = 0, inicio
        while actual < fin:
            actual += timedelta(days=1)
            if actual.weekday() < 5:
                dias += 1
        return dias
