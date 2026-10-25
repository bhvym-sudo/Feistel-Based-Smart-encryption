import asyncio
from io import BytesIO

import httpx
from openpyxl import load_workbook

from app.main import app


async def _request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def request(method: str, path: str, **kwargs):
    # Starlette's threaded TestClient currently hangs on Python 3.14; the
    # native async ASGI transport exercises the same application directly.
    return asyncio.run(_request(method, path, **kwargs))


def test_dashboard_and_health():
    response = request("GET", "/")
    assert response.status_code == 200
    assert "Feistel Smart Meter Simulator" in response.text
    assert request("GET", "/api/health").json()["status"] == "ok"


def test_encrypt_decrypt_api():
    encrypted = request("POST", "/api/cipher/encrypt", json={
        "plaintext": 124,
        "key": 0xBEEF,
        "rounds": 6,
    })
    assert encrypted.status_code == 200
    body = encrypted.json()
    assert len(body["trace"]) == 6

    decrypted = request("POST", "/api/cipher/decrypt", json={
        "ciphertext": body["ciphertext"],
        "key": 0xBEEF,
        "rounds": 6,
    })
    assert decrypted.status_code == 200
    assert decrypted.json()["plaintext"] == 124


def test_readings_and_packet_api():
    readings = request("GET", "/api/readings?count=12&interval_minutes=15&seed=3")
    assert readings.status_code == 200
    assert len(readings.json()["readings"]) == 12

    packet = request("POST", "/api/packet/simulate", json={
        "plaintext": 88,
        "key": 0xBEEF,
        "rounds": 6,
        "meter_id": "SM-TEST",
        "sequence": 1,
        "iv": 90,
    })
    assert packet.status_code == 200
    assert packet.json()["integrity_valid"] is True
    assert packet.json()["sequence_valid"] is True
    assert packet.json()["recovered_plaintext"] == 88

    tampered = request("POST", "/api/packet/simulate", json={
        "plaintext": 88,
        "key": 0xBEEF,
        "rounds": 6,
        "meter_id": "SM-TEST",
        "sequence": 1,
        "iv": 90,
        "attack_mode": "tamper",
    })
    assert tampered.status_code == 200
    assert tampered.json()["accepted"] is False
    assert tampered.json()["integrity_valid"] is False

    replayed = request("POST", "/api/packet/simulate", json={
        "plaintext": 88,
        "key": 0xBEEF,
        "rounds": 6,
        "meter_id": "SM-TEST",
        "sequence": 1,
        "iv": 90,
        "attack_mode": "replay",
    })
    assert replayed.status_code == 200
    assert replayed.json()["accepted"] is False
    assert replayed.json()["integrity_valid"] is True
    assert replayed.json()["sequence_valid"] is False


def test_validation_rejects_bad_round_count():
    response = request("POST", "/api/cipher/encrypt", json={
        "plaintext": 10,
        "key": 20,
        "rounds": 5,
    })
    assert response.status_code == 422


def test_analysis_api_compares_all_round_counts():
    response = request("POST", "/api/analysis/run", json={
        "key": 0xBEEF,
        "samples": 16,
        "iterations": 1000,
        "voltage": 3.3,
        "active_current_ma": 8,
    })
    assert response.status_code == 200
    body = response.json()
    assert [item["rounds"] for item in body["configurations"]] == [4, 6, 8]
    for item in body["configurations"]:
        assert len(item["avalanche"]["heatmap"]) == 8
        assert item["timing"]["minimum_us"] <= item["timing"]["maximum_us"]
        assert item["timing"]["standard_deviation_us"] >= 0
        assert item["energy_estimate"]["estimated_power_mw"] == 26.4


def test_excel_export_downloads_valid_workbook():
    response = request("GET", "/api/automation/export.xlsx")
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.headers["content-disposition"].endswith('.xlsx"')

    workbook = load_workbook(BytesIO(response.content))
    sheet = workbook["Automation Data"]
    assert sheet.freeze_panes == "A2"
    assert sheet["A1"].value == "ID"
    assert sheet["N1"].value == "Integrity"
    workbook.close()

