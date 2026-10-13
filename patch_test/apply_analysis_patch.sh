#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"

if [[ ! -f "$ROOT/app/main.py" ]]; then
  echo "Run this script from the backend directory."
  exit 1
fi

mkdir -p "$ROOT/app/services" "$ROOT/app/routers"
cp "$(dirname "$0")/historical_backfill_service.py" "$ROOT/app/services/historical_backfill_service.py"
cp "$(dirname "$0")/mtf_analysis_service.py" "$ROOT/app/services/mtf_analysis_service.py"
cp "$(dirname "$0")/analysis_mtf_router.py" "$ROOT/app/routers/analysis_mtf.py"
cp "$(dirname "$0")/market_updater.py" "$ROOT/app/services/market_updater.py"

python - <<'PY'
from pathlib import Path

main = Path("app/main.py")
text = main.read_text(encoding="utf-8")

if "from app.routers.analysis_mtf import router as analysis_mtf_router" not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and (lines[insert_at].startswith("from ") or lines[insert_at].startswith("import ") or not lines[insert_at].strip()):
        insert_at += 1
    lines.insert(insert_at, "from app.routers.analysis_mtf import router as analysis_mtf_router")
    text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")

if "include_router(analysis_mtf_router)" not in text:
    marker = "if __name__ == \"__main__\":"
    if marker in text:
        text = text.replace(marker, "app.include_router(analysis_mtf_router)\n\n" + marker, 1)
    else:
        text += "\napp.include_router(analysis_mtf_router)\n"

main.write_text(text, encoding="utf-8")
PY

chmod +x patch_test/apply_analysis_patch.sh

python -m py_compile patch_test/historical_backfill_service.py patch_test/mtf_analysis_service.py patch_test/analysis_mtf_router.py
