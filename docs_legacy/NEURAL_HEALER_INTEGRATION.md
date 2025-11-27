"""
Integration Example: Neural Healer in TrinityEngine

This snippet shows how to integrate the Neural Healer into the self-healing loop.
To be merged into src/trinity/engine.py in production.
"""

from trinity.components.neural_healer import NeuralHealer


# Add to TrinityEngine.__init__()
def __init__(self, config: Optional[TrinityConfig] = None, use_neural_healer: bool = True):
    """
    Initialize Trinity Engine.
    
    Args:
        config: Trinity configuration
        use_neural_healer: Use generative LSTM healer (v0.5.0) instead of heuristic
    """
    self.config = config or TrinityConfig()
    self.builder = SiteBuilder(templates_dir=self.config.templates_path)
    self.guardian = TrinityGuardian(vision_enabled=self.config.vision_ai_enabled)
    
    # Choose healer: Neural (v0.5.0) or Heuristic (v0.4.0)
    if use_neural_healer:
        try:
            self.healer = NeuralHealer.from_default_paths(fallback_to_heuristic=True)
            logger.info("🧠 Neural Healer initialized (generative mode)")
        except Exception as e:
            logger.warning(f"Neural Healer failed, using heuristic: {e}")
            from trinity.components.healer import SmartHealer
            self.healer = SmartHealer()
    else:
        from trinity.components.healer import SmartHealer
        self.healer = SmartHealer()
        logger.info("🔧 Heuristic Healer initialized (v0.4.0 mode)")
    
    self.miner = TrinityMiner(dataset_path=self.config.project_root / "data" / "training_dataset.csv")
    
    # Optionally load predictive model (v0.3.0)
    self.predictor = None
    if self.config.enable_ml_prediction:
        predictor_path = self.config.project_root / "models" / "layout_risk_predictor.pkl"
        if predictor_path.exists():
            self.predictor = LayoutRiskPredictor.load(predictor_path)


# Modified self-healing loop (relevant section)
def build_with_self_healing(
    self,
    content: Dict,
    theme: str,
    output_filename: str,
    enable_guardian: bool = None,
    enable_prediction: bool = None,
) -> BuildResult:
    """
    Build with self-healing loop.
    
    Neural Healer receives context about theme and error type
    for smarter fix generation.
    """
    # ... existing code ...
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"🔄 Build Attempt {attempt}/{max_retries}")
        
        try:
            # Build page
            output_path = self.builder.build_page(
                content=active_content,
                theme=theme,
                output_filename=output_filename,
                style_overrides=accumulated_overrides,
            )
            
            # Guardian audit
            if enable_guardian:
                audit_result = self.guardian.audit_layout(output_path)
                
                if audit_result["approved"]:
                    logger.info("✅ Guardian approved layout")
                    break
                
                # Guardian rejected - generate fix
                logger.warning(f"❌ Guardian rejected: {audit_result['reason']}")
                
                # Extract error context for Neural Healer
                error_context = {
                    "theme": theme,
                    "error_type": self._classify_error(audit_result["issues"]),
                    "content_length": len(str(content.get("hero", {}).get("title", ""))),
                }
                
                # Generate fix (Neural or Heuristic)
                healing_result = self.healer.heal_layout(
                    guardian_report=audit_result,
                    content=active_content,
                    attempt=attempt,
                    context=error_context  # NEW: Pass context to Neural Healer
                )
                
                # Apply fix
                self._apply_healing(healing_result, accumulated_overrides, active_content)
                fixes_applied.append(healing_result.strategy.value)
        
        except Exception as e:
            logger.error(f"Build attempt {attempt} failed: {e}")
            errors.append(str(e))
    
    # ... rest of method ...


def _classify_error(self, issues: List[str]) -> str:
    """
    Classify Guardian issues into error types for Neural Healer.
    
    Maps Guardian's verbose issue descriptions to standardized error types
    that match the training data categories.
    
    Args:
        issues: List of issue strings from Guardian
        
    Returns:
        Error type: "overflow", "text_too_long", "layout_shift", or "unknown"
    """
    issues_text = " ".join(issues).lower()
    
    if any(word in issues_text for word in ["overflow", "horizontal", "scroll"]):
        return "overflow"
    elif any(word in issues_text for word in ["text", "long", "title"]):
        return "text_too_long"
    elif any(word in issues_text for word in ["shift", "layout", "position"]):
        return "layout_shift"
    else:
        return "unknown"


# Example usage in CLI
def build_command(
    theme: str = "enterprise",
    input_file: Path = None,
    output: str = "index.html",
    guardian: bool = False,
    neural: bool = True,  # NEW: Enable neural healer
):
    """
    Build command with neural healer option.
    """
    engine = TrinityEngine(use_neural_healer=neural)
    
    # Load content
    with open(input_file) as f:
        content = json.load(f)
    
    # Build with self-healing
    result = engine.build_with_self_healing(
        content=content,
        theme=theme,
        output_filename=output,
        enable_guardian=guardian,
    )
    
    print(f"Build status: {result.status}")
    if neural:
        print("🧠 Neural Healer was used for fix generation")


# Backward compatibility check
if __name__ == "__main__":
    # Test fallback behavior
    print("Testing Neural Healer integration...\n")
    
    # Case 1: Neural model available
    try:
        engine_neural = TrinityEngine(use_neural_healer=True)
        print("✅ Neural mode: OK")
    except Exception as e:
        print(f"❌ Neural mode failed: {e}")
    
    # Case 2: Heuristic fallback
    engine_heuristic = TrinityEngine(use_neural_healer=False)
    print("✅ Heuristic mode: OK")
    
    # Case 3: Heal with context
    from trinity.components.neural_healer import NeuralHealer
    healer = NeuralHealer.from_default_paths()
    
    result = healer.heal_layout(
        guardian_report={"approved": False, "reason": "overflow"},
        content={"hero": {"title": "A" * 100}},
        attempt=1,
        context={"theme": "brutalist", "error_type": "overflow"}
    )
    
    print(f"\n🧠 Generated fix: {result.style_overrides}")
