"""Meter packet framing, chaining and integrity helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from datetime import datetime

from .cipher import FeistelCipher


@dataclass(frozen=True)
class MeterPacket:
    meter_id: str
    timestamp: str
    sequence: int
    iv: int
    ciphertext: int
    tag: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _authenticated_bytes(packet_fields: dict[str, object]) -> bytes:
    return json.dumps(packet_fields, sort_keys=True, separators=(",", ":")).encode()


class PacketService:
    def __init__(self, encryption_key: int, integrity_key: bytes, rounds: int = 6) -> None:
        self.cipher = FeistelCipher(encryption_key, rounds)
        self.integrity_key = integrity_key

    def create_packet(
        self,
        plaintext: int,
        meter_id: str,
        sequence: int,
        iv: int,
        timestamp: datetime | None = None,
    ) -> MeterPacket:
        timestamp = timestamp or datetime.now().astimezone()
        ciphertext = self.cipher.encrypt(plaintext ^ iv)
        fields: dict[str, object] = {
            "meter_id": meter_id,
            "timestamp": timestamp.isoformat(),
            "sequence": sequence,
            "iv": iv,
            "ciphertext": ciphertext,
        }
        tag = hmac.new(self.integrity_key, _authenticated_bytes(fields), hashlib.sha256).hexdigest()[:8]
        return MeterPacket(tag=tag, **fields)

    def verify(self, packet: MeterPacket) -> bool:
        fields = packet.to_dict()
        supplied = str(fields.pop("tag"))
        expected = hmac.new(
            self.integrity_key,
            _authenticated_bytes(fields),
            hashlib.sha256,
        ).hexdigest()[:8]
        return hmac.compare_digest(supplied, expected)

    def decrypt_packet(self, packet: MeterPacket) -> int:
        if not self.verify(packet):
            raise ValueError("packet integrity check failed")
        return self.cipher.decrypt(packet.ciphertext) ^ packet.iv

