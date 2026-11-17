"""Запись фактического unittest результата и интервала, без заданного test-count."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    log=io.StringIO();start=datetime.now(timezone.utc);tick=time.monotonic()
    suite=unittest.defaultTestLoader.discover(str(ROOT/"tests"))
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    elapsed=time.monotonic()-tick;end=datetime.now(timezone.utc)
    (a.output/"tests.txt").write_text(log.getvalue(),encoding="utf-8")
    data={"started_at":start.isoformat(),"ended_at":end.isoformat(),"elapsed_seconds":elapsed,
          "tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),
          "passed":result.wasSuccessful(),"interpreter":sys.executable,"python":sys.version,
          "packages":{name:importlib.metadata.version(name) for name in ("openpyxl","pypdf","et-xmlfile")},
          "kind":"deterministic_tests_not_agent_execution"}
    (a.output/"result.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,ensure_ascii=True));raise SystemExit(0 if result.wasSuccessful() else 1)
