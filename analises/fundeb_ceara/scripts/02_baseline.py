"""02–06 — etapas do estudo; a execução completa é `python -m analises.fundeb_ceara.run`."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def _run() -> None:
    from analises.fundeb_ceara.run import main
    raise SystemExit(main())


if __name__ == "__main__":
    _run()
