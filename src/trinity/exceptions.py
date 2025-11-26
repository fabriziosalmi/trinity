"""
Trinity Core - Custom Exception Hierarchy

Provides specific exception types for better error handling and debugging.
Replaces generic 'except Exception' blocks with domain-specific exceptions.
"""


class TrinityError(Exception):
    """Base exception for all Trinity errors."""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# Configuration Errors
class ConfigurationError(TrinityError):
    """Raised when configuration is invalid or missing."""
    pass


class ThemeNotFoundError(ConfigurationError):
    """Raised when a requested theme doesn't exist."""
    pass


class PathResolutionError(ConfigurationError):
    """Raised when a path cannot be resolved."""
    pass


# Content Generation Errors
class ContentGenerationError(TrinityError):
    """Base exception for content generation failures."""
    pass


class LLMConnectionError(ContentGenerationError):
    """Raised when LLM API connection fails."""
    pass


class LLMTimeoutError(ContentGenerationError):
    """Raised when LLM request times out."""
    pass


class LLMResponseError(ContentGenerationError):
    """Raised when LLM returns invalid or unparseable response."""
    pass


class ContentValidationError(ContentGenerationError):
    """Raised when generated content fails validation."""
    pass


# Build Errors
class BuildError(TrinityError):
    """Base exception for build failures."""
    pass


class TemplateNotFoundError(BuildError):
    """Raised when a template file cannot be found."""
    pass


class TemplateRenderError(BuildError):
    """Raised when template rendering fails."""
    pass


class CSSMergeError(BuildError):
    """Raised when CSS merging fails."""
    pass


# Guardian/QA Errors
class GuardianError(TrinityError):
    """Base exception for Guardian QA failures."""
    pass


class PlaywrightError(GuardianError):
    """Raised when Playwright browser automation fails."""
    pass


class ScreenshotError(GuardianError):
    """Raised when screenshot capture fails."""
    pass


class VisionAIError(GuardianError):
    """Raised when vision AI analysis fails."""
    pass


# Healing Errors
class HealingError(TrinityError):
    """Base exception for self-healing failures."""
    pass


class MaxRetriesExceededError(HealingError):
    """Raised when maximum retry attempts are exhausted."""
    pass


class HealingStrategyError(HealingError):
    """Raised when a healing strategy fails to execute."""
    pass


# ML/Prediction Errors
class MLError(TrinityError):
    """Base exception for ML operations."""
    pass


class ModelNotFoundError(MLError):
    """Raised when a trained model file cannot be found."""
    pass


class ModelLoadError(MLError):
    """Raised when model loading/deserialization fails."""
    pass


class PredictionError(MLError):
    """Raised when model prediction fails."""
    pass


class TrainingError(MLError):
    """Raised when model training fails."""
    pass


class DataValidationError(MLError):
    """Raised when training data is invalid."""
    pass


# Validation Errors
class ValidationError(TrinityError):
    """Base exception for validation failures."""
    pass


class SchemaValidationError(ValidationError):
    """Raised when data doesn't match expected schema."""
    pass


class FileValidationError(ValidationError):
    """Raised when file validation fails."""
    pass


# Resource Errors
class ResourceError(TrinityError):
    """Base exception for resource-related failures."""
    pass


class FileNotFoundError(ResourceError):
    """Raised when a required file is not found."""
    pass


class DirectoryNotFoundError(ResourceError):
    """Raised when a required directory is not found."""
    pass


class DiskSpaceError(ResourceError):
    """Raised when insufficient disk space is available."""
    pass


# Circuit Breaker Errors
class CircuitBreakerError(TrinityError):
    """Base exception for circuit breaker failures."""
    pass


class CircuitOpenError(CircuitBreakerError):
    """Raised when circuit breaker is open and requests are blocked."""
    pass


class CircuitHalfOpenError(CircuitBreakerError):
    """Raised when circuit is in half-open state testing recovery."""
    pass
