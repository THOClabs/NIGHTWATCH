"""
Unit tests for NIGHTWATCH configuration system.

Tests configuration loading, validation, and environment variable overrides.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

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
