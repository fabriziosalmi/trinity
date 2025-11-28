"""
Trinity - AI-Powered Static Site Generator
with Self-Healing Layout QA and Neural-Symbolic Learning

A deterministic static site builder that combines:
- Semantic HTML skeletons (Jinja2 templates)
- LLM-generated content (OpenAI/LM Studio)
- Vision-based QA (Guardian with Playwright)
- Self-healing layout fixes (automatic retry with CSS/content fixes)
- ML-powered predictive models (Risk Assessor, Style Generator)
"""

__version__ = "0.8.1"
__author__ = "Trinity Team"

from trinity.components.brain import ContentEngine, ContentEngineError
from trinity.components.builder import SiteBuilder, SiteBuilderError
from trinity.components.dataminer import TrinityMiner
from trinity.components.guardian import GuardianError, TrinityGuardian
from trinity.config import TrinityConfig
from trinity.engine import BuildResult, TrinityEngine

__all__ = [
    "TrinityEngine",
    "SiteBuilder",
    "ContentEngine",
    "TrinityGuardian",
    "TrinityMiner",
    "TrinityConfig",
    "BuildResult",
    "SiteBuilderError",
    "ContentEngineError",
    "GuardianError",
]
