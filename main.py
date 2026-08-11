"""Single-command local runner for model service + Flask backend."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse a dotenv-style file into key/value pairs.

    Args:
        path: Path to the `.env` file.

    Returns:
        dict[str, str]: Parsed environment variables.
    """
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _spawn(command: list[str], cwd: Path, env: dict[str, str], name: str) -> subprocess.Popen:
    """Start a subprocess and print a standardized startup message.

    Args:
        command: Command vector to execute.
        cwd: Working directory for the subprocess.
        env: Environment variables passed to the subprocess.
        name: Human-readable process name for logs.

    Returns:
        subprocess.Popen: Running subprocess handle.
    """
    print(f"[main] starting {name}: {' '.join(command)}")
    return subprocess.Popen(command, cwd=str(cwd), env=env)


def _get_bool(raw: str | None, default: bool) -> bool:
    """Convert a textual environment value into boolean form.

    Args:
        raw: Raw environment value.
        default: Default value when `raw` is missing.

    Returns:
        bool: Parsed boolean result.
    """
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_host(raw: str | None, default: str) -> str:
    """Resolve a host string with fallback handling.

    Args:
        raw: Raw host value from environment.
        default: Default host used when `raw` is empty.

    Returns:
        str: Effective host.
    """
    value = (raw or "").strip()
    return value or default


def _display_host(host: str) -> str:
    """Normalize localhost hosts for display output.

    Args:
        host: Hostname or IP to print.

    Returns:
        str: Display-friendly host label.
    """
    return "localhost" if host in {"127.0.0.1", "::1"} else host


def _split_csv(raw: str | None) -> list[str]:
    """Split a comma-delimited string into normalized values.

    Args:
        raw: CSV input value.

    Returns:
        list[str]: Non-empty, stripped entries.
    """
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _terminate_all(processes: list[tuple[str, subprocess.Popen]]) -> None:
    """Terminate child processes gracefully and force-kill if required.

    Args:
        processes: Process tuples as `(name, handle)`.
    """
    for name, proc in processes:
        if proc.poll() is None:
            print(f"[main] stopping {name}")
            proc.terminate()

    deadline = time.time() + 8
    while time.time() < deadline:
        if all(proc.poll() is not None for _, proc in processes):
            return
        time.sleep(0.2)

    for name, proc in processes:
        if proc.poll() is None:
            print(f"[main] force-killing {name}")
            proc.kill()


def main() -> None:
    """Run backend and model-service processes with coordinated lifecycle."""
    root = Path(__file__).resolve().parent
    env_file_values = _read_env_file(root / ".env")
    base_env = env_file_values.copy()
    base_env.update(os.environ)

    model_port = int(base_env.get("MODEL_SERVICE_PORT", "8000"))
    backend_port = int(base_env.get("PORT", base_env.get("BACKEND_PORT", "5000")))
    localhost_only = _get_bool(base_env.get("LOCALHOST_ONLY"), True)

    model_host = _get_host(base_env.get("MODEL_SERVICE_HOST"), "127.0.0.1")
    backend_host = _get_host(base_env.get("BACKEND_HOST"), "127.0.0.1")

    if localhost_only:
        model_host = "127.0.0.1"
        backend_host = "127.0.0.1"

    processes: list[tuple[str, subprocess.Popen]] = []

    model_env = base_env.copy()
    model_env.setdefault("PORT", str(model_port))
    model_env["HOST"] = model_host
    model_env["MODELS_ROOT"] = str(root / "models")
    processes.append(
        (
            "model_service",
            _spawn([sys.executable, "-m", "model_service.app"], root, model_env, "model_service"),
        )
    )

    backend_env = base_env.copy()
    backend_env.setdefault("PORT", str(backend_port))
    backend_env["HOST"] = backend_host
    backend_env.setdefault("MODEL_SERVICE_URL", f"http://127.0.0.1:{model_port}")
    backend_env["MODELS_ROOT"] = str(root / "models")

    existing_origins = _split_csv(backend_env.get("CORS_ORIGINS"))
    local_origins = [f"http://localhost:{backend_port}", f"http://127.0.0.1:{backend_port}"]
    if backend_host not in {"localhost", "127.0.0.1", "::1"}:
        local_origins.append(f"http://{backend_host}:{backend_port}")
    backend_env["CORS_ORIGINS"] = ",".join(dict.fromkeys(existing_origins + local_origins))

    processes.append(
        (
            "backend",
            _spawn([sys.executable, "-m", "backend.app"], root, backend_env, "backend"),
        )
    )

    if not localhost_only and any(host not in {"127.0.0.1", "::1"} for host in (backend_host, model_host)):
        print("[main] warning: LOCALHOST_ONLY=false and one or more services are exposed to the network.")

    print(f"[main] backend: http://{_display_host(backend_host)}:{backend_port}")
    print(f"[main] model service: http://{_display_host(model_host)}:{model_port}/health")
    print(f"[main] web app (Jinja): http://{_display_host(backend_host)}:{backend_port}")
    print("[main] press Ctrl+C to stop all services")

    exit_code = 0
    try:
        while True:
            for name, proc in processes:
                code = proc.poll()
                if code is None:
                    continue
                if code != 0:
                    print(f"[main] {name} exited with code {code}")
                    exit_code = code
                    raise RuntimeError(f"{name} exited unexpectedly")
                print(f"[main] {name} stopped")
                exit_code = 1
                raise RuntimeError(f"{name} stopped")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[main] shutdown requested")
    except RuntimeError:
        pass
    finally:
        _terminate_all(processes)

    if exit_code != 0:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
