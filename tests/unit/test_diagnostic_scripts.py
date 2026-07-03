from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_script(script_path: str, *args: str):
    return subprocess.run(
        [sys.executable, script_path, *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def test_cli_processor_show_text_missing_file_exits_nonzero():
    result = _run_script("scripts/diagnostics/cli_processor_show_text.py", "missing.pdf")

    assert result.returncode == 1
    assert "Archivo no encontrado" in result.stdout


def test_extract_text_demo_failed_processing_exits_nonzero(tmp_path):
    fake_pdf = tmp_path / "not-a-real.pdf"
    fake_pdf.write_bytes(b"not a real pdf")

    result = _run_script("scripts/diagnostics/extract_text_demo.py", str(fake_pdf))

    assert result.returncode == 1
    assert "No se extrajo" in result.stdout


def test_chase_debug_script_runs_declared_main_path():
    result = _run_script("scripts/diagnostics/chase_debug.py")

    assert result.returncode == 0
    assert "Found 8 transactions" in result.stdout
    assert "Skipped" not in result.stdout
    assert "Skipped" not in result.stderr
