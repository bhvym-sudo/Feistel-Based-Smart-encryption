"""Replaceable smart-meter data generators.

Team members can implement ``ReadingGenerator`` and register their generator in
``app/main.py`` without changing the API or frontend.
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol


@dataclass(frozen=True)
class MeterReading:
    meter_id: str
    timestamp: datetime
    sequence: int
    usage_kwh: float
    power_kw: float
    voltage: float
    current: float
    quantized_value: int

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


class ReadingGenerator(Protocol):
    def generate(
        self,
        count: int,
        interval_minutes: int,
        seed: int,
        meter_id: str,
    ) -> list[MeterReading]: ...


class ResidentialLoadGenerator:
    """Creates a repeatable household profile with peaks and appliance events."""

    def __init__(self, maximum_interval_kwh: float = 2.0) -> None:
        self.maximum_interval_kwh = maximum_interval_kwh

    @staticmethod
    def _peak(hour: float, centre: float, width: float, height: float) -> float:
        return height * math.exp(-0.5 * ((hour - centre) / width) ** 2)

    def generate(
        self,
        count: int = 96,
        interval_minutes: int = 15,
        seed: int = 42,
        meter_id: str = "SM-2048",
    ) -> list[MeterReading]:
        if not 1 <= count <= 500:
            raise ValueError("count must be between 1 and 500")
        if interval_minutes not in (5, 10, 15, 30, 60):
            raise ValueError("unsupported interval")

        rng = random.Random(seed)
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        start = now - timedelta(minutes=interval_minutes * (count - 1))
        readings: list[MeterReading] = []

        for sequence in range(1, count + 1):
            timestamp = start + timedelta(minutes=(sequence - 1) * interval_minutes)
            hour = timestamp.hour + timestamp.minute / 60
            base_kw = 0.22
            morning_kw = self._peak(hour, 7.5, 1.35, 1.25)
            evening_kw = self._peak(hour, 19.5, 2.1, 1.85)
            daytime_kw = self._peak(hour, 13.0, 3.6, 0.38)
            appliance_kw = rng.uniform(0.5, 1.6) if rng.random() < 0.07 else 0.0
            noise_kw = rng.uniform(-0.08, 0.08)
            power_kw = max(0.08, base_kw + morning_kw + evening_kw + daytime_kw + appliance_kw + noise_kw)
            usage_kwh = power_kw * interval_minutes / 60
            voltage = 230 + rng.uniform(-4.5, 4.5)
            current = power_kw * 1000 / voltage
            quantized = round(min(usage_kwh, self.maximum_interval_kwh) / self.maximum_interval_kwh * 255)

            readings.append(MeterReading(
                meter_id=meter_id,
                timestamp=timestamp,
                sequence=sequence,
                usage_kwh=round(usage_kwh, 4),
                power_kw=round(power_kw, 3),
                voltage=round(voltage, 1),
                current=round(current, 2),
                quantized_value=max(0, min(255, quantized)),
            ))

        return readings

