"""
Trinity Engine - Main Orchestrator

Coordinates the build → audit → heal → retry cycle.
Implements the Self-Healing Loop with intelligent fix strategies.
"""
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import os

from trinity.config import TrinityConfig
from trinity.components.builder import SiteBuilder
from trinity.components.brain import ContentEngine
from trinity.components.guardian import TrinityGuardian
from trinity.components.healer import SmartHealer, HealingResult, HealingStrategy
from trinity.components.dataminer import TrinityMiner
from trinity.components.predictor import LayoutRiskPredictor
from trinity.utils.validators import ContentValidator, ValidationError
from trinity.utils.logger import get_logger

logger = get_logger(__name__)


class BuildStatus(str, Enum):
    """Build result status."""
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    PARTIAL = "partial"


class BuildResult(BaseModel):
    """Structured build result."""
    
    status: BuildStatus
    output_path: Optional[Path] = None
    theme: str
    attempts: int = 0
    guardian_report: Optional[Dict[str, Any]] = None
    fixes_applied: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True


class TrinityEngine:
    """
    Main orchestrator for Trinity Core.
    
    Coordinates:
    - Content generation (Brain)
    - Site building (Builder)
    - Layout QA (Guardian)
    - Self-healing (Healer)
    """
    
    def __init__(self, config: Optional[TrinityConfig] = None):
        """
        Initialize Trinity Engine.
        
        Args:
            config: Trinity configuration (uses defaults if None)
        """
        self.config = config or TrinityConfig()
        
        # Initialize components
        self.builder = SiteBuilder(template_dir=str(self.config.templates_path))
        self.validator = ContentValidator()
        self.healer = SmartHealer(truncate_length=self.config.truncate_length)
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
                viewport_height=self.config.guardian_viewport_height
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
        logger.info(f"🔨 Starting build: {output_filename} (theme={theme}, guardian={enable_guardian})")
        
        # Validate content upfront
        try:
            self.validator.validate_content_schema(content)
        except ValidationError as e:
            logger.error(f"Content validation failed: {e}")
            return BuildResult(
                status=BuildStatus.FAILED,
                theme=theme,
                errors=[f"Content validation failed: {e}"]
            )
        
        # Self-Healing Loop
        max_retries = self.config.max_retries if enable_guardian else 1
        attempt = 0
        current_content = content
        current_style_overrides: Dict[str, str] = {}  # Track CSS overrides
        fixes_applied = []
        
        # 🔮 Phase 3: Pre-Cognition (predict risk before first render)
        if enable_guardian and self.config.predictive_enabled:
            risk_score, prediction_available = self.predictor.predict_risk(
                content=content,
                theme=theme,
                css_signature="NONE"
            )
            
            if prediction_available:
                recommendation = self.predictor.get_recommendation(risk_score)
                logger.info(f"🔮 Neural Predictor: {recommendation['reason']}")
                
                # Pre-emptive healing if high risk
                if recommendation["skip_none_strategy"]:
                    logger.warning(f"⚡ Activating pre-emptive healer (risk={risk_score:.0%})")
                    # Apply CSS_BREAK_WORD immediately (skip NONE attempt)
                    # Create a mock guardian report to trigger CSS_BREAK_WORD strategy
                    mock_report = {
                        "approved": False,
                        "status": "fail",
                        "reason": "ML predicted high risk",
                        "issues": ["Predicted layout overflow"],
                        "fix_suggestion": "break-word"
                    }
                    preemptive_fix = self.healer.heal_layout(
                        guardian_report=mock_report,
                        content=content,
                        attempt=1  # Force CSS_BREAK_WORD
                    )
                    if preemptive_fix.style_overrides:
                        current_style_overrides = preemptive_fix.style_overrides
                        fixes_applied.append("Pre-emptive CSS_BREAK_WORD (ML predicted failure)")
        
        while attempt < max_retries:
            attempt += 1
            logger.info(f"🔄 Build Attempt {attempt}/{max_retries}")
            
            # 1. Build page with current style overrides
            try:
                output_path = self.builder.build_page(
                    content=current_content,
                    theme=theme,
                    output_filename=output_filename,
                    style_overrides=current_style_overrides if current_style_overrides else None
                )
                logger.info(f"✓ Page built: {output_path}")
            except Exception as e:
                logger.error(f"Build failed: {e}")
                return BuildResult(
                    status=BuildStatus.FAILED,
                    theme=theme,
                    attempts=attempt,
                    errors=[f"Build error: {e}"]
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
                    css_overrides=current_style_overrides if current_style_overrides else None
                )
                
                return BuildResult(
                    status=BuildStatus.SUCCESS,
                    output_path=output_path,
                    theme=theme,
                    attempts=attempt
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
                        css_overrides=current_style_overrides if current_style_overrides else None
                    )
                    
                    return BuildResult(
                        status=BuildStatus.SUCCESS,
                        output_path=output_path,
                        theme=theme,
                        attempts=attempt,
                        guardian_report=report,
                        fixes_applied=fixes_applied
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
                        css_overrides=current_style_overrides if current_style_overrides else None
                    )
                    
                    # Check if we can retry
                    if attempt < max_retries:
                        # Apply progressive healing strategy
                        healing_result = self.healer.heal_layout(
                            guardian_report=report,
                            content=current_content,
                            attempt=attempt
                        )
                        
                        logger.info(f"🚑 Applied strategy: {healing_result.strategy.value}")
                        logger.info(f"   {healing_result.description}")
                        
                        # Update state based on healing result
                        if healing_result.content_modified:
                            # Nuclear option: content was modified
                            current_content = healing_result.modified_content
                            logger.warning("⚠️  Content modified (nuclear option)")
                        else:
                            # CSS strategy: update style overrides
                            current_style_overrides.update(healing_result.style_overrides)
                        
                        fixes_applied.append(
                            f"{healing_result.strategy.value} (attempt {attempt})"
                        )
                        logger.info(f"   → Retrying build with {healing_result.strategy.value}...\n")
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
                            errors=[f"Guardian rejected after {attempt} attempts"]
                        )
                        
            except Exception as e:
                logger.error(f"Guardian QA failed: {e}")
                return BuildResult(
                    status=BuildStatus.FAILED,
                    output_path=output_path,
                    theme=theme,
                    attempts=attempt,
                    fixes_applied=fixes_applied,
                    errors=[f"Guardian error: {e}"]
                )
        
        # Should not reach here
        return BuildResult(
            status=BuildStatus.FAILED,
            theme=theme,
            attempts=attempt,
            errors=["Unknown error in build loop"]
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
                lm_studio_url=self.config.lm_studio_url,
                timeout=self.config.llm_timeout
            )
            
            # Generate content
            content = engine.generate_content_with_fallback(
                raw_text_path=raw_text_path,
                theme=theme,
                fallback_path=str(self.config.data_dir / "input_content.json")
            )
            
            # Build with self-healing
            return self.build_with_self_healing(
                content=content,
                theme=theme,
                output_filename=output_filename,
                enable_guardian=enable_guardian
            )
            
        except Exception as e:
            logger.error(f"LLM build failed: {e}")
            return BuildResult(
                status=BuildStatus.FAILED,
                theme=theme,
                attempts=0,
                errors=[f"LLM generation failed: {e}"]
            )
