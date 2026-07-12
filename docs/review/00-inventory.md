# NIGHTWATCH Repository Inventory (L1 Reconnaissance)

**Generated:** 2026-07-12  
**Repository:** /home/user/NIGHTWATCH  
**Git Status:** Clean repository (main branch)

---

## 1. Directory Tree (Top 3 Levels)

```
.
├── bin/                          # CLI entry points (bash launcher scripts)
├── deploy/                       # Deployment and systemd service files
│   ├── scripts/                  # Installation and upgrade shell scripts
│   └── systemd/                  # systemd service definitions for NIGHTWATCH
├── docker/                       # Container configurations
│   └── simulators/               # Docker images for testing (mount, camera, weather, PHD2)
├── docs/                         # Project documentation
│   ├── assets/                   # Images and diagrams
│   ├── decisions/                # Architecture Decision Records (ADRs)
│   ├── pos/                      # Points of Study (research/analysis documents)
│   └── research/                 # Research and sourcing guides
├── examples/                     # Example usage scripts
├── firmware/                     # Hardware firmware configs (OnStepX telescope controller)
│   └── onstepx_config/           # OnStepX board configuration headers
├── nightwatch/                   # Core Python package (orchestrator, LLM client, safety)
├── pos/                          # POS (Points Of Study) agent documents
│   └── agents/                   # Named analysis agents (Howard Dutton, Damian Peach, etc.)
├── services/                     # 22 independent service modules
│   ├── alerts/                   # Alert manager and escalation
│   ├── alpaca/                   # ASCOM Alpaca device client (network telescope control)
│   ├── astrometry/               # Plate solver integration (astrometry.net)
│   ├── camera/                   # ZWO ASI camera driver wrapper
│   ├── catalog/                  # Messier and object catalog with scoring
│   ├── enclosure/                # Roof/dome controller
│   ├── encoder/                  # Encoder bridge for mount position tracking
│   ├── ephemeris/                # Skyfield-based celestial calculations
│   ├── focus/                    # Autofocus service (V-curve analysis)
│   ├── guiding/                  # PHD2 guide camera integration
│   ├── indi/                     # INDI device client (Linux astronomy devices)
│   ├── meteor_tracking/          # Fireball network and shower tracking
│   ├── mount_control/            # LX200 and OnStepX mount commands
│   ├── nlp/                      # Natural language processing (conversation, preferences)
│   ├── power/                    # Power management and reboot scheduling
│   ├── safety_monitor/           # Safety interlocks (weather, limit sensors)
│   ├── scheduling/               # Task scheduling and conditions
│   ├── simulators/               # Mock devices for testing
│   ├── voice/                    # Voice vocabulary and wake-word training
│   └── weather/                  # Weather station integration (Ecowitt, AAG)
├── tests/                        # Automated tests (110 Python files)
│   ├── e2e/                      # End-to-end voice flow tests
│   ├── fixtures/                 # Mock services and test utilities
│   ├── hardware/                 # Hardware-dependent tests (skipped in CI)
│   ├── integration/              # Integration tests with Docker simulators
│   ├── mocks/                    # Mock device implementations
│   └── unit/                     # Unit tests per service
├── voice/                        # Voice pipeline package
│   ├── stt/                      # Speech-to-text (faster-whisper)
│   ├── tts/                      # Text-to-speech (piper-tts)
│   ├── tools/                    # Telescope and meteor command tools
│   └── wyoming/                  # Wyoming voice integration protocol servers
└── .claude/                      # Claude Code agent configuration
    ├── agents/                   # Domain-expert agent role definitions
    └── commands/                 # Custom command workflows
```

---

## 2. Languages and Approximate LOC

| Language | Files | LOC | Purpose |
|----------|-------|-----|---------|
| Python | 213 | ~122,342 | Core application, services, voice pipeline, tests |
| YAML | 30+ | ~2,500 | Config files, CI/CD workflows, docker-compose |
| Markdown | 40+ | ~5,000+ | Documentation, architecture decisions, ADRs |
| Bash | 2 | ~100 | CLI launcher scripts (bin/nightwatch) |
| Batch | 1 | ~150 | Windows launcher (bin/nightwatch.bat) |
| C/Header | 1 | ~200 | OnStepX firmware config (firmware/onstepx_config/Config.h) |

