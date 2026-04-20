"""End-to-end CLI test using local CSV data, no network."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yaml
from click.testing import CliRunner

from alphaagent.cli import main


def _write_csv(path: Path, closes: list[float], start: date) -> None:
    rows = [
        (
            (start + timedelta(days=i)).isoformat(),
            c, c, c, c, 1000, 1e8,
        )
        for i, c in enumerate(closes)
    ]
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "amount"])
    df.to_csv(path, index=False)


def _build_fixtures(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Synthetic CSVs + meta CSV + screen.yaml. Returns (config, output, picks_yaml)."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    start = date(2024, 1, 1)
    _write_csv(data_dir / "WIN.csv", [10 + i * 0.5 for i in range(120)], start)
    _write_csv(data_dir / "LOS.csv", [50 - i * 0.4 for i in range(120)], start)
    _write_csv(data_dir / "MID.csv", [20 + (i % 5 - 2) for i in range(120)], start)

    meta_path = tmp_path / "meta.csv"
    meta_path.write_text(
        "symbol,name,industry,list_date\n"
        "WIN,WinCo,科技,2010-01-01\n"
        "LOS,LoseCo,科技,2010-01-01\n"
        "MID,MidCo,科技,2010-01-01\n"
    )

    cfg_path = tmp_path / "screen.yaml"
    out_path = tmp_path / "picks.yaml"
    cfg_path.write_text(
        f"""
universe:
  source: static
  symbols: ["WIN", "LOS", "MID"]
data:
  source: csv
  root: {data_dir}
  freq: 1d
as_of: 2024-04-20
lookback_days: 60
calendar_enabled: false
meta:
  source: csv
  csv: {meta_path}
filters:
  - type: min_price
    min_price: 15.0
rules:
  - type: momentum
    lookback: 30
    weight: 0.6
  - type: above_ma
    period: 10
    weight: 0.4
execution:
  max_workers: 2
  show_progress: false
output:
  path: {out_path}
  top_n: 10
  with_reasons: full
  format: yaml
""",
        encoding="utf-8",
    )
    return cfg_path, out_path, meta_path


def test_screen_cli_end_to_end(tmp_path):
    cfg_path, out_path, _ = _build_fixtures(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["screen", "-c", str(cfg_path)])

    assert result.exit_code == 0, result.output
    assert out_path.exists()

    parsed = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    # WIN should top the list (monotonic increase)
    assert parsed["symbols"][0] == "WIN"
    # LOS dropped by min_price filter
    assert "LOS" not in parsed["symbols"]
    # universe_snapshot has all 3 (pre-filter)
    assert set(parsed["metadata"]["universe_snapshot"]) == {"WIN", "LOS", "MID"}


def test_screen_cli_dry_run(tmp_path):
    cfg_path, out_path, _ = _build_fixtures(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["screen", "-c", str(cfg_path), "--dry-run"])

    assert result.exit_code == 0
    assert "config OK" in result.output
    assert not out_path.exists()  # didn't write


def test_screen_cli_replay(tmp_path):
    cfg_path, out_path, _ = _build_fixtures(tmp_path)
    runner = CliRunner()

    # First run produces picks.yaml with universe_snapshot
    result1 = runner.invoke(main, ["screen", "-c", str(cfg_path)])
    assert result1.exit_code == 0

    # Replay using the snapshot
    out2 = tmp_path / "picks_v2.yaml"
    result2 = runner.invoke(
        main,
        ["screen", "-c", str(cfg_path), "--replay", str(out_path), "-o", str(out2)],
    )
    assert result2.exit_code == 0, result2.output
    parsed = yaml.safe_load(out2.read_text(encoding="utf-8"))
    assert set(parsed["metadata"]["universe_snapshot"]) == {"WIN", "LOS", "MID"}


def test_screen_cli_csv_output(tmp_path):
    cfg_path, _, _ = _build_fixtures(tmp_path)
    # Rewrite config to use csv format
    text = cfg_path.read_text(encoding="utf-8").replace("format: yaml", "format: csv")
    csv_out = tmp_path / "picks.csv"
    text = text.replace("picks.yaml", "picks.csv")
    cfg_path.write_text(text, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["screen", "-c", str(cfg_path)])
    assert result.exit_code == 0, result.output
    assert csv_out.exists()
    body = csv_out.read_text(encoding="utf-8")
    assert "symbol" in body.splitlines()[0]
    assert "WIN" in body


def test_list_screen_rules_command():
    runner = CliRunner()
    result = runner.invoke(main, ["list-screen-rules"])
    assert result.exit_code == 0
    assert "momentum" in result.output
    assert "above_ma" in result.output
    assert "exclude_st" in result.output
