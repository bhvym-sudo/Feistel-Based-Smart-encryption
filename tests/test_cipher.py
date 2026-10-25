import pytest

from app.core.cipher import FeistelCipher, hamming_distance


@pytest.mark.parametrize("rounds", [4, 6, 8])
@pytest.mark.parametrize("key", [0x0000, 0x0001, 0xBEEF, 0xFFFF])
def test_all_plaintexts_round_trip(rounds, key):
    cipher = FeistelCipher(key, rounds)
    for plaintext in range(256):
        assert cipher.decrypt(cipher.encrypt(plaintext)) == plaintext


def test_trace_contains_one_entry_per_round():
    cipher = FeistelCipher(0xBEEF, 6)
    ciphertext, trace = cipher.encrypt(0x7C, trace=True)
    assert 0 <= ciphertext <= 255
    assert len(trace) == 6
    assert trace[0].left_in == 0x7
    assert trace[0].right_in == 0xC


def test_invalid_values_are_rejected():
    with pytest.raises(ValueError):
        FeistelCipher(0x10000, 6)
    with pytest.raises(ValueError):
        FeistelCipher(0xBEEF, 5)
    with pytest.raises(ValueError):
        FeistelCipher(0xBEEF, 6).encrypt(256)


def test_hamming_distance():
    assert hamming_distance(0b00000000, 0b11111111) == 8
    assert hamming_distance(0b10101010, 0b10101011) == 1