**Total Source LOC (excluding docs/tests):** ~25,000 (Python core + services)  
**Total Project LOC (including tests/docs):** ~135,000+

---

## 3. Dependency Manifests and Key Dependencies

### 3.1 Main Project Manifest
**File:** `/home/user/NIGHTWATCH/pyproject.toml`

- **Build System:** `setuptools>=61.0`, `wheel`
- **Python Requirement:** `>=3.11`
- **Package Name:** `nightwatch` (v0.1.0-dev)
- **Entry Point:** CLI via `nightwatch = nightwatch.main:main`

**Core Dependencies (nightwatch package):**
- `pydantic>=2.0` — Configuration validation and type checking
- `PyYAML>=6.0` — YAML configuration parsing

**Optional Dependency Groups:**
- `services`: `skyfield>=1.48`, `aiohttp>=3.9`, `pyserial>=3.5`, `astropy>=6.0`
- `voice`: `faster-whisper>=1.0`, `piper-tts>=1.2`, `sounddevice>=0.5`, `numpy>=1.26`, `pymicro-vad>=1.0`
- `dev`: `pytest>=8.0`, `pytest-asyncio>=0.24`, `pytest-cov>=5.0`, `mypy>=1.14`, `ruff>=0.8`, `pre-commit>=4.0`

### 3.2 Services Dependencies
**File:** `/home/user/NIGHTWATCH/services/requirements.txt`

- `skyfield~=1.48` — JPL ephemeris (DE440) for celestial calculations
- `aiohttp~=3.9` — Async HTTP client for weather and external APIs
- `pyserial~=3.5` — Serial communication (telescope mounts)
- `pyindi-client~=2.0.8` — INDI device control (Linux astronomy)
- `alpyca~=3.0.0` — ASCOM Alpaca network device protocol

### 3.3 Voice Pipeline Dependencies
**File:** `/home/user/NIGHTWATCH/voice/requirements.txt`

- `faster-whisper~=1.0.3` — Speech-to-text (CTranslate2 optimized)
- `piper-tts~=1.2.0` — Text-to-speech synthesis
- `sounddevice~=0.5.1` — Audio I/O
- `numpy~=1.26` — Numerical computing for audio processing
- `pymicro-vad~=1.0.0` — Neural voice activity detection
- `webrtcvad~=2.0.10` — Google WebRTC VAD (fallback)

### 3.4 Development Dependencies
**File:** `/home/user/NIGHTWATCH/requirements-dev.txt`

**Testing:** `pytest~=8.3`, `pytest-asyncio~=0.24`, `pytest-cov~=5.0`, `pytest-xdist~=3.5`, `pytest-timeout~=2.3`, `pytest-mock~=3.14`, `responses~=0.25`, `aioresponses~=0.7`

**Linting & Type Checking:** `ruff~=0.8`, `mypy~=1.14`, `types-PyYAML~=6.0`, `types-requests~=2.32`

**Development Tools:** `pre-commit~=4.0`, `docker~=7.1`, `ipython~=8.30`, `ipdb~=0.13`, `build~=1.2`, `twine~=5.1`

### 3.5 Dependency Lock File
**File:** `/home/user/NIGHTWATCH/uv.lock` (~460 KB)

Pinned transitive dependencies for reproducible builds via `uv` package manager.

---

## 4. Build, Run, Test, and Lint Commands

### 4.1 Installation and Running

**Primary Entry Point:**
```bash
# Via installed CLI command
nightwatch [--config /path/to/config.yaml] [--log-level DEBUG] [--dry-run]

# Via Python module
python -m nightwatch.main [options]

# Via bash launcher script
./bin/nightwatch [options]

# Windows batch launcher
.\bin\nightwatch.bat [options]
```
**Sources:** `/home/user/NIGHTWATCH/bin/nightwatch`, `/home/user/NIGHTWATCH/nightwatch/main.py` (lines 1–17)

