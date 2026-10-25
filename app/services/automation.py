"""Continuous smart-meter automation and persistent record storage."""

from __future__ import annotations

import asyncio
import sqlite3
import time
from pathlib import Path

from app.core.cipher import FeistelCipher
from app.core.data_generator import ReadingGenerator
from app.core.packet import PacketService
from app.services.analysis import estimate_energy, run_avalanche_analysis


class AutomationService:
    def __init__(self, generator: ReadingGenerator, database_path: Path) -> None:
        self.generator = generator
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.running = False
        self.task: asyncio.Task | None = None
        self.config: dict[str, object] | None = None
        self.latest: dict[str, object] | None = None
        self.metrics: dict[str, object] | None = None
        self._create_table()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_table(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS automation_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    usage_kwh REAL NOT NULL,
                    power_kw REAL NOT NULL,
                    voltage REAL NOT NULL,
                    current REAL NOT NULL,
                    quantized_value INTEGER NOT NULL,
                    ciphertext INTEGER NOT NULL,
                    ciphertext_bits TEXT NOT NULL,
                    integrity_valid INTEGER NOT NULL,
                    rounds INTEGER NOT NULL,
                    encryption_us REAL NOT NULL
                )
            """)

    def _next_sequence(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM automation_records"
            ).fetchone()
        return int(row["next_sequence"])

    def _save(self, record: dict[str, object]) -> int:
        with self._connect() as connection:
            cursor = connection.execute("""
                INSERT INTO automation_records (
                    timestamp, sequence, usage_kwh, power_kw, voltage, current,
                    quantized_value, ciphertext, ciphertext_bits,
                    integrity_valid, rounds, encryption_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["timestamp"], record["sequence"], record["usage_kwh"],
                record["power_kw"], record["voltage"], record["current"],
                record["quantized_value"], record["ciphertext"],
                record["ciphertext_bits"], int(record["integrity_valid"]),
                record["rounds"], record["encryption_us"],
            ))
            connection.execute("""
                DELETE FROM automation_records
                WHERE id NOT IN (
                    SELECT id FROM automation_records ORDER BY id DESC LIMIT 2000
                )
            """)
            return int(cursor.lastrowid)

    def records(self, limit: int = 200) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM automation_records ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = [dict(row) for row in reversed(rows)]
        for record in result:
            record["integrity_valid"] = bool(record["integrity_valid"])
        return result

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM automation_records")
        self.latest = None

    async def start(self, key: int, rounds: int, interval_seconds: float, meter_id: str) -> dict[str, object]:
        if self.running:
            return self.status()
        self.config = {
            "key": key,
            "rounds": rounds,
            "interval_seconds": interval_seconds,
            "meter_id": meter_id,
        }
        avalanche = run_avalanche_analysis(key, rounds, samples=32)
        self.metrics = {"avalanche_percent": avalanche["average_percent"]}
        self.running = True
        self.task = asyncio.create_task(self._run())
        return self.status()

    async def stop(self) -> dict[str, object]:
        self.running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.task = None
        return self.status()

    def status(self) -> dict[str, object]:
        return {
            "running": self.running,
            "config": self.config,
            "record_count": len(self.records(limit=2000)),
            "latest": self.latest,
            "metrics": self.metrics,
        }

    async def _run(self) -> None:
        assert self.config is not None
        sequence = self._next_sequence()
        key = int(self.config["key"])
        rounds = int(self.config["rounds"])
        interval = float(self.config["interval_seconds"])
        meter_id = str(self.config["meter_id"])
        cipher = FeistelCipher(key, rounds)
        packet_service = PacketService(key, b"feistel-grid-integrity-key", rounds)

        try:
            while self.running:
                reading = self.generator.generate(1, 15, sequence * 7919, meter_id)[0]
                started = time.perf_counter_ns()
                ciphertext, trace = cipher.encrypt(reading.quantized_value, trace=True)
                encryption_us = (time.perf_counter_ns() - started) / 1000
                packet = packet_service.create_packet(
                    reading.quantized_value, meter_id, sequence, 0x5A, reading.timestamp
                )
                energy = estimate_energy(encryption_us)
                record: dict[str, object] = {
                    **reading.to_dict(),
                    "sequence": sequence,
                    "plaintext_bits": f"{reading.quantized_value:08b}",
                    "ciphertext": ciphertext,
                    "ciphertext_bits": f"{ciphertext:08b}",
                    "rounds": rounds,
                    "trace": [item.to_dict() for item in trace],
                    "packet": packet.to_dict(),
                    "integrity_valid": packet_service.verify(packet),
                    "sequence_valid": True,
                    "accepted": True,
                    "recovered_plaintext": reading.quantized_value,
                    "encryption_us": round(encryption_us, 4),
                    "estimated_energy_uj": energy["estimated_energy_uj"],
                }
                record["id"] = self._save(record)
                self.latest = record
                sequence += 1
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        finally:
            self.running = False
