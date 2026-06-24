# AGENTS.md

## Cursor Cloud specific instructions

NIGHTWATCH is a Python (>=3.11) voice-controlled autonomous-observatory control
system. It is a collection of async observatory services (`services/`), a voice
pipeline (`voice/`), and a core orchestrator/CLI package (`nightwatch/`). There
is no web UI — it is a CLI/library application tested via `pytest`.

### Environment

- Dependencies are installed into a virtualenv at `.venv` (the startup/update
  script creates it and runs `pip install -e ".[services,voice,dev]"`).
  Activate it before doing anything: `source .venv/bin/activate`.
- Two system packages are required and are baked into the VM image (do NOT add
  them to the update script): `python3.12-venv` (for `python -m venv`) and
  `libportaudio2` (so the voice extra's `sounddevice` can import). If a fresh VM
  is missing them, install with `sudo apt-get install -y python3.12-venv libportaudio2`.

### Lint / type-check / test / run

- Lint: `ruff check services/ voice/ nightwatch/`. Note the repo currently has
  thousands of findings under the strict `pyproject.toml` config; CI runs
  `ruff check ... --ignore=E501,F401,F841` with `|| true`, so lint is advisory.
- Type-check: `mypy nightwatch/` (also advisory in CI).
- Tests: `pytest tests/unit/` (CI target). See `pytest.ini` / `README.md` for
  the standard commands; coverage via `pytest --cov=nightwatch --cov=services`.

### Non-obvious test caveats

- A few focuser tests (`tests/unit/test_focuser_service.py::TestFocuserServiceMovement`)
  hang on a real wait. The active config is `pytest.ini` (timeout=120, signal
  method), so the full suite *completes* but wastes ~120s per hung test. For a
  fast run use `pytest tests/unit/ --timeout=15 --timeout-method=signal`. Do
  NOT rely on the `pyproject.toml` thread-timeout — the thread method cannot
  interrupt the hang and aborts the whole session.
- 4 unit files fail at *collection* because they hardcode absolute paths /
  broken imports (pre-existing, unrelated to the environment):
  `test_plate_solver.py`, `test_safety_monitor.py`, `test_whisper_service.py`,
  `test_piper_service.py`. Exclude them with `--ignore` for a clean run.
- With the above exclusions the unit suite is ~2444 passed / ~16 failed; the
  remaining failures are pre-existing timing/formatting assertions, not setup
  issues.

### Known broken entrypoints (pre-existing, do not "fix" during setup)

- The CLI `python -m nightwatch.main` (and `bin/nightwatch`) crashes immediately
  with `setup_logging() got an unexpected keyword argument 'level'`. The README
  also references a `python -m nightwatch.cli` module that does not exist.
- The hardware simulators (e.g. `services.simulators.mount_simulator.MountSimulator`)
  fail to instantiate: the base class in `services/simulators/__init__.py`
  assigns `self.state`, but subclasses define `state` as a read-only property.

### Demonstrating the product works

The end-to-end product behavior is best exercised via the `tests/e2e/` suite
(goto/park/session/safety, which use mock devices) and by driving the real
voice tool registry against the catalog, e.g.:

```python
from services.catalog.catalog import CatalogService
from voice.tools.telescope_tools import ToolRegistry, create_default_handlers
cat = CatalogService(db_path="/tmp/nw.db"); cat.initialize()
reg = ToolRegistry()
for n, h in create_default_handlers(catalog_service=cat).items():
    if reg.get_tool(n): reg.set_handler(n, h)
# await reg.execute("lookup_object", {"object_name": "Andromeda"})
```