**Installation:**
```bash
pip install -e ".[all]"           # Full development install
pip install -e ".[services]"      # Services only
pip install -e ".[voice]"         # Voice only
pip install -r requirements-dev.txt  # Dev dependencies
```

### 4.2 Testing Commands (from CI)
**File:** `/home/user/NIGHTWATCH/.github/workflows/ci.yml`

```bash
# Unit tests with coverage
pytest tests/unit/ -v \
  --cov=services --cov=nightwatch --cov=voice \
  --cov-report=term-missing --cov-report=xml:coverage.xml \
  --cov-report=html:coverage_html \
  -x --tb=short

# Integration tests (Alpaca simulators)
pytest tests/integration/test_device_layer.py -v --tb=short -m "alpaca" --timeout=120

# Full integration suite
pytest tests/integration/ -v --tb=short --timeout=120

# E2E tests
pytest tests/e2e/ -v --tb=short --timeout=180 -m "e2e"

# Mock service integration tests
pytest tests/integration/test_mount_catalog.py tests/integration/test_safety_mount.py -v
```

### 4.3 Linting and Type Checking
**File:** `/home/user/NIGHTWATCH/.github/workflows/ci.yml`

```bash
# Ruff linting
ruff check services/ voice/ nightwatch/ --ignore=E501,F401,F841 --output-format=github

# Ruff formatting check
ruff format --check services/ voice/ nightwatch/

# MyPy type checking
mypy nightwatch/ --ignore-missing-imports --no-error-summary --show-error-codes --pretty
mypy services/ --ignore-missing-imports --no-error-summary --show-error-codes --pretty
mypy voice/ --ignore-missing-imports --no-error-summary --show-error-codes --pretty

# Security scanning
bandit -r services/ nightwatch/ voice/ -ll -f txt --exclude "**/test*,**/*_test.py"
pip-audit --requirement services/requirements.txt --format columns

# Pre-commit hooks (local)
pre-commit install
pre-commit run --all-files
```

### 4.4 Docker and Deployment

**Docker Compose:**
```bash
docker compose -f docker/docker-compose.dev.yml up -d    # Development
docker compose -f docker/docker-compose.prod.yml up -d   # Production
docker compose -f docker/docker-compose.test.yml up -d   # Testing
```

**Deployment Scripts:**
- `/home/user/NIGHTWATCH/deploy/scripts/install.sh` — Installation script
- `/home/user/NIGHTWATCH/deploy/scripts/upgrade.sh` — Upgrade script

**Systemd Services:**
```bash
# Install service
sudo systemctl enable /home/user/NIGHTWATCH/deploy/systemd/nightwatch.service
sudo systemctl start nightwatch
sudo systemctl status nightwatch
```

---

## 5. Entry Points

### 5.1 CLI Entry Point
**Main Module:** `/home/user/NIGHTWATCH/nightwatch/main.py` (lines 1–50)

Exports:
- `main()` — CLI entry point with argparse
- `async_main()` — Async orchestration logic
- `create_parser()` — Argument parser builder

**Arguments:**
- `--config PATH` — Configuration file path
- `--log-level LEVEL` — Logging level (DEBUG, INFO, WARNING, ERROR)
- `--dry-run` — Validate config without starting
- `--help` — Show help

### 5.2 Voice and Tool Execution
**Modules:**
- `/home/user/NIGHTWATCH/nightwatch/voice_pipeline.py` (83.5 KB) — Voice command parsing and LLM integration
- `/home/user/NIGHTWATCH/nightwatch/tool_executor.py` (57 KB) — Executes telescope/weather/mount commands
- `/home/user/NIGHTWATCH/voice/tools/telescope_tools.py` (225 KB) — Exported telescope control functions

### 5.3 Orchestrator
**Module:** `/home/user/NIGHTWATCH/nightwatch/orchestrator.py` (121.7 KB)

Main orchestration class that coordinates:
- Service initialization
- Health monitoring
- LLM client communication
- Emergency response handling
- Safety interlocks

### 5.4 Services Initialization
**Module:** `/home/user/NIGHTWATCH/services/__init__.py` (3.3 KB)

