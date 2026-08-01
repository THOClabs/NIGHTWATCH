"""
Unit tests for NIGHTWATCH configuration system.

Tests configuration loading, validation, and environment variable overrides.
"""

import logging
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from nightwatch import config as config_module
from nightwatch.config import (
    AlertConfig,
    CameraConfig,
    EnclosureConfig,
    EncoderConfig,
    GuiderConfig,
    LLMConfig,
    MountConfig,
    NightwatchConfig,
    PowerConfig,
    SafetyConfig,
    SiteConfig,
    TTSConfig,
    VoiceConfig,
    WeatherConfig,
    get_config_paths,
    load_config,
)
from nightwatch.exceptions import ConfigurationError


class TestSiteConfig:
    """Tests for SiteConfig dataclass."""

    def test_default_values(self) -> None:
        """Test SiteConfig has sensible defaults."""
        config = SiteConfig()
        assert config.latitude == 38.9
        assert config.longitude == -117.4
        assert config.elevation == 1800.0
        assert config.timezone == "America/Los_Angeles"
        assert config.name == "NIGHTWATCH Observatory"

    def test_latitude_range(self) -> None:
        """Test latitude validation (-90 to 90)."""
        # Valid latitudes
        SiteConfig(latitude=0.0)
        SiteConfig(latitude=90.0)
        SiteConfig(latitude=-90.0)

        # Invalid latitudes
        with pytest.raises(ValueError):
            SiteConfig(latitude=91.0)
        with pytest.raises(ValueError):
            SiteConfig(latitude=-91.0)

    def test_longitude_range(self) -> None:
        """Test longitude validation (-180 to 180)."""
        # Valid longitudes
        SiteConfig(longitude=0.0)
        SiteConfig(longitude=180.0)
        SiteConfig(longitude=-180.0)

        # Invalid longitudes
        with pytest.raises(ValueError):
            SiteConfig(longitude=181.0)
        with pytest.raises(ValueError):
            SiteConfig(longitude=-181.0)

    def test_timezone_validation(self) -> None:
        """Test timezone format validation."""
        # Valid timezones
        SiteConfig(timezone="America/New_York")
        SiteConfig(timezone="UTC")
        SiteConfig(timezone="GMT")

        # Invalid timezone format
        with pytest.raises(ValueError):
            SiteConfig(timezone="EST")


class TestMountConfig:
    """Tests for MountConfig dataclass."""

    def test_default_values(self) -> None:
        """Test MountConfig has sensible defaults."""
        config = MountConfig()
        assert config.type == "onstepx"
        assert config.host == "onstep.local"
        assert config.port == 9999
        assert config.timeout == 5.0
        assert config.retry_count == 3

    def test_port_range(self) -> None:
        """Test port validation (1-65535)."""
        MountConfig(port=1)
        MountConfig(port=65535)

        with pytest.raises(ValueError):
            MountConfig(port=0)
        with pytest.raises(ValueError):
            MountConfig(port=65536)

    def test_mount_types(self) -> None:
        """Test valid mount type literals."""
        for mount_type in ["onstepx", "lx200", "indi", "alpaca", "simulator"]:
            config = MountConfig(type=mount_type)
            assert config.type == mount_type


class TestWeatherConfig:
    """Tests for WeatherConfig dataclass."""

    def test_default_values(self) -> None:
        """Test WeatherConfig has sensible defaults."""
        config = WeatherConfig()
        assert config.enabled is True
        assert config.type == "ecowitt"
        assert config.poll_interval == 30.0
        assert config.stale_threshold == 120.0

    def test_poll_interval_range(self) -> None:
        """Test poll interval validation (5-300 seconds)."""
        WeatherConfig(poll_interval=5.0)
        WeatherConfig(poll_interval=300.0)

        with pytest.raises(ValueError):
            WeatherConfig(poll_interval=4.0)
        with pytest.raises(ValueError):
            WeatherConfig(poll_interval=301.0)


class TestSafetyConfig:
    """Tests for SafetyConfig dataclass."""

    def test_default_thresholds(self) -> None:
        """Test safety thresholds match POS Day 4 recommendations."""
        config = SafetyConfig()
        # Wind thresholds
        assert config.wind_limit_warning == 20.0
        assert config.wind_limit_park == 25.0
        assert config.wind_limit_emergency == 30.0
        # Humidity thresholds
        assert config.humidity_limit_warning == 75.0
        assert config.humidity_limit_park == 80.0
        assert config.humidity_limit_emergency == 85.0
        # Rain holdoff
        assert config.rain_holdoff_minutes == 30.0

    def test_sensor_timeout_range(self) -> None:
        """Test sensor timeout validation."""
        SafetyConfig(sensor_timeout=30.0)
        SafetyConfig(sensor_timeout=600.0)

        with pytest.raises(ValueError):
            SafetyConfig(sensor_timeout=29.0)


