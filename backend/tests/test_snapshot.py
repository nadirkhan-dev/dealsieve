"""scripts/build_snapshot.py feeds the static GitHub Pages preview.

If it silently produced fewer leads, unscored leads or missing briefs, the
published preview would be wrong with no server-side error to notice, so the
output is checked here.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_snapshot.py"
SNAPSHOT = ROOT / "frontend" / "public" / "snapshot.json"


def test_build_snapshot_produces_scored_leads_with_briefs(tmp_path):
    before = SNAPSHOT.read_text() if SNAPSHOT.exists() else None
    try:
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT,
                                capture_output=True, text=True)
        assert result.returncode == 0, f"script failed:\n{result.stdout}\n{result.stderr}"
        snap = json.loads(SNAPSHOT.read_text())

        assert len(snap["leads"]) == 13
        assert len(snap["details"]) == 13
        assert all(l["score"] is not None for l in snap["leads"]), "every lead must be scored"
        assert all(l["tier"] for l in snap["leads"])
        assert any(l["tier"] == "A" for l in snap["leads"])

        for lead in snap["leads"]:
            detail = snap["details"][str(lead["id"])]
            brief = detail["brief"]
            assert brief, f"{lead['name']} has no brief"
            # The snapshot must never depend on an API key being present.
            assert brief["source"] == "template", brief["source"]
            assert brief["summary"] and brief["email_body"] and brief["questions"]

        # The industry filter needs the raw column, not the guess from the site.
        assert set(snap["raw_industries"]) == {str(l["id"]) for l in snap["leads"]}
        assert snap["stats"]["total"] == 13
        assert snap["settings"]["weights"]
    finally:
        if before is not None:
            SNAPSHOT.write_text(before)