Exports each service module for dynamic loading:
- Alert manager, Alpaca client, Plate solver, Camera, Catalog, Enclosure, Encoder, Ephemeris, Focuser, Guider, INDI, Meteor tracking, Mount control, NLP, Power, Safety monitor, Scheduler, Simulators, Voice trainer, Weather

---

## 6. Configuration and Environment Surface

### 6.1 Configuration File
**Path:** `./nightwatch.yaml` (current dir) → `~/.nightwatch/config.yaml` (user) → `/etc/nightwatch/config.yaml` (system)  
**Example:** `/home/user/NIGHTWATCH/nightwatch.yaml.example` (10.5 KB)

**Configuration Sections:**
- `site` — Observatory location (latitude, longitude, elevation, timezone)
- `mount` — Telescope mount (type, host, port, serial, timeout, retry)
- `weather` — Weather station (type, host, poll interval)
- `voice` — Speech pipeline (model, device, language)
- `tts` — Text-to-speech (model, device)
- `llm` — LLM backend (model, endpoint, api_key)
- `safety` — Safety thresholds (wind, humidity, temperature, rain)
- `camera` — Camera setup
- `guider` — Guide camera (PHD2)
- `encoder` — Mount encoders
- `alert` — Alert escalation
- `power` — Power management (reboot scheduling)
- `enclosure` — Roof/dome control

### 6.2 Environment Variables (NIGHTWATCH_ Prefix)

**Supported Override Pattern:** `NIGHTWATCH_<SECTION>_<KEY>=value`

Example:
```bash
NIGHTWATCH_MOUNT_HOST=192.168.1.100
NIGHTWATCH_SITE_LATITUDE=38.9
NIGHTWATCH_VOICE_MODEL=large-v3
```

**Safety Override Allowlist:** Empty by default (line 90 in `/home/user/NIGHTWATCH/nightwatch/config.py`)  
Only explicitly allowlisted safety thresholds can be overridden via env vars to prevent accidental disabling of safety interlocks.

**Source:** `/home/user/NIGHTWATCH/nightwatch/config.py` (lines 8–90)

### 6.3 Logging Configuration
**Module:** `/home/user/NIGHTWATCH/nightwatch/logging_config.py` (12.2 KB)

Configurable log levels and output handlers (console, file, structured).

### 6.4 Launcher Environment
**Script:** `/home/user/NIGHTWATCH/bin/nightwatch` (lines 14–17)

Recognized env vars:
- `NIGHTWATCH_CONFIG` — Configuration file path
- `NIGHTWATCH_LOG_LEVEL` — Logging verbosity
- `VIRTUAL_ENV` — Python venv activation path

---

## 7. Oddities and Special Features

### 7.1 No Generated Code, Vendored Dependencies, or Monorepo Boundaries
- No `generated/` directories detected
- No vendored third-party code; all dependencies managed via pyproject.toml and requirements files
- No git submodules (checked via `.gitmodules`)
- Single-package monorepo structure: core (`nightwatch`) + services layer (`services/`) + voice pipeline (`voice/`)

### 7.2 Large Files
**Lock File:** `/home/user/NIGHTWATCH/uv.lock` (~460 KB)  
Contains pinned transitive dependencies for `uv` package manager.

**Large Modules:**
- `nightwatch/orchestrator.py` (121.7 KB) — Main orchestration engine
- `voice/tools/telescope_tools.py` (225 KB) — Exported telescope command signatures for voice control
- `nightwatch/voice_pipeline.py` (83.5 KB) — Voice command parsing and LLM orchestration
- `nightwatch/llm_client.py` (42.8 KB) — LLM API client abstraction
- `nightwatch/tool_executor.py` (57 KB) — Tool execution and parameter validation
- `services/safety_monitor/monitor.py` (71 KB) — Safety interlock engine

### 7.3 Testing Infrastructure
**110 Python test files** across:
- `tests/unit/` — Unit tests (default, fast)
- `tests/integration/` — Tests requiring Docker simulators or mock services
- `tests/e2e/` — End-to-end voice flow tests
- `tests/hardware/` — Hardware tests (skipped in CI, require real telescope hardware)
- `tests/fixtures/` — Mock implementations of all services (weather, mount, camera, guider, LLM, etc.)

