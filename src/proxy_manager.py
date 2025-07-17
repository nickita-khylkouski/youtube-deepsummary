#!/usr/bin/env python3
"""
Proxy Manager for YouTube Deep Summary

Handles proxy rotation and configuration for transcript extraction using
Webshare proxy service with automatic fallback and retry mechanisms.
"""

import os
import time
import random
from typing import Dict, Optional, Tuple
from src.config import Config


class ProxyManager:
    """Manages proxy rotation and configuration"""
    
    def __init__(self, max_proxies: int = 9):
        """
        Initialize the proxy manager
        
        Args:
            max_proxies: Maximum number of proxies to rotate through (1-9)
        """
        self.max_proxies = max_proxies
        self.current_proxy = 1
        self.failed_proxies = set()
        self.last_rotation_time = time.time()
        self.rotation_interval = 60  # Rotate every 60 seconds minimum
        
    def get_current_proxy_config(self) -> Optional[Dict[str, str]]:
        """
        Get current proxy configuration for requests
        
        Returns:
            Dictionary with proxy configuration or None if no proxy available
        """
        if not Config.is_webshare_proxy_configured():
            print("🔴 No Webshare proxy configured, falling back to legacy proxy")
            return Config.get_proxy_config()
        
        # Get current proxy URL
        proxy_url = Config.get_webshare_proxy_url(self.current_proxy)
        if proxy_url:
            print(f"🌐 Using proxy: {Config.PROXY_USERNAME}-{self.current_proxy}@{Config.PROXY_HOST}:{Config.PROXY_PORT}")
            return {
                'http': proxy_url,
                'https': proxy_url
            }
        
        return None
    
    def get_current_proxy_for_ytdlp(self) -> Optional[str]:
        """
        Get current proxy configuration for yt-dlp
        
        Returns:
            Proxy URL string for yt-dlp or None if no proxy available
        """
        if not Config.is_webshare_proxy_configured():
            if Config.YOUTUBE_PROXY:
                return f"http://{Config.YOUTUBE_PROXY}"
            return None
        
        proxy_url = Config.get_webshare_proxy_url(self.current_proxy)
        if proxy_url:
            print(f"🌐 Using yt-dlp proxy: {Config.PROXY_USERNAME}-{self.current_proxy}@{Config.PROXY_HOST}:{Config.PROXY_PORT}")
            return proxy_url
        
        return None
    
    def mark_proxy_failed(self, proxy_number: Optional[int] = None):
        """
        Mark a proxy as failed and rotate to next one
        
        Args:
            proxy_number: Specific proxy number to mark as failed, or current if None
        """
        if proxy_number is None:
            proxy_number = self.current_proxy
        
        self.failed_proxies.add(proxy_number)
        print(f"🔴 Marked proxy {Config.PROXY_USERNAME}-{proxy_number} as failed")
        
        # Rotate to next proxy
        self.rotate_proxy()
    
    def rotate_proxy(self) -> bool:
        """
        Rotate to the next available proxy
        
        Returns:
            True if successfully rotated, False if no proxies available
        """
        if not Config.is_webshare_proxy_configured():
            print("🔴 No Webshare proxy configured for rotation")
            return False
        
        # Find next available proxy
        attempts = 0
        while attempts < self.max_proxies:
            self.current_proxy = (self.current_proxy % self.max_proxies) + 1
            
            if self.current_proxy not in self.failed_proxies:
                print(f"🔄 Rotated to proxy: {Config.PROXY_USERNAME}-{self.current_proxy}")
                self.last_rotation_time = time.time()
                return True
            
            attempts += 1
        
        # All proxies failed, reset and try again
        print("⚠️ All proxies failed, resetting failed proxy list")
        self.failed_proxies.clear()
        self.current_proxy = random.randint(1, self.max_proxies)
        print(f"🔄 Reset to random proxy: {Config.PROXY_USERNAME}-{self.current_proxy}")
        self.last_rotation_time = time.time()
        return True
    
    def should_rotate(self) -> bool:
        """
        Check if it's time to rotate proxies based on time interval
        
        Returns:
            True if rotation is recommended
        """
        return (time.time() - self.last_rotation_time) > self.rotation_interval
    
    def get_proxy_info(self) -> Dict[str, any]:
        """
        Get information about current proxy status
        
        Returns:
            Dictionary with proxy status information
        """
        return {
            'current_proxy': self.current_proxy,
            'failed_proxies': list(self.failed_proxies),
            'max_proxies': self.max_proxies,
            'webshare_configured': Config.is_webshare_proxy_configured(),
            'legacy_proxy': Config.YOUTUBE_PROXY,
            'rotation_interval': self.rotation_interval,
            'last_rotation': self.last_rotation_time
        }
    
    def test_proxy(self, proxy_number: Optional[int] = None) -> Tuple[bool, str]:
        """
        Test if a specific proxy is working
        
        Args:
            proxy_number: Proxy number to test, or current if None
            
        Returns:
            Tuple of (success, message)
        """
        if proxy_number is None:
            proxy_number = self.current_proxy
        
        if not Config.is_webshare_proxy_configured():
            return False, "No Webshare proxy configured"
        
        try:
            import requests
            proxy_url = Config.get_webshare_proxy_url(proxy_number)
            if not proxy_url:
                return False, "Failed to generate proxy URL"
            
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # Test with a simple request
            response = requests.get(
                "https://ipv4.webshare.io/", 
                proxies=proxies, 
                timeout=10
            )
            
            if response.status_code == 200:
                return True, f"Proxy {Config.PROXY_USERNAME}-{proxy_number} is working"
            else:
                return False, f"Proxy returned status code {response.status_code}"
                
        except Exception as e:
            return False, f"Proxy test failed: {str(e)}"


# Global proxy manager instance
proxy_manager = ProxyManager()


def get_proxy_config() -> Optional[Dict[str, str]]:
    """
    Convenience function to get current proxy configuration
    
    Returns:
        Dictionary with proxy configuration or None
    """
    return proxy_manager.get_current_proxy_config()


def get_ytdlp_proxy() -> Optional[str]:
    """
    Convenience function to get proxy for yt-dlp
    
    Returns:
        Proxy URL string or None
    """
    return proxy_manager.get_current_proxy_for_ytdlp()


def rotate_proxy() -> bool:
    """
    Convenience function to rotate proxy
    
    Returns:
        True if rotation successful
    """
    return proxy_manager.rotate_proxy()


def mark_proxy_failed():
    """
    Convenience function to mark current proxy as failed
    """
    proxy_manager.mark_proxy_failed()