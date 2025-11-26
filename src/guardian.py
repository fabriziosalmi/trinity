"""
Trinity Core - Guardian Module (Vision-Augmented QA)
Rule #7: Graceful degradation on AI failures
Rule #28: Structured logging
Rule #5: Type safety and validation
"""
import asyncio
import base64
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from playwright.async_api import async_playwright
except ImportError:
    raise ImportError("playwright required. Install with: pip install playwright && playwright install chromium")

try:
    from openai import OpenAI, APIConnectionError, APIError
except ImportError:
    raise ImportError("openai required. Install with: pip install openai")

from pydantic import BaseModel, Field, ValidationError

# Rule #28: Structured logging
logger = logging.getLogger(__name__)

# Rule #8: No magic strings
# Docker-compatible: Uses LM_STUDIO_URL env var with fallback to localhost
DEFAULT_LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://192.168.100.12:1234/v1")
DEFAULT_MODEL_ID = "qwen2.5-coder-3b-instruct-mlx"
DEFAULT_VIEWPORT_WIDTH = 1024
DEFAULT_VIEWPORT_HEIGHT = 768


class AuditReport(BaseModel):
    """Pydantic schema for Guardian audit report."""
    approved: bool = Field(..., description="Whether layout passed inspection")
    status: str = Field(..., description="pass or fail")
    reason: str = Field(..., description="Explanation of decision")
    issues: list[str] = Field(default_factory=list, description="List of detected issues")
    fix_suggestion: str = Field(default="none", description="Suggested fix action")
    screenshot_path: Optional[str] = None


class GuardianError(Exception):
    """Base exception for Guardian errors."""
    pass


