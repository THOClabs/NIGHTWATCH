"""
Atomic-persistence regression test for the success tracker (fix S2-5).

_save() writes to a temp file and os.replace()s it into place, so a crash
during the write cannot corrupt or truncate the existing history. If the
replace fails, the previously persisted history must remain intact on disk.
"""

from services.catalog import success_tracker as st_mod
from services.catalog.success_tracker import SuccessTracker


def test_save_failure_preserves_prior_history(tmp_path, monkeypatch):
    history_path = tmp_path / "success_history.json"

    tracker = SuccessTracker(history_path=history_path)
    tracker.record_observation("M31", success=True, quality_score=0.9)

    # First record persisted normally.
    assert history_path.exists()

    # Make the atomic replace step of the NEXT save fail, simulating a crash.
    def failing_replace(src, dst):
        raise OSError("simulated crash during atomic replace")

    monkeypatch.setattr(st_mod.os, "replace", failing_replace)

    # This save fails at replace time; it must not corrupt the existing file.
    tracker.record_observation("M42", success=True, quality_score=0.8)

    # Reload from disk: the first object's history must have survived.
    reloaded = SuccessTracker(history_path=history_path)
    target_ids = [r.target_id for r in reloaded._records]

    assert "M31" in target_ids
    # The failed save must not have leaked the second record onto disk.
    assert "M42" not in target_ids
