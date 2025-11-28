"""
Trinity - Secrets Management

Secure storage and retrieval of API keys and sensitive configuration.
Integrates with system keyring and supports multiple backends.

Backends:
- System keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Environment variables (fallback)
- .env file (development only, not recommended for production)

Usage:
    >>> from trinity.utils.secrets import secrets_manager
    >>>
    >>> # Store API key
    >>> secrets_manager.set_secret("openai_api_key", "sk-...")
    >>>
    >>> # Retrieve API key
    >>> api_key = secrets_manager.get_secret("openai_api_key")
    >>>
    >>> # Delete API key
    >>> secrets_manager.delete_secret("openai_api_key")
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional, cast

from trinity.exceptions import ConfigurationError
from trinity.utils.logger import get_logger

logger = get_logger(__name__)

# Try to import keyring (optional dependency)
try:
    import keyring  # type: ignore

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning(
        "keyring package not available. Install with: pip install keyring\n"
        "Falling back to environment variables for secrets."
    )


class SecretBackend(Enum):
    """Secret storage backends."""

    KEYRING = "keyring"  # System keyring (most secure)
    ENVIRONMENT = "environment"  # Environment variables
    DOTENV = "dotenv"  # .env file (dev only)


class SecretsManager:
    """
    Manages secure storage and retrieval of secrets.

    Priority (highest to lowest):
    1. System keyring (if available)
    2. Environment variables
    3. .env file (development only)
    """

    SERVICE_NAME = "trinity-core"

    def __init__(self, prefer_keyring: bool = True, dotenv_path: Optional[Path] = None):
        """
        Initialize secrets manager.

        Args:
            prefer_keyring: Prefer keyring over environment variables
            dotenv_path: Path to .env file (optional)
        """
        self.prefer_keyring = prefer_keyring and KEYRING_AVAILABLE
        self.dotenv_path = dotenv_path or Path(".env")

        if self.prefer_keyring:
            logger.info("🔐 Secrets manager initialized with system keyring")
        else:
            logger.info(
                "🔐 Secrets manager initialized with environment variables "
                "(keyring not available or disabled)"
            )

    def get_secret(
        self, key: str, default: Optional[str] = None, required: bool = False
    ) -> Optional[str]:
        """
        Retrieve a secret.

        Args:
            key: Secret key name
            default: Default value if not found
            required: Raise error if secret not found

        Returns:
            Secret value or default

        Raises:
            ConfigurationError: If secret is required but not found
        """
        # Normalize key name
        key_normalized = key.upper().replace("-", "_")

        # Try keyring first (most secure)
        if self.prefer_keyring:
            try:
                value = cast(Optional[str], keyring.get_password(self.SERVICE_NAME, key_normalized))
                if value:
                    logger.debug(f"Retrieved secret '{key}' from keyring")
                    return value
            except Exception as e:
                logger.warning(f"Failed to retrieve '{key}' from keyring: {e}")

        # Try environment variables
        value = os.getenv(key_normalized) or os.getenv(f"TRINITY_{key_normalized}")
        if value:
            logger.debug(f"Retrieved secret '{key}' from environment")
            return value

        # Try .env file (dev only)
        if self.dotenv_path.exists():
            try:
                with open(self.dotenv_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if "=" in line:
                                env_key, env_value = line.split("=", 1)
                                if env_key.strip() == key_normalized:
                                    logger.debug(f"Retrieved secret '{key}' from .env")
                                    return env_value.strip().strip('"').strip("'")
            except Exception as e:
                logger.warning(f"Failed to read .env file: {e}")

        # Not found
        if required:
            raise ConfigurationError(
                f"Required secret '{key}' not found in keyring, environment, or .env file",
                details={
                    "key": key,
                    "keyring_available": KEYRING_AVAILABLE,
                    "dotenv_exists": self.dotenv_path.exists(),
                },
            )

        logger.debug(f"Secret '{key}' not found, using default")
        return default

    def set_secret(self, key: str, value: str) -> None:
        """
        Store a secret.

        Args:
            key: Secret key name
            value: Secret value

        Raises:
            ConfigurationError: If storage fails
        """
        key_normalized = key.upper().replace("-", "_")

        if self.prefer_keyring:
            try:
                keyring.set_password(self.SERVICE_NAME, key_normalized, value)
                logger.info(f"✅ Stored secret '{key}' in system keyring")
                return
            except Exception as e:
                logger.error(f"Failed to store '{key}' in keyring: {e}")
                raise ConfigurationError(
                    f"Failed to store secret '{key}' in keyring",
                    details={"key": key, "error": str(e)},
                )
        else:
            logger.warning(
                f"Keyring not available. Please set environment variable: "
                f"export {key_normalized}='your_value'"
            )
            raise ConfigurationError(
                f"Cannot store secret '{key}' without keyring support",
                details={"key": key, "suggestion": f"export {key_normalized}='your_value'"},
            )

    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret.

        Args:
            key: Secret key name

        Returns:
            True if deleted, False if not found
        """
        key_normalized = key.upper().replace("-", "_")

        if self.prefer_keyring:
            try:
                keyring.delete_password(self.SERVICE_NAME, key_normalized)
                logger.info(f"🗑️  Deleted secret '{key}' from keyring")
                return True
            except keyring.errors.PasswordDeleteError:
                logger.debug(f"Secret '{key}' not found in keyring")
                return False
            except Exception as e:
                logger.error(f"Failed to delete '{key}' from keyring: {e}")
                return False
        else:
            logger.warning(
                f"Keyring not available. Manually unset environment variable: "
                f"unset {key_normalized}"
            )
            return False

    def list_secrets(self) -> list[str]:
        """
        List all stored secret keys.

        Returns:
            List of secret key names
        """
        # Note: keyring doesn't provide a native list operation
        # This is a placeholder for future implementation
        logger.warning("list_secrets() not fully implemented")
        return []

    def get_backend_info(self) -> dict[str, Any]:
        """
        Get information about the active backend.

        Returns:
            Dictionary with backend details
        """
        backend = SecretBackend.KEYRING if self.prefer_keyring else SecretBackend.ENVIRONMENT

        backend_details = {}
        if KEYRING_AVAILABLE:
            try:
                backend_details["keyring_backend"] = str(keyring.get_keyring())
            except:
                backend_details["keyring_backend"] = "unknown"

        return {
            "active_backend": backend.value,
            "keyring_available": KEYRING_AVAILABLE,
            "keyring_preferred": self.prefer_keyring,
            "dotenv_path": str(self.dotenv_path),
            "dotenv_exists": self.dotenv_path.exists(),
            **backend_details,
        }


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create global secrets manager."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


# Convenience alias
secrets_manager = get_secrets_manager()
