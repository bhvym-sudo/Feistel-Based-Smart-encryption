import asyncio

from app.core.data_generator import ResidentialLoadGenerator
from app.services.automation import AutomationService


def test_automation_runs_until_stopped_and_persists_records(tmp_path):
    async def exercise():
        service = AutomationService(
            ResidentialLoadGenerator(),
            tmp_path / "automation.db",
        )
        await service.start(0xBEEF, 6, 0.5, "SM-TEST")
        await asyncio.sleep(0.05)

        status = service.status()
        assert status["running"] is True
        assert status["record_count"] >= 1
        assert status["latest"]["meter_id"] == "SM-TEST"

        await service.stop()
        stopped_count = len(service.records())
        await asyncio.sleep(0.05)
        assert service.status()["running"] is False
        assert len(service.records()) == stopped_count

        service.clear()
        assert service.records() == []

    asyncio.run(exercise())