**Docker Simulators:**
- Mount simulator (`docker/simulators/Dockerfile.mount`)
- Camera simulator (`docker/simulators/Dockerfile.mount`)
- Weather simulator (`docker/simulators/Dockerfile.weather`)
- PHD2 guide simulator (`docker/simulators/Dockerfile.phd2`)
- Cloud watcher simulator (`docker/simulators/Dockerfile.cloud`)

### 7.4 Safety-Critical Features
**Module:** `/home/user/NIGHTWATCH/nightwatch/safety_interlock.py` (18.7 KB)

Implements:
- Dual-redundant rain sensor voting (SAFE-002)
- Hardware watchdog fail-safe (SAFE-004)
- Cancellation token propagation (ARCH-003)
- Safety threshold allowlisting (SAFE-003, line 90 of config.py)

### 7.5 Firmware Configuration
**Included:** `/home/user/NIGHTWATCH/firmware/onstepx_config/Config.h` (~200 lines)

OnStepX telescope controller configuration header (not built as part of Python app; provided for reference).

### 7.6 Structured Documentation
**Architecture Decisions:** `/home/user/NIGHTWATCH/docs/decisions/` (ADR format)  
**Research/Analysis:** `/home/user/NIGHTWATCH/docs/pos/` and `/home/user/NIGHTWATCH/pos/agents/` (Points of Study)  
**Agent Definitions:** `/home/user/NIGHTWATCH/.claude/agents/` (Claude Code agent roles)

### 7.7 Pre-commit Hooks (Mandatory)
**File:** `/home/user/NIGHTWATCH/.pre-commit-config.yaml` (155 lines)

Enforces before every commit:
- File format checks (trailing newlines, merge markers, case conflicts)
- YAML/TOML/JSON validation
- Private key detection
- Ruff linting and formatting (auto-fix)
- MyPy type checking (nightwatch only)
- Bandit security checks (excluding tests)
- No direct commits to main/master

---

## 8. Suggested Domain Decomposition

Based on L1 reconnaissance, this system decomposes into **5 primary domains** with clear architectural boundaries:

### 8.1 **Core Orchestration & Safety** (Decision Authority)
**Directories:**
- `nightwatch/` — Main orchestrator, config, logging, safety interlocks, health checks, emergency response
- `nightwatch/safety_interlock.py`, `nightwatch/emergency_response.py`, `nightwatch/watchdog.py`

**Responsibilities:**
- System state machine and lifecycle management
- Safety threshold enforcement and veto logic
- Configuration loading and validation
- Signal handling and graceful shutdown
- Health monitoring and watchdog timers

**Coupling:** Highest coupling; depends on all other domains  
**Test Coverage:** Unit and e2e tests in `tests/unit/`, `tests/e2e/`

---

### 8.2 **Voice & Natural Language Processing** (Input Interface)
**Directories:**
- `voice/` — Speech-to-text, text-to-speech, audio I/O, Wyoming protocol servers
  - `voice/stt/` — faster-whisper speech recognition
  - `voice/tts/` — piper-tts synthesis
  - `voice/wyoming/` — Wyoming voice protocol implementation
- `services/nlp/` — Clarification, conversation context, user preferences, sky description

**Responsibilities:**
- Audio capture and voice activity detection
- Speech-to-text inference (faster-whisper)
- Natural language understanding (conversation tracking, preferences)
- Text-to-speech synthesis (piper-tts)
- Wyoming protocol bridge for third-party integrations

**Coupling:** Upstream of tool execution; depends on LLM client for intent routing  
**Test Coverage:** Unit tests in `tests/unit/test_voice*`, fixtures in `tests/fixtures/mock_stt.py`, `tests/fixtures/mock_tts.py`

---

### 8.3 **Command Execution & Tool Integration** (Orchestration Agents)
**Directories:**
- `nightwatch/tool_executor.py` — Command parsing, parameter validation, tool invocation
- `nightwatch/response_formatter.py` — Format tool outputs for TTS/display
- `voice/tools/telescope_tools.py` — Exported telescope command signatures (225 KB)
- `voice/tools/meteor_tools.py` — Meteor and shower tracking commands
- `services/voice/vocabulary_trainer.py`, `services/voice/wake_word_trainer.py`

