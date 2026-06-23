from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from statistics import mean
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = BACKEND_ROOT.parent / "MultiBur-frontend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def print_title(title: str) -> None:
    line = "=" * 88
    print(f"\n{line}\n{title}\n{line}")


def print_kv(label: str, value: Any) -> None:
    print(f"{label:<34}: {value}")


def print_db_error(exc: Exception) -> None:
    print_kv("Estado consulta BD", "NO EJECUTADA")
    print_kv("Motivo", exc.__class__.__name__)
    print(
        "Detalle                            : No se pudo abrir conexion con la base de datos. "
        "Verifica que DATABASE_URL apunte al Transaction Pooler de Supabase o ejecuta la metrica "
        "desde un entorno que resuelva el host configurado."
    )


def print_table(headers: list[str], rows: list[list[Any]]) -> None:
    if not rows:
        print("(sin registros)")
        return
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def fmt(row_values: list[Any]) -> str:
        return " | ".join(str(value).ljust(widths[i]) for i, value in enumerate(row_values))

    print(fmt(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(fmt(row))


def pct(part: int | float, total: int | float) -> str:
    if not total:
        return "0.00%"
    return f"{(part / total) * 100:.2f}%"


def get_session_and_engine():
    from app.db.session import SessionLocal, engine

    return SessionLocal(), engine


def count_query(session, model) -> int:
    return int(session.query(model).count())


def backend_api_url() -> str:
    return os.getenv("METRICAS_API_URL", "https://multibur-backend.onrender.com/api/v1").rstrip("/")


def get_token() -> str | None:
    explicit = os.getenv("METRICAS_TOKEN")
    if explicit:
        return explicit

    email = os.getenv("METRICAS_ADMIN_EMAIL")
    password = os.getenv("METRICAS_ADMIN_PASSWORD")
    if not email or not password:
        return None

    url = f"{backend_api_url()}/auth/login/access-token"
    data = urllib.parse.urlencode({"username": email, "password": password}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("access_token")
    except Exception as exc:  # noqa: BLE001 - consola de evidencia
        print_kv("Token ADMIN", f"No disponible ({exc})")
        return None


def request_timed(endpoint: str, token: str | None = None, method: str = "GET") -> dict[str, Any]:
    url = f"{backend_api_url()}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, method=method, headers=headers)

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            response.read()
            status = response.status
            ok = 200 <= status < 300
    except urllib.error.HTTPError as exc:
        exc.read()
        status = exc.code
        ok = False
    except Exception as exc:  # noqa: BLE001 - consola de evidencia
        return {
            "endpoint": endpoint,
            "status": "ERROR",
            "ok": False,
            "ms": round((time.perf_counter() - start) * 1000, 2),
            "detalle": str(exc),
        }

    return {
        "endpoint": endpoint,
        "status": status,
        "ok": ok,
        "ms": round((time.perf_counter() - start) * 1000, 2),
        "detalle": "OK" if ok else "Respuesta no exitosa",
    }


def avg(values: list[float]) -> float:
    return round(mean(values), 2) if values else 0.0


def run_python(args: list[str], cwd: Path = BACKEND_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )
