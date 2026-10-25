"""FastAPI entry point for the smart-meter encryption suite."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.cipher import FeistelCipher
from app.core.data_generator import ReadingGenerator, ResidentialLoadGenerator
from app.core.packet import MeterPacket, PacketService
from app.models import (
    AnalysisRequest,
    AutomationStartRequest,
    CipherRequest,
    DecryptRequest,
    PacketRequest,
)
from app.services.analysis import (
    benchmark_cipher,
    estimate_energy,
    run_avalanche_analysis,
    run_key_sensitivity,
)
from app.services.automation import AutomationService
from app.services.excel_export import create_automation_workbook


BASE_DIR = Path(__file__).resolve().parent

# Replace this object with another ReadingGenerator implementation when a
# teammate delivers a new data-generation model.
reading_generator: ReadingGenerator = ResidentialLoadGenerator()
automation_service = AutomationService(reading_generator, BASE_DIR.parent / "data" / "automation.db")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await automation_service.stop()


app = FastAPI(
    title="FeistelGrid Lab API",
    version="1.0.0",
    description="Educational 8-bit Feistel cipher and smart-meter telemetry simulator.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "FeistelGrid Lab"}


@app.get("/api/readings")
async def readings(
    count: int = Query(default=96, ge=1, le=500),
    interval_minutes: int = Query(default=15),
    seed: int = Query(default=42),
    meter_id: str = Query(default="SM-2048", min_length=2, max_length=32),
) -> dict[str, object]:
    generated = reading_generator.generate(count, interval_minutes, seed, meter_id)
    return {
        "meter_id": meter_id,
        "interval_minutes": interval_minutes,
        "count": len(generated),
        "readings": [reading.to_dict() for reading in generated],
    }


@app.post("/api/cipher/encrypt")
async def encrypt(payload: CipherRequest) -> dict[str, object]:
    cipher = FeistelCipher(payload.key, payload.rounds)
    ciphertext, trace = cipher.encrypt(payload.plaintext, trace=True)
    return {
        "plaintext": payload.plaintext,
        "plaintext_bits": f"{payload.plaintext:08b}",
        "ciphertext": ciphertext,
        "ciphertext_bits": f"{ciphertext:08b}",
        "key": payload.key,
        "key_hex": f"0x{payload.key:04X}",
        "rounds": payload.rounds,
        "subkeys": [{"value": key, "bits": f"{key:04b}"} for key in cipher.subkeys],
        "trace": [item.to_dict() for item in trace],
    }


@app.post("/api/cipher/decrypt")
async def decrypt(payload: DecryptRequest) -> dict[str, object]:
    cipher = FeistelCipher(payload.key, payload.rounds)
    plaintext = cipher.decrypt(payload.ciphertext)
    return {
        "ciphertext": payload.ciphertext,
        "ciphertext_bits": f"{payload.ciphertext:08b}",
        "plaintext": plaintext,
        "plaintext_bits": f"{plaintext:08b}",
    }


@app.post("/api/packet/simulate")
async def simulate_packet(payload: PacketRequest) -> dict[str, object]:
    service = PacketService(payload.key, b"feistel-grid-integrity-key", payload.rounds)
    packet = service.create_packet(
        payload.plaintext,
        payload.meter_id,
        payload.sequence,
        payload.iv,
    )
    transmitted_packet = packet
    if payload.attack_mode == "tamper":
        transmitted_packet = MeterPacket(**{
            **packet.to_dict(),
            "ciphertext": packet.ciphertext ^ 0x01,
        })

    integrity_valid = service.verify(transmitted_packet)
    sequence_valid = payload.attack_mode != "replay"
    recovered = service.decrypt_packet(transmitted_packet) if integrity_valid else None
    accepted = integrity_valid and sequence_valid
    if not integrity_valid:
        decision = "Rejected: the packet changed after its integrity tag was created."
    elif not sequence_valid:
        decision = "Rejected: the sequence number is stale and indicates a replay."
    else:
        decision = "Accepted: integrity and sequence checks passed."
    return {
        "packet": transmitted_packet.to_dict(),
        "pre_encryption_value": payload.plaintext ^ payload.iv,
        "integrity_valid": integrity_valid,
        "sequence_valid": sequence_valid,
        "recovered_plaintext": recovered,
        "accepted": accepted,
        "attack_mode": payload.attack_mode,
        "decision": decision,
    }


@app.post("/api/analysis/run")
async def run_analysis(payload: AnalysisRequest) -> dict[str, object]:
    configurations = []
    for rounds in FeistelCipher.valid_rounds:
        avalanche = run_avalanche_analysis(payload.key, rounds, payload.samples)
        key_sensitivity = run_key_sensitivity(payload.key, rounds, payload.samples)
        timing = benchmark_cipher(payload.key, rounds, payload.iterations)
        energy = estimate_energy(
            float(timing["average_us"]),
            payload.voltage,
            payload.active_current_ma,
        )
        configurations.append({
            "rounds": rounds,
            "avalanche": avalanche,
            "key_sensitivity": key_sensitivity,
            "timing": timing,
            "energy_estimate": energy,
        })
    return {
        "key": payload.key,
        "samples": payload.samples,
        "note": "Energy values are model-based estimates, not physical MCU measurements.",
        "configurations": configurations,
    }


@app.post("/api/automation/start")
async def start_automation(payload: AutomationStartRequest) -> dict[str, object]:
    return await automation_service.start(
        payload.key,
        payload.rounds,
        payload.interval_seconds,
        payload.meter_id,
    )


@app.post("/api/automation/stop")
async def stop_automation() -> dict[str, object]:
    return await automation_service.stop()


@app.get("/api/automation/status")
async def automation_status() -> dict[str, object]:
    return automation_service.status()


@app.get("/api/automation/records")
async def automation_records(
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, object]:
    records = automation_service.records(limit)
    return {"count": len(records), "records": records}


@app.get("/api/automation/export.xlsx")
async def export_automation_records() -> StreamingResponse:
    records = automation_service.records(limit=2000)
    workbook = create_automation_workbook(records)
    filename = f"smart-meter-data-{datetime.now().strftime('%Y%m%d-%H%M%S')}.xlsx"
    return StreamingResponse(
        workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/api/automation/records")
async def clear_automation_records() -> dict[str, object]:
    automation_service.clear()
    return {"cleared": True}