**Responsibilities:**
- Parse and validate voice commands into structured parameters
- Route commands to appropriate service modules
- Format structured responses for human-readable TTS
- Maintain vocabulary and command recognition models
- Tool parameter type validation and bounds checking

**Coupling:** Central hub between voice and hardware services; delegates to astronomy/device services  
**Test Coverage:** Unit tests, mock LLM in `tests/fixtures/mock_llm.py`

---

### 8.4 **Astronomy & Hardware Services** (Capability Modules)
**22 Service Modules in `services/`:**

**Astronomy/Observation:**
- `ephemeris/` — Skyfield celestial calculations (sun, moon, planets, custom objects)
- `catalog/` — Messier and object catalog with scoring and identification
- `astrometry/` — Plate solver integration (astrometry.net, ASTAP)
- `meteor_tracking/` — Fireball network, shower calendar, trajectory
- `guiding/` — PHD2 guide star auto-calibration and guiding loop

**Hardware Control:**
- `mount_control/` — LX200 and OnStepX commands (goto, park, unpark, sync)
- `camera/` — ZWO ASI camera capture and frame analysis
- `focus/` — Autofocus V-curve analysis and stepping
- `enclosure/` — Roof/dome open/close control
- `encoder/` — Mount encoder position tracking

**Infrastructure:**
- `alpaca/`, `indi/` — Device protocol clients (network and local)
- `weather/` — Ecowitt, AAG, WS90 weather station integration
- `power/` — Power management and scheduled reboots
- `safety_monitor/` — Real-time safety veto (wind, humidity, rain, temperature)
- `alerts/` — Alert escalation and notification

**Utility:**
- `scheduling/` — Cron-like task scheduling and condition evaluation
- `simulators/` — Mock mount, camera, guider, weather for testing

**Responsibilities:**
- Encapsulated hardware and external service communication
- State caching (position, temperature, etc.)
- Retry logic and connection resilience
- Async device operations

**Coupling:** Loosely coupled to each other; tightly coupled to orchestrator for dispatch  
**Test Coverage:** Unit per module, integration with Docker simulators, mocks in `tests/fixtures/`

---

### 8.5 **LLM Client & Tool Binding** (Decision Engine)
**Directories:**
- `nightwatch/llm_client.py` (42.8 KB) — LLM API client, token management, model abstraction
- `nightwatch/tool_params.py` — Tool parameter schema definitions
- `nightwatch/cancellation.py` — Async cancellation token propagation

**Responsibilities:**
- Abstract LLM backend (OpenAI-compatible API, local inference, etc.)
- Tool schema registration and parameter binding
- Token usage tracking and cost monitoring
- Request/response streaming and error handling
- Cancellation propagation for safe interruption

**Coupling:** Used by orchestrator and voice pipeline; knows about all tool signatures from command services  
**Test Coverage:** Unit tests with mock LLM in `tests/fixtures/mock_llm.py`

---

## Summary Table: Domain Allocation

| Domain | Directories | Purpose | Key Files |
|--------|-----------|---------|-----------|
| **Core Orchestration & Safety** | `nightwatch/` | System state, safety enforcement, lifecycle | `orchestrator.py`, `safety_interlock.py`, `config.py` |
| **Voice & NLP** | `voice/`, `services/nlp/` | Audio I/O, speech recognition, understanding | `voice_pipeline.py`, `whisper_service.py`, `clarification.py` |
| **Command Execution & Tools** | `nightwatch/tool_executor.py`, `voice/tools/` | Command routing, parameter validation | `tool_executor.py`, `telescope_tools.py` (225 KB) |
| **Astronomy & Hardware Services** | `services/` (22 modules) | Observatory hardware and external service integration | `services/*/`, simulators, device clients |
| **LLM Client & Tool Binding** | `nightwatch/llm_client.py`, `nightwatch/tool_params.py` | LLM abstraction, tool schema, token management | `llm_client.py`, `tool_params.py` |

Each domain can be reviewed, tested, and evolved independently by a focused team, with clear interfaces defined by the orchestrator's tool invocation API and configuration schemas.

