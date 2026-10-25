from datetime import datetime, timezone

import pytest

from app.core.data_generator import ResidentialLoadGenerator
from app.core.packet import MeterPacket, PacketService


def test_generator_returns_valid_readings():
    readings = ResidentialLoadGenerator().generate(48, 15, 42, "SM-TEST")
    assert len(readings) == 48
    assert [item.sequence for item in readings] == list(range(1, 49))
    assert all(0 <= item.quantized_value <= 255 for item in readings)
    assert all(item.power_kw > 0 for item in readings)
    assert all(item.meter_id == "SM-TEST" for item in readings)


def test_packet_round_trip_and_integrity():
    service = PacketService(0xBEEF, b"independent-test-key", 6)
    packet = service.create_packet(124, "SM-TEST", 8, 0x5A, datetime.now(timezone.utc))
    assert service.verify(packet)
    assert service.decrypt_packet(packet) == 124

    altered = MeterPacket(**{**packet.to_dict(), "ciphertext": packet.ciphertext ^ 1})
    assert not service.verify(altered)
    with pytest.raises(ValueError):
        service.decrypt_packet(altered)