class TestVoiceConfig:
    """Tests for VoiceConfig dataclass."""

    def test_default_values(self) -> None:
        """Test VoiceConfig has DGX Spark optimized defaults."""
        config = VoiceConfig()
        assert config.enabled is True
        assert config.model == "large-v3"
        assert config.device == "auto"
        assert config.compute_type == "int8_float16"

    def test_wyoming_host_defaults_to_loopback(self) -> None:
        """SEC3-1: STT Wyoming server must bind loopback by default."""
        assert VoiceConfig().wyoming_host == "127.0.0.1"


class TestTTSConfigSecurity:
    """SEC3-1: security-relevant TTS config defaults."""

    def test_wyoming_host_defaults_to_loopback(self) -> None:
        """SEC3-1: TTS Wyoming server must bind loopback by default."""
        assert TTSConfig().wyoming_host == "127.0.0.1"


class TestNightwatchConfig:
    """Tests for master NightwatchConfig class."""

    def test_default_configuration(self) -> None:
        """Test NightwatchConfig creates all subsystems with defaults."""
        config = NightwatchConfig()

        # Check all subsystems exist
        assert isinstance(config.site, SiteConfig)
        assert isinstance(config.mount, MountConfig)
        assert isinstance(config.weather, WeatherConfig)
        assert isinstance(config.voice, VoiceConfig)
        assert isinstance(config.tts, TTSConfig)
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.safety, SafetyConfig)
        assert isinstance(config.camera, CameraConfig)
        assert isinstance(config.guider, GuiderConfig)
        assert isinstance(config.encoder, EncoderConfig)
        assert isinstance(config.enclosure, EnclosureConfig)
        assert isinstance(config.power, PowerConfig)
        assert isinstance(config.alerts, AlertConfig)

    def test_partial_configuration(self) -> None:
        """Test NightwatchConfig accepts partial overrides."""
        config = NightwatchConfig(
            site={"latitude": 40.0, "longitude": -120.0},
            mount={"host": "192.168.1.100"},
        )

        assert config.site.latitude == 40.0
        assert config.site.longitude == -120.0
        # Default still applied
        assert config.site.elevation == 1800.0
        assert config.mount.host == "192.168.1.100"
        assert config.mount.port == 9999  # Default

    def test_log_level_options(self) -> None:
        """Test valid log level literals."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = NightwatchConfig(log_level=level)
            assert config.log_level == level


class TestConfigFilePaths:
    """Tests for config file path discovery."""

    def test_get_config_paths_returns_list(self) -> None:
        """Test get_config_paths returns expected paths."""
        paths = get_config_paths()
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert all(isinstance(p, Path) for p in paths)

    def test_config_paths_include_current_dir(self) -> None:
        """Test current directory is checked first."""
        paths = get_config_paths()
        assert Path("./nightwatch.yaml") in paths

    def test_config_paths_include_home_dir(self) -> None:
        """Test home directory is included."""
        paths = get_config_paths()
        home = Path.home()
        assert home / ".nightwatch" / "config.yaml" in paths


class TestLoadConfig:
    """Tests for configuration loading."""

    def test_load_default_config(self) -> None:
        """Test loading config with no file returns defaults."""
        config = load_config()
        assert isinstance(config, NightwatchConfig)
        assert config.site.latitude == 38.9

    def test_load_from_yaml_file(self) -> None:
        """Test loading config from YAML file."""
        config_data = {
            "site": {
                "latitude": 45.0,
                "longitude": -122.0,
                "name": "Test Observatory",
            },
            "mount": {
                "host": "test.local",
                "port": 8888,
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)
            assert config.site.latitude == 45.0
            assert config.site.longitude == -122.0
            assert config.site.name == "Test Observatory"
            assert config.mount.host == "test.local"
            assert config.mount.port == 8888
            # Defaults still applied
            assert config.site.elevation == 1800.0
        finally:
            os.unlink(temp_path)

    def test_load_nonexistent_file_raises_error(self) -> None:
        """Test loading nonexistent file raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            load_config("/nonexistent/path/config.yaml")
        assert "not found" in str(exc_info.value)

    def test_load_invalid_yaml_raises_error(self) -> None:
        """Test loading invalid YAML raises ConfigurationError."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(temp_path)
            assert "Invalid YAML" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_load_invalid_config_raises_error(self) -> None:
        """Test loading invalid config values raises ConfigurationError."""
        config_data = {
            "site": {
                "latitude": 999.0,  # Invalid latitude
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config(temp_path)
            assert "validation failed" in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_env_override_string(self) -> None:
        """Test environment variable overrides string values."""
        os.environ["NIGHTWATCH_MOUNT_HOST"] = "env-override.local"
        try:
            config = load_config()
            assert config.mount.host == "env-override.local"
        finally:
            del os.environ["NIGHTWATCH_MOUNT_HOST"]

    def test_env_override_integer(self) -> None:
        """Test environment variable overrides integer values."""
        os.environ["NIGHTWATCH_MOUNT_PORT"] = "1234"
        try:
            config = load_config()
            assert config.mount.port == 1234
        finally:
            del os.environ["NIGHTWATCH_MOUNT_PORT"]

    def test_env_override_float(self) -> None:
        """Test environment variable overrides float values."""
        os.environ["NIGHTWATCH_SITE_LATITUDE"] = "42.5"
        try:
            config = load_config()
            assert config.site.latitude == 42.5
        finally:
            del os.environ["NIGHTWATCH_SITE_LATITUDE"]

    def test_env_override_boolean(self) -> None:
        """Test environment variable overrides boolean values."""
        os.environ["NIGHTWATCH_WEATHER_ENABLED"] = "false"
        try:
            config = load_config()
            assert config.weather.enabled is False
        finally:
            del os.environ["NIGHTWATCH_WEATHER_ENABLED"]

    def test_env_override_with_file(self) -> None:
        """Test environment variables override file values."""
        config_data = {
            "mount": {"host": "file-host.local"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        os.environ["NIGHTWATCH_MOUNT_HOST"] = "env-host.local"
        try:
            config = load_config(temp_path)
            # Environment should override file
            assert config.mount.host == "env-host.local"
        finally:
            del os.environ["NIGHTWATCH_MOUNT_HOST"]
            os.unlink(temp_path)


class TestSafetyEnvOverrideAllowlist:
    """Tests for SAFE-003: env-var override allowlist for safety thresholds.

    Risk #5: Without the allowlist, an operator could silently disable wind/
    humidity/temperature protection via `NIGHTWATCH_SAFETY_*=<unsafe value>`.
    The allowlist is the conservative default (empty set) — any safety env
    override is rejected with a CRITICAL log and the YAML/default value wins.
    """

    def test_safety_env_override_rejected_when_not_in_allowlist(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A safety env var not in the allowlist must NOT take effect.

        Verifies the SAFE-003 spec line: starting with a safety env override
        falls back to the YAML/default value (default wind_limit_park=25.0).
        """
        # Sanity: the target key must NOT be on the allowlist for this test
        # to exercise the rejection path. If a future commit allowlists it,
        # this assertion will catch the test drift.
        assert "wind_limit_park" not in config_module.SAFETY_ENV_OVERRIDE_ALLOWLIST

        os.environ["NIGHTWATCH_SAFETY_WIND_LIMIT_PARK"] = "999"
        try:
            with caplog.at_level(logging.CRITICAL, logger="nightwatch.config"):
                config = load_config()
            # Default value preserved — env override was rejected
            assert config.safety.wind_limit_park == 25.0
            # A CRITICAL log was emitted naming the rejected env var
            critical_records = [
                r for r in caplog.records if r.levelno == logging.CRITICAL
            ]
            assert len(critical_records) >= 1, (
                "Expected at least one CRITICAL log for rejected safety override"
            )
            joined = " ".join(r.getMessage() for r in critical_records)
            assert "NIGHTWATCH_SAFETY_WIND_LIMIT_PARK" in joined
            assert "wind_limit_park" in joined
        finally:
            del os.environ["NIGHTWATCH_SAFETY_WIND_LIMIT_PARK"]

    def test_safety_env_override_wind_limit_mph_alias_also_rejected(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The spec's literal verify line: WIND_LIMIT_MPH must be rejected too.

        Even though `wind_limit_mph` is not a defined SafetyConfig field (and
        would be silently dropped by pydantic), it is still a SAFETY-section
        env override and must trip the allowlist guard — operators should see
        a loud warning rather than a silent no-op.
        """
        os.environ["NIGHTWATCH_SAFETY_WIND_LIMIT_MPH"] = "999"
        try:
            with caplog.at_level(logging.CRITICAL, logger="nightwatch.config"):
                config = load_config()
            # Defaults preserved
            assert config.safety.wind_limit_park == 25.0
            assert config.safety.wind_limit_warning == 20.0
            # CRITICAL log emitted
            critical_records = [
                r for r in caplog.records if r.levelno == logging.CRITICAL
            ]
            assert any(
                "NIGHTWATCH_SAFETY_WIND_LIMIT_MPH" in r.getMessage()
                for r in critical_records
            )
        finally:
            del os.environ["NIGHTWATCH_SAFETY_WIND_LIMIT_MPH"]

    def test_safety_env_override_critical_log_names_allowlist(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """For transparency, the rejection log must name the allowlist contents.

        Per the SAFE-003 spec: the warning should identify what IS permitted
        so an operator can either edit the allowlist (code review) or use the
        correct config-file path.
        """
        os.environ["NIGHTWATCH_SAFETY_HUMIDITY_LIMIT_EMERGENCY"] = "100"
        try:
            with caplog.at_level(logging.CRITICAL, logger="nightwatch.config"):
                load_config()
            critical_records = [
                r for r in caplog.records if r.levelno == logging.CRITICAL
            ]
            joined = " ".join(r.getMessage() for r in critical_records)
            if config_module.SAFETY_ENV_OVERRIDE_ALLOWLIST:
                for allowed in config_module.SAFETY_ENV_OVERRIDE_ALLOWLIST:
                    assert allowed in joined
            else:
                # Empty allowlist must still be mentioned (e.g. "allowlist=set()"
                # or "no safety overrides permitted")
                assert (
                    "allowlist" in joined.lower()
                    or "no safety" in joined.lower()
                )
        finally:
            del os.environ["NIGHTWATCH_SAFETY_HUMIDITY_LIMIT_EMERGENCY"]

    def test_safety_env_override_permitted_when_in_allowlist(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When a key IS on the allowlist, the env override takes effect.

        Documents the positive path. Patches the allowlist in-place to permit
        `wind_limit_park` for the duration of the test, then asserts the env
        value flows through. This ensures the guard is a real allowlist
        (deny-by-default with an explicit allow) rather than a blanket block.
        """
        monkeypatch.setattr(
            config_module,
            "SAFETY_ENV_OVERRIDE_ALLOWLIST",
            frozenset({"wind_limit_park"}),
        )
        os.environ["NIGHTWATCH_SAFETY_WIND_LIMIT_PARK"] = "27"
        try:
            config = config_module.load_config()
            assert config.safety.wind_limit_park == 27.0
        finally:
            del os.environ["NIGHTWATCH_SAFETY_WIND_LIMIT_PARK"]

    def test_non_safety_env_overrides_unaffected_by_allowlist(self) -> None:
        """Allowlist guards ONLY the safety section — others continue to work.

        Regression check: SAFE-003 must not break the existing env-override
        contract for mount/site/weather/etc.
        """
        os.environ["NIGHTWATCH_MOUNT_HOST"] = "non-safety-host.local"
        try:
            config = load_config()
            assert config.mount.host == "non-safety-host.local"
        finally:
            del os.environ["NIGHTWATCH_MOUNT_HOST"]


class TestConfigIntegration:
    """Integration tests for configuration system."""

    def test_full_config_roundtrip(self) -> None:
        """Test creating, saving, and loading a full configuration."""
        # Create config with custom values
        original = NightwatchConfig(
            site=SiteConfig(latitude=35.0, longitude=-115.0, name="Test Site"),
            mount=MountConfig(host="mount.local", port=9999),
            safety=SafetyConfig(wind_limit_park=30.0),
        )

        # Convert to dict and save to YAML
        config_dict = original.model_dump()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_dict, f)
            temp_path = f.name

        try:
            # Load back and verify
            loaded = load_config(temp_path)
            assert loaded.site.latitude == 35.0
            assert loaded.site.longitude == -115.0
            assert loaded.site.name == "Test Site"
            assert loaded.mount.host == "mount.local"
            assert loaded.safety.wind_limit_park == 30.0
        finally:
            os.unlink(temp_path)
