"""Educational 8-bit Feistel cipher.

This module is deliberately small and explicit so students can inspect every
operation. It is not intended for production cryptography.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


SBOX: tuple[int, ...] = (
    0xC, 0x5, 0x6, 0xB,
    0x9, 0x0, 0xA, 0xD,
    0x3, 0xE, 0xF, 0x8,
    0x4, 0x7, 0x1, 0x2,
)


@dataclass(frozen=True)
class RoundTrace:
    round: int
    subkey: int
    left_in: int
    right_in: int
    xor_input: int
    sbox_output: int
    permutation_output: int
    left_out: int
    right_out: int

    def to_dict(self) -> dict[str, int | str]:
        data: dict[str, int | str] = asdict(self)
        for field in (
            "subkey", "left_in", "right_in", "xor_input", "sbox_output",
            "permutation_output", "left_out", "right_out",
        ):
            data[f"{field}_bits"] = f"{getattr(self, field):04b}"
        return data


class FeistelCipher:
    """Balanced Feistel network with two 4-bit halves."""

    valid_rounds = (4, 6, 8)

    def __init__(self, key: int, rounds: int = 6) -> None:
        if not 0 <= key <= 0xFFFF:
            raise ValueError("key must be a 16-bit integer")
        if rounds not in self.valid_rounds:
            raise ValueError(f"rounds must be one of {self.valid_rounds}")
        self.key = key
        self.rounds = rounds
        self.subkeys = self._derive_subkeys()

    @staticmethod
    def _rotate_left_16(value: int, shift: int) -> int:
        shift %= 16
        return ((value << shift) | (value >> (16 - shift))) & 0xFFFF

    def _derive_subkeys(self) -> tuple[int, ...]:
        """Rotate cumulatively, then select the low nibble for each round."""
        working_key = self.key
        keys: list[int] = []
        for round_index in range(self.rounds):
            working_key = self._rotate_left_16(working_key, round_index + 1)
            keys.append(working_key & 0xF)
        return tuple(keys)

    @staticmethod
    def _permute(value: int) -> int:
        """Map input bit positions [3,2,1,0] to output [2,0,3,1]."""
        b3 = (value >> 3) & 1
        b2 = (value >> 2) & 1
        b1 = (value >> 1) & 1
        b0 = value & 1
        return (b2 << 3) | (b0 << 2) | (b3 << 1) | b1

    @classmethod
    def round_function(cls, right: int, subkey: int) -> tuple[int, int, int]:
        xor_input = (right ^ subkey) & 0xF
        substituted = SBOX[xor_input]
        permuted = cls._permute(substituted)
        return xor_input, substituted, permuted

    def encrypt(self, plaintext: int, *, trace: bool = False):
        if not 0 <= plaintext <= 0xFF:
            raise ValueError("plaintext must be an 8-bit integer")
        left, right = (plaintext >> 4) & 0xF, plaintext & 0xF
        traces: list[RoundTrace] = []

        for index, subkey in enumerate(self.subkeys, start=1):
            left_in, right_in = left, right
            xor_input, substituted, permuted = self.round_function(right, subkey)
            left, right = right, left ^ permuted
            traces.append(RoundTrace(
                index, subkey, left_in, right_in, xor_input, substituted,
                permuted, left, right,
            ))

        ciphertext = (left << 4) | right
        return (ciphertext, traces) if trace else ciphertext

    def decrypt(self, ciphertext: int) -> int:
        if not 0 <= ciphertext <= 0xFF:
            raise ValueError("ciphertext must be an 8-bit integer")
        left, right = (ciphertext >> 4) & 0xF, ciphertext & 0xF

        # Inverse of (L, R) -> (R, L XOR F(R, K)).
        for subkey in reversed(self.subkeys):
            previous_right = left
            _, _, function_output = self.round_function(previous_right, subkey)
            previous_left = right ^ function_output
            left, right = previous_left, previous_right

        return (left << 4) | right


def hamming_distance(first: int, second: int) -> int:
    """Count differing bits in two 8-bit values."""
    return ((first ^ second) & 0xFF).bit_count()

