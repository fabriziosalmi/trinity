"""
Trinity Engine - Main Orchestrator

Coordinates the build → audit → heal → retry cycle.
Implements the Self-Healing Loop with intelligent fix strategies.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from trinity.components.brain import ContentEngine
from trinity.components.builder import SiteBuilder
from trinity.components.dataminer import TrinityMiner
from trinity.components.guardian import TrinityGuardian
from trinity.components.healer import SmartHealer
from trinity.components.neural_healer import NeuralHealer
from trinity.components.predictor import LayoutRiskPredictor
from trinity.config import TrinityConfig
from trinity.utils.logger import get_logger
from trinity.utils.validators import ContentValidator, ValidationError

logger = get_logger(__name__)


class BuildStatus(str, Enum):
    """Build result status."""

    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    PARTIAL = "partial"


class BuildResult(BaseModel):
    """Structured build result."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: BuildStatus
    output_path: Optional[Path] = None
    theme: str
    attempts: int = 0
    guardian_report: Optional[Dict[str, Any]] = None
    fixes_applied: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class TrinityEngine:
    """
    Main orchestrator for Trinity.

    Coordinates:
    - Content generation (Brain)
    - Site building (Builder)
    - Layout QA (Guardian)
    - Self-healing (Healer)
    """

    def __init__(self, config: Optional[TrinityConfig] = None, use_neural_healer: bool = False):
        """
        Initialize Trinity Engine.

        Args:
            config: Trinity configuration (uses defaults if None)
            use_neural_healer: Use Neural Healer (v0.5.0) instead of SmartHealer
        """
        self.config = config or TrinityConfig()
        self.use_neural_healer = use_neural_healer

        # Initialize components
        self.builder = SiteBuilder(template_dir=str(self.config.templates_path))
        self.validator = ContentValidator()

        # Healer: Neural (v0.5.0 LSTM) or Smart (heuristic)
        if use_neural_healer:
            self.healer = NeuralHealer.from_default_paths(fallback_to_heuristic=True)
            logger.info("🧠 Neural Healer activated (LSTM-based CSS generation)")
        else:
            self.healer = SmartHealer(truncate_length=self.config.truncate_length)
            logger.info("🚑 SmartHealer activated (heuristic strategies)")

        self.miner = TrinityMiner()  # ML dataset collector

        # Guardian is lazy-loaded when needed
        self._guardian: Optional[TrinityGuardian] = None

        # Risk predictor (Phase 3: lazy-load trained model)
        self._predictor: Optional[LayoutRiskPredictor] = None

        logger.info("🚀 TrinityEngine initialized")

    @property
    def guardian(self) -> TrinityGuardian:
        """Lazy-load Guardian (Playwright is heavy)."""
        if self._guardian is None:
            self._guardian = TrinityGuardian(
                enable_vision_ai=self.config.guardian_vision_ai,
                viewport_width=self.config.guardian_viewport_width,
                viewport_height=self.config.guardian_viewport_height,
            )
            logger.info("🛡️  Guardian loaded")
        return self._guardian

    @property
    def predictor(self) -> LayoutRiskPredictor:
        """Lazy-load ML Risk Predictor (Rule #66: Load once)."""
        if self._predictor is None:
            self._predictor = LayoutRiskPredictor()
            logger.info("🔮 Predictor loaded")
        return self._predictor
        return self._guardian

    def build_with_self_healing(
        self,
        content: Dict[str, Any],
        theme: str,
        output_filename: str,
        enable_guardian: bool = False,
    ) -> BuildResult:
        """
        Build page with Self-Healing Loop.

        Args:
            content: Content dictionary (validated)
            theme: Theme name
            output_filename: Output HTML filename
            enable_guardian: Enable Guardian QA and self-healing

        Returns:
            BuildResult with status and metadata
        """
        logger.info(
            f"🔨 Starting build: {output_filename} (theme={theme}, guardian={enable_guardian})"
        )

        # Validate content upfront
        try:
            self.validator.validate_content_schema(content)
        except ValidationError as e:
            logger.error(f"Content validation failed: {e}")
            return BuildResult(
                status=BuildStatus.FAILED, theme=theme, errors=[f"Content validation failed: {e}"]
            )

        # Self-Healing Loop
        max_retries = self.config.max_retries if enable_guardian else 1
        attempt = 0
        current_content = content
        current_style_overrides: Dict[str, str] = {}  # Track CSS overrides
        fixes_applied = []

        # 🔮 Phase 3: Pre-Cognition (v0.8.0: predict WHICH strategy, not just risk)
        if enable_guardian and self.config.predictive_enabled:
            # v0.8.0: Calculate density features for multiclass prediction
            css_density_spacing = 0  # TODO: Extract from theme
            css_density_layout = 0   # TODO: Extract from theme
            
            # Calculate pathological score from content
            from trinity.components.dataminer import TrinityMiner
            miner = TrinityMiner()
            pathological_score = miner._calculate_pathological_score(content)
            
            # Get multiclass strategy recommendation
            prediction = self.predictor.predict_best_strategy(
                content=content,
                theme=theme,
                css_density_spacing=css_density_spacing,
                css_density_layout=css_density_layout,
                pathological_score=pathological_score
            )

            if prediction["prediction_available"]:
                strategy_name = prediction["strategy_name"]
                confidence = prediction["confidence"]
                
                logger.info(
                    f"🔮 Neural Predictor: Recommends {strategy_name} "
                    f"(confidence: {confidence:.0%})"
                )

                # Smart strategy selection based on ML recommendation
                if strategy_name != "NONE" and confidence > 0.6:
                    logger.warning(
                        f"⚡ Skipping to recommended strategy: {strategy_name} "
                        f"(predicted by multiclass model)"
                    )
                    
                    # Map strategy name to attempt number for healer
                    strategy_to_attempt = {
                        "CSS_BREAK_WORD": 1,
                        "FONT_SHRINK": 2,
                        "CSS_TRUNCATE": 3,
                        "CONTENT_CUT": 4
                    }
                    
                    recommended_attempt = strategy_to_attempt.get(strategy_name, 1)
                    
                    # Create mock guardian report for pre-emptive healing
                    mock_report = {
                        "approved": False,
                        "status": "fail",
                        "reason": f"ML predicted {strategy_name} needed",
                        "issues": [f"Multiclass model recommends {strategy_name}"],
                        "fix_suggestion": strategy_name.lower(),
                    }
                    
                    preemptive_fix = self.healer.heal_layout(
                        guardian_report=mock_report,
                        content=content,
                        attempt=recommended_attempt,  # Use ML-recommended strategy
                    )
                    
                    if preemptive_fix.style_overrides:
                        current_style_overrides = preemptive_fix.style_overrides
                        fixes_applied.append(
                            f"Pre-emptive {strategy_name} (ML confidence: {confidence:.0%})"
                        )

        while attempt < max_retries:
            attempt += 1
            logger.info(f"🔄 Build Attempt {attempt}/{max_retries}")

            # 1. Build page with current style overrides
            try:
                output_path = self.builder.build_page(
                    content=current_content,
                    theme=theme,
                    output_filename=output_filename,
                    style_overrides=current_style_overrides if current_style_overrides else None,
                )
                logger.info(f"✓ Page built: {output_path}")
            except Exception as e:
                logger.error(f"Build failed: {e}")
                return BuildResult(
                    status=BuildStatus.FAILED,
                    theme=theme,
                    attempts=attempt,
                    errors=[f"Build error: {e}"],
                )

            # 2. If Guardian disabled, return success
            if not enable_guardian:
                logger.info("✅ Build complete (Guardian disabled)")

                # Log successful build to training dataset (positive sample without Guardian check)
                current_strategy = fixes_applied[-1].split(" ")[0] if fixes_applied else "NONE"
                self.miner.log_build_event(
                    theme=theme,
                    content=current_content,
                    strategy=current_strategy,
                    guardian_verdict=True,  # Assume success (no Guardian = pass)
                    guardian_reason="",
                    css_overrides=current_style_overrides if current_style_overrides else None,
                )

                return BuildResult(
                    status=BuildStatus.SUCCESS,
                    output_path=output_path,
                    theme=theme,
                    attempts=attempt,
                )

            # 3. Guardian Audit
            try:
                logger.info("👁️  Guardian inspecting layout...")
                abs_path = output_path.resolve()
                report = self.guardian.audit_layout(str(abs_path))

                if report["approved"]:
                    logger.info(f"✅ Guardian APPROVED: {report['reason']}")

                    # Log successful build to training dataset
                    current_strategy = fixes_applied[-1].split(" ")[0] if fixes_applied else "NONE"
                    self.miner.log_build_event(
                        theme=theme,
                        content=current_content,
                        strategy=current_strategy,
                        guardian_verdict=True,
                        guardian_reason="",
                        css_overrides=current_style_overrides if current_style_overrides else None,
                    )

                    return BuildResult(
                        status=BuildStatus.SUCCESS,
                        output_path=output_path,
                        theme=theme,
                        attempts=attempt,
                        guardian_report=report,
                        fixes_applied=fixes_applied,
                    )
                else:
                    logger.warning(f"❌ Guardian REJECTED: {report['reason']}")

                    # Log failed build to training dataset (negative sample)
                    current_strategy = fixes_applied[-1].split(" ")[0] if fixes_applied else "NONE"
                    self.miner.log_build_event(
                        theme=theme,
                        content=current_content,
                        strategy=current_strategy,
                        guardian_verdict=False,
                        guardian_reason=report["reason"],
                        css_overrides=current_style_overrides if current_style_overrides else None,
                    )

                    # Check if we can retry
                    if attempt < max_retries:
                        # Apply progressive healing strategy
                        # v0.5.0: Pass context to Neural Healer if enabled
                        if self.use_neural_healer:
                            # Extract error type from Guardian report
                            error_type = "overflow"  # Default
                            if "overflow" in report.get("reason", "").lower():
                                error_type = "overflow"
                            elif "text" in report.get("reason", "").lower():
                                error_type = "text_too_long"
                            elif "layout" in report.get("reason", "").lower():
                                error_type = "layout_shift"

                            healing_context = {"theme": theme, "error_type": error_type}

                            healing_result = self.healer.heal_layout(
                                guardian_report=report,
                                content=current_content,
                                attempt=attempt,
                                context=healing_context,
                            )
                        else:
                            # SmartHealer (heuristic)
                            healing_result = self.healer.heal_layout(
                                guardian_report=report, content=current_content, attempt=attempt
                            )

                        healer_type = "🧠 Neural" if self.use_neural_healer else "🚑 Smart"
                        logger.info(
                            f"{healer_type} Applied strategy: {healing_result.strategy.value}"
                        )
                        logger.info(f"   {healing_result.description}")

                        # Update state based on healing result
                        if healing_result.content_modified:
                            # Nuclear option: content was modified
                            current_content = healing_result.modified_content
                            logger.warning("⚠️  Content modified (nuclear option)")
                        else:
                            # CSS strategy: update style overrides
                            current_style_overrides.update(healing_result.style_overrides)

                        fixes_applied.append(f"{healing_result.strategy.value} (attempt {attempt})")
                        logger.info(
                            f"   → Retrying build with {healing_result.strategy.value}...\n"
                        )
                    else:
                        # Max retries reached
                        logger.error("💀 Max retries reached. Build failed.")

                        # Rename broken file
                        broken_path = output_path.parent / f"BROKEN_{output_filename}"
                        os.rename(str(output_path), str(broken_path))
                        logger.info(f"   → Broken layout saved as: {broken_path}")

                        return BuildResult(
                            status=BuildStatus.REJECTED,
                            output_path=broken_path,
                            theme=theme,
                            attempts=attempt,
                            guardian_report=report,
                            fixes_applied=fixes_applied,
                            errors=[f"Guardian rejected after {attempt} attempts"],
                        )

            except Exception as e:
                logger.error(f"Guardian QA failed: {e}")
                return BuildResult(
                    status=BuildStatus.FAILED,
                    output_path=output_path,
                    theme=theme,
                    attempts=attempt,
                    fixes_applied=fixes_applied,
                    errors=[f"Guardian error: {e}"],
                )

        # Should not reach here
        return BuildResult(
            status=BuildStatus.FAILED,
            theme=theme,
            attempts=attempt,
            errors=["Unknown error in build loop"],
        )

    def build_with_llm(
        self,
        raw_text_path: str,
        theme: str,
        output_filename: str,
        enable_guardian: bool = False,
    ) -> BuildResult:
        """
        Build page with LLM content generation.

        Args:
            raw_text_path: Path to raw portfolio data
            theme: Theme name
            output_filename: Output HTML filename
            enable_guardian: Enable Guardian QA

        Returns:
            BuildResult with status and metadata
        """
        logger.info(f"🧠 Generating LLM content from: {raw_text_path}")

        try:
            # Initialize ContentEngine
            engine = ContentEngine(
                lm_studio_url=self.config.lm_studio_url, timeout=self.config.llm_timeout
            )

            # Generate content
            content = engine.generate_content_with_fallback(
                raw_text_path=raw_text_path,
                theme=theme,
                fallback_path=str(self.config.data_dir / "input_content.json"),
            )

            # Build with self-healing
            return self.build_with_self_healing(
                content=content,
                theme=theme,
                output_filename=output_filename,
                enable_guardian=enable_guardian,
            )

        except Exception as e:
            logger.error(f"LLM build failed: {e}")
            return BuildResult(
                status=BuildStatus.FAILED,
                theme=theme,
                attempts=0,
                errors=[f"LLM generation failed: {e}"],
            )
