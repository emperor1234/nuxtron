from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
TASK_REGISTRATION_SCRIPT = r"""
from backend.fastapi.app.celery_app import celery_app

celery_app.loader.import_default_modules()
required = {
    "nuxtron.tasks.ai.process_image",
    "nuxtron.tasks.ai.process_text",
    "nuxtron.tasks.ai.process_video",
    "nuxtron.tasks.ai.process_voice",
    "workforce.execute_mission",
}
retired_placeholders = {
    "nuxtron.tasks.analytics.compute_metrics",
    "nuxtron.tasks.seo.refresh_scores",
    "nuxtron.tasks.notifications.send_digest",
}
missing = sorted(required.difference(celery_app.tasks))
if missing:
    raise SystemExit(f"Celery tasks not registered: {missing}")
registered_placeholders = sorted(retired_placeholders.intersection(celery_app.tasks))
if registered_placeholders:
    raise SystemExit(f"Retired placeholder Celery tasks are still registered: {registered_placeholders}")
print("CELERY_TASK_REGISTRATION_OK")
"""


def test_canonical_celery_app_registers_worker_tasks_without_broker_connection() -> None:
    dependency_paths = [path for path in sys.path if "site-packages" in path]
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(REPO_ROOT), *dependency_paths]),
        "ENVIRONMENT": "development",
        "NUXTRON_SKIP_STARTUP_DB_INIT": "1",
        "APP_ENC_KEY": "00" * 32,
        "FASTAPI_API_KEY": "celery-test-api-key",
    }

    result = subprocess.run(
        [sys.executable, "-c", TASK_REGISTRATION_SCRIPT],
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "CELERY_TASK_REGISTRATION_OK" in result.stdout
