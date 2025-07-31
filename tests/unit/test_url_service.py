"""
Simple tests for UrlService that work without Flask context.
"""

import pytest
from app.services import UrlService


@pytest.mark.unit
class TestUrlService:
    """Test UrlService functionality."""
    
    def test_process_firebase_to_cdn_url_firebase_url(self):
        """Test converting Firebase URLs to CDN."""
        firebase_url = "https://firebasestorage.googleapis.com/v0/b/project.appspot.com/o/cards%2Fimage.png?alt=media"
        
        result = UrlService.process_firebase_to_cdn_url(firebase_url)
        
        assert result == "https://cdn.pvpocket.xyz/cards/image.png"
    
    def test_process_firebase_to_cdn_url_already_cdn(self):
        """Test URLs already on CDN are unchanged."""
        cdn_url = "https://cdn.pvpocket.xyz/cards/image.png"
        
        result = UrlService.process_firebase_to_cdn_url(cdn_url)
        
        assert result == cdn_url
    
    def test_process_firebase_to_cdn_url_fallback(self):
        """Test fallback behavior for edge cases."""
        # Test with empty string
        result = UrlService.process_firebase_to_cdn_url("")
        assert result == ""
        
        # Test with simple path
        result = UrlService.process_firebase_to_cdn_url("simple-path")
        # Should get CDN prefix added
        assert "cdn.pvpocket.xyz" in result