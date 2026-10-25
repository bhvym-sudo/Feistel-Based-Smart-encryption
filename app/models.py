"""API request models and validation rules."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CipherRequest(BaseModel):
    plaintext: int = Field(ge=0, le=255)
    key: int = Field(default=0xBEEF, ge=0, le=0xFFFF)
    rounds: int = 6

    @field_validator("rounds")
    @classmethod
    def validate_rounds(cls, value: int) -> int:
        if value not in (4, 6, 8):
            raise ValueError("rounds must be 4, 6, or 8")
        return value


class DecryptRequest(BaseModel):
    ciphertext: int = Field(ge=0, le=255)
    key: int = Field(default=0xBEEF, ge=0, le=0xFFFF)
    rounds: int = 6

    @field_validator("rounds")
    @classmethod
    def validate_rounds(cls, value: int) -> int:
        if value not in (4, 6, 8):
            raise ValueError("rounds must be 4, 6, or 8")
        return value


class PacketRequest(CipherRequest):
    meter_id: str = Field(default="SM-2048", min_length=2, max_length=32)
    sequence: int = Field(default=1, ge=0)
    iv: int = Field(default=0x5A, ge=0, le=255)
    attack_mode: Literal["none", "tamper", "replay"] = "none"


class AnalysisRequest(BaseModel):
    key: int = Field(default=0xBEEF, ge=0, le=0xFFFF)
    samples: int = Field(default=128, ge=16, le=512)
    iterations: int = Field(default=20_000, ge=1_000, le=200_000)
    voltage: float = Field(default=3.3, gt=0, le=12)
    active_current_ma: float = Field(default=8.0, gt=0, le=500)


class AutomationStartRequest(BaseModel):
    key: int = Field(default=0xBEEF, ge=0, le=0xFFFF)
    rounds: int = 6
    interval_seconds: float = Field(default=2.0, ge=0.5, le=30)
    meter_id: str = Field(default="SM-2048", min_length=2, max_length=32)

    @field_validator("rounds")
    @classmethod
    def validate_rounds(cls, value: int) -> int:
        if value not in (4, 6, 8):
            raise ValueError("rounds must be 4, 6, or 8")
        return value