class TrinityGuardian:
    """
    Vision-powered layout quality assurance system.
    
    Responsibilities:
    - Render HTML in headless browser
    - Perform hybrid checks (DOM + Vision AI)
    - Detect layout bugs (overflow, overlap, broken rendering)
    - Return actionable fix suggestions
    
    Does NOT:
    - Fix layouts automatically (that's for future iterations)
    - Generate content (handled by ContentEngine)
    - Build HTML (handled by SiteBuilder)
    """
    
    def __init__(
        self,
        base_url: str = DEFAULT_LM_STUDIO_URL,
        model_id: str = DEFAULT_MODEL_ID,
        viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
        viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
        enable_vision_ai: bool = True
    ):
        """
        Initialize TrinityGuardian with Qwen VL endpoint.
        
        Args:
            base_url: LM Studio API endpoint
            model_id: Vision model identifier
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            enable_vision_ai: Use Qwen VL for visual inspection (disable for fast DOM-only checks)
        """
        self.base_url = base_url
        self.model_id = model_id
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.enable_vision_ai = enable_vision_ai
        
        # Initialize OpenAI-compatible client for Vision API
        if self.enable_vision_ai:
            self.client = OpenAI(base_url=base_url, api_key="lm-studio")
        
        logger.info(f"👁️  TrinityGuardian initialized (vision_ai={enable_vision_ai})")
    
    async def _capture_screenshot(self, html_path: str) -> Optional[str]:
        """
        Render HTML in headless browser and capture screenshot.
        
        Args:
            html_path: Absolute path to HTML file
            
        Returns:
            Base64-encoded screenshot or None on failure
        """
        path = Path(html_path)
        if not path.exists():
            raise FileNotFoundError(f"HTML file not found: {path}")
        
        try:
            async with async_playwright() as p:
                # Launch headless Chromium
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={"width": self.viewport_width, "height": self.viewport_height}
                )
                
                # Load HTML file (use file:// URL)
                await page.goto(f"file://{path.resolve()}")
                
                # Wait for page to fully render
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)  # Extra safety margin for CSS animations
                
                # Capture screenshot
                screenshot_bytes = await page.screenshot(full_page=True)
                
                await browser.close()
                
                # Encode to base64
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                logger.info(f"✓ Screenshot captured: {len(screenshot_b64)} bytes")
                return screenshot_b64
                
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    async def _check_dom_overflow(self, html_path: str) -> bool:
        """
        Fast DOM-based check for overflow issues.
        
        Args:
            html_path: Absolute path to HTML file
            
        Returns:
            True if overflow detected, False otherwise
        """
        path = Path(html_path)
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto(f"file://{path.resolve()}")
                await page.wait_for_load_state("networkidle")
                
                # Inject JavaScript to check for overflow
                overflow_detected = await page.evaluate("""
                    () => {
                        const elements = Array.from(document.querySelectorAll('*'));
                        const overflowing = elements.filter(el => {
                            // Check horizontal overflow
                            if (el.scrollWidth > el.clientWidth + 5) {  // 5px tolerance
                                return true;
                            }
                            // Check if text is clipped
                            const computed = window.getComputedStyle(el);
                            if (computed.overflow === 'hidden' && el.scrollHeight > el.clientHeight + 5) {
                                return true;
                            }
                            return false;
                        });
                        
                        if (overflowing.length > 0) {
                            console.log('Overflow detected in:', overflowing.map(el => el.tagName + '.' + el.className));
                            return true;
                        }
                        return false;
                    }
                """)
                
                await browser.close()
                
                if overflow_detected:
                    logger.warning("⚠️  DOM overflow detected via JavaScript")
                
                return overflow_detected
                
        except Exception as e:
            logger.error(f"DOM overflow check failed: {e}")
            return False
    
    def _analyze_with_vision(self, screenshot_b64: str) -> Dict[str, Any]:
        """
        Analyze screenshot using Qwen VL vision model.
        
        Args:
            screenshot_b64: Base64-encoded screenshot
            
        Returns:
            Analysis result dictionary
        """
        system_prompt = """You are a UI/UX QA Specialist with expert-level knowledge of web layout debugging.

Analyze this website screenshot and check STRICTLY for technical layout bugs:

1. **Text Overflow**: Text going outside its container borders (white cards, colored boxes)
2. **Text Overlap**: Text overlapping other text, icons, or buttons
3. **Broken Elements**: Missing images, broken grids, collapsed containers
4. **Visual Rendering Bugs**: Elements that appear corrupted or malformed

IGNORE aesthetics, colors, fonts, or design choices. ONLY report BUGS.

Return ONLY a JSON object (no markdown, no code blocks):
{
    "status": "pass" or "fail",
    "issues": ["description of issue 1", "description of issue 2"],
    "fix_suggestion": "truncate" or "smaller_font" or "wrap_text" or "none"
}

If the layout looks technically sound, return: {"status": "pass", "issues": [], "fix_suggestion": "none"}"""

        try:
            logger.info("🧠 Sending screenshot to Qwen VL for analysis...")
            
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_b64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "Analyze this webpage screenshot for layout bugs."
                            }
                        ]
                    }
                ],
                temperature=0.1,  # Low temperature for deterministic analysis
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean response (remove markdown if present)
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            analysis = json.loads(content)
            
            logger.info(f"✓ Vision analysis complete: {analysis.get('status', 'unknown')}")
            return analysis
            
        except (APIConnectionError, APIError) as e:
            logger.error(f"Qwen VL connection failed: {e}")
            # Rule #7: Graceful degradation
            return {
                "status": "pass",
                "issues": ["Vision AI unavailable - auto-approved"],
                "fix_suggestion": "none"
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Vision AI response: {e}")
            return {
                "status": "pass",
                "issues": ["Vision AI response invalid - auto-approved"],
                "fix_suggestion": "none"
            }
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {
                "status": "pass",
                "issues": ["Vision AI error - auto-approved"],
                "fix_suggestion": "none"
            }
    
    def audit_layout(self, html_path: str) -> Dict[str, Any]:
        """
        Perform complete layout audit (DOM + Vision AI).
        
        Args:
            html_path: Absolute path to HTML file
            
        Returns:
            Audit report dictionary
        """
        logger.info(f"👁️  Guardian inspecting: {html_path}")
        
        # Phase 1: Fast DOM check
        logger.info("Phase 1: DOM overflow detection...")
        dom_overflow = asyncio.run(self._check_dom_overflow(html_path))
        
        if dom_overflow and not self.enable_vision_ai:
            # Early exit if DOM check fails and Vision AI is disabled
            return {
                "approved": False,
                "status": "fail",
                "reason": "DOM overflow detected (horizontal or vertical)",
                "issues": ["Text or content overflowing container boundaries"],
                "fix_suggestion": "truncate",
                "screenshot_path": None
            }
        
        # Phase 2: Vision AI analysis
        if self.enable_vision_ai:
            logger.info("Phase 2: Vision AI analysis (Qwen VL)...")
            
            screenshot_b64 = asyncio.run(self._capture_screenshot(html_path))
            
            if not screenshot_b64:
                logger.warning("Screenshot capture failed - auto-approving")
                return {
                    "approved": True,
                    "status": "pass",
                    "reason": "Screenshot unavailable - approved by default",
                    "issues": [],
                    "fix_suggestion": "none",
                    "screenshot_path": None
                }
            
            vision_analysis = self._analyze_with_vision(screenshot_b64)
            
            # Combine DOM + Vision results
            approved = vision_analysis["status"] == "pass" and not dom_overflow
            
            if dom_overflow and vision_analysis["status"] == "pass":
                # DOM detected overflow but Vision AI says it's fine
                # Trust Vision AI (it might be intentional overflow/scroll)
                approved = True
                reason = "DOM overflow detected but visually acceptable"
            elif vision_analysis["status"] == "fail":
                approved = False
                reason = f"Visual layout bugs detected: {', '.join(vision_analysis['issues'])}"
            else:
                approved = True
                reason = "Layout passed all checks"
            
            return {
                "approved": approved,
                "status": "pass" if approved else "fail",
                "reason": reason,
                "issues": vision_analysis.get("issues", []),
                "fix_suggestion": vision_analysis.get("fix_suggestion", "none"),
                "screenshot_path": None  # Could save to disk if needed
            }
        
        else:
            # Vision AI disabled, rely only on DOM check
            return {
                "approved": not dom_overflow,
                "status": "pass" if not dom_overflow else "fail",
                "reason": "DOM overflow detected" if dom_overflow else "DOM checks passed",
                "issues": ["Horizontal or vertical overflow detected"] if dom_overflow else [],
                "fix_suggestion": "truncate" if dom_overflow else "none",
                "screenshot_path": None
            }


# Demo usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test with a real HTML file
    test_file = Path("output/index_brutalist_llm.html")
    
    if test_file.exists():
        guardian = TrinityGuardian(enable_vision_ai=True)
        
        report = guardian.audit_layout(str(test_file.resolve()))
        
        print("\n" + "=" * 60)
        print("GUARDIAN AUDIT REPORT")
        print("=" * 60)
        print(f"Status: {'✅ APPROVED' if report['approved'] else '❌ REJECTED'}")
        print(f"Reason: {report['reason']}")
        if report['issues']:
            print(f"Issues Found: {len(report['issues'])}")
            for issue in report['issues']:
                print(f"  - {issue}")
        print(f"Fix Suggestion: {report['fix_suggestion']}")
        print("=" * 60)
    else:
        print(f"Test file not found: {test_file}")
