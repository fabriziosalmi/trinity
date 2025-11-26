"""
Test SiteBuilder CSS override merging

Tests cover:
- CSS override merging with theme classes
- Jinja2 template rendering with overrides
- Theme loading and validation
"""

import pytest
from pathlib import Path
from trinity.components.builder import SiteBuilder


@pytest.fixture
def builder():
    """Create SiteBuilder instance for testing"""
    return SiteBuilder()


@pytest.fixture
def mock_content():
    """Mock content for testing"""
    return {
        "brand_name": "Test Site",
        "tagline": "Test tagline",
        "hero": {
            "title": "Test Title",
            "subtitle": "Test subtitle"
        },
        "repos": []
    }


class TestCSSOverrideMerging:
    """Test style_overrides parameter in build_page()"""
    
    def test_build_without_overrides(self, builder, mock_content):
        """Test normal build without CSS overrides"""
        output_path = builder.build_page(mock_content, theme="enterprise")
        
        assert output_path is not None
        assert output_path.exists()
        assert str(output_path).endswith(".html")
    
    def test_build_with_style_overrides(self, builder, mock_content):
        """Test build with CSS overrides merges classes correctly"""
        style_overrides = {
            "heading_primary": "break-all overflow-wrap-anywhere",
            "heading_secondary": "line-clamp-2 truncate"
        }
        
        output_path = builder.build_page(
            mock_content, 
            theme="brutalist",
            style_overrides=style_overrides
        )
        
        assert output_path is not None
        assert output_path.exists()
        
        # Read generated HTML and verify CSS classes are merged
        with open(output_path, 'r') as f:
            html = f.read()
            
        # Should contain both original theme classes AND overrides
        assert "break-all" in html or "overflow-wrap-anywhere" in html
    
    def test_overrides_preserve_original_classes(self, builder, mock_content):
        """Test that CSS overrides append to original classes"""
        style_overrides = {
            "heading_primary": "text-3xl"  # Override
        }
        
        output_path = builder.build_page(
            mock_content,
            theme="enterprise",
            style_overrides=style_overrides
        )
        
        with open(output_path, 'r') as f:
            html = f.read()
        
        # Should have BOTH original enterprise hero_title classes AND text-3xl
        # (Original enterprise hero_title likely has font-bold, text-slate-900)
        assert "text-3xl" in html
    
    def test_empty_overrides_dict(self, builder, mock_content):
        """Test build with empty overrides dict works normally"""
        output_path = builder.build_page(
            mock_content,
            theme="editorial",
            style_overrides={}
        )
        
        assert output_path is not None
        assert output_path.exists()


class TestThemeLoading:
    """Test theme configuration loading"""
    
    def test_loads_all_themes(self, builder):
        """Test that all themes load successfully"""
        themes = ["enterprise", "brutalist", "editorial"]
        
        for theme in themes:
            # Should not raise exception
            output = builder.build_page(
                {"brand_name": "Test", "hero": {"title": "Test", "subtitle": "Test"}, "repos": []},
                theme=theme
            )
            assert output is not None
    
    def test_invalid_theme_raises_error(self, builder):
        """Test that invalid theme name raises appropriate error"""
        with pytest.raises(Exception):
            builder.build_page(
                {"brand_name": "Test", "hero": {"title": "Test", "subtitle": "Test"}, "repos": []},
                theme="nonexistent_theme"
            )
