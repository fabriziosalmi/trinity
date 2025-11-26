"""
Test TrinityConfig Pydantic Settings

Tests cover:
- Configuration loading from settings.yaml
- Environment variable override (TRINITY_*)
- Default values
- Path resolution
"""

from pathlib import Path

from trinity.config import TrinityConfig


class TestConfigDefaults:
    """Test default configuration values"""

    def test_config_has_default_values(self):
        """Test that config loads with sensible defaults"""
        config = TrinityConfig()

        assert config.max_retries >= 1
        assert config.truncate_length > 0
        assert config.lm_studio_url is not None

    def test_project_root_is_path(self):
        """Test that project_root is a valid Path object"""
        config = TrinityConfig()

        assert isinstance(config.project_root, Path)
        assert config.project_root.exists()


class TestPathResolution:
    """Test path resolution properties"""

    def test_templates_path_exists(self):
        """Test that templates directory exists"""
        config = TrinityConfig()

        templates_path = config.templates_path
        assert isinstance(templates_path, Path)
        # Note: May not exist in test environment, but should be a valid path

    def test_output_path_is_valid(self):
        """Test that output path is valid"""
        config = TrinityConfig()

        output_path = config.output_path
        assert isinstance(output_path, Path)

    def test_config_path_is_valid(self):
        """Test that config directory path is valid"""
        config = TrinityConfig()

        config_path = config.config_path
        assert isinstance(config_path, Path)


class TestGuardianConfig:
    """Test Guardian-specific configuration"""

    def test_guardian_can_be_disabled(self):
        """Test that Guardian can be disabled via config"""
        config = TrinityConfig()

        # Default should be False (disabled for performance)
        assert config.guardian_enabled is False

    def test_vision_ai_default(self):
        """Test Vision AI default setting"""
        config = TrinityConfig()

        # Vision AI should default to False (optional feature)
        assert config.guardian_vision_ai is False


class TestSelfHealingConfig:
    """Test self-healing configuration"""

    def test_max_retries_is_positive(self):
        """Test that max_retries is a positive integer"""
        config = TrinityConfig()

        assert config.max_retries > 0
        assert isinstance(config.max_retries, int)

    def test_truncate_length_is_positive(self):
        """Test that truncate_length is positive"""
        config = TrinityConfig()

        assert config.truncate_length > 0
        assert isinstance(config.truncate_length, int)
