"""
Caching layer for parsed entities, file trees, and statistics.
Uses a simple file-based cache with TTL (time-to-live) support.
"""
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Optional, Any


class CacheManager:
    """Manages caching of repository analysis results."""
    
    def __init__(self, cache_dir: str = ".cache/analysis", ttl_seconds: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time-to-live for cache entries (default: 1 hour)
        """
        self.cache_dir = Path(__file__).resolve().parent.parent / cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
    
    def _get_cache_key(self, repo_url: str, **kwargs) -> str:
        """
        Generate a unique cache key based on repo URL and parameters.
        
        Args:
            repo_url: Repository URL
            **kwargs: Additional parameters that affect the result
        
        Returns:
            SHA256 hash as cache key
        """
        # Create a deterministic string from all parameters
        params = {
            "repo_url": repo_url,
            **kwargs
        }
        # Sort keys for deterministic hashing
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(param_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str, cache_type: str) -> Path:
        """Get the file path for a cache entry."""
        return self.cache_dir / f"{cache_type}_{cache_key}.json"
    
    def _is_valid(self, cache_path: Path) -> bool:
        """Check if cache entry exists and is not expired."""
        if not cache_path.exists():
            return False
        
        # Check TTL
        mtime = cache_path.stat().st_mtime
        age = time.time() - mtime
        return age < self.ttl_seconds
    
    def get(self, cache_type: str, repo_url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data.
        
        Args:
            cache_type: Type of cache (e.g., 'file_tree', 'entities', 'stats')
            repo_url: Repository URL
            **kwargs: Additional parameters used for cache key
        
        Returns:
            Cached data or None if not found/expired
        """
        cache_key = self._get_cache_key(repo_url, **kwargs)
        cache_path = self._get_cache_path(cache_key, cache_type)
        
        if not self._is_valid(cache_path):
            return None
        
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            # If cache is corrupted, treat as miss
            return None
    
    def set(self, cache_type: str, repo_url: str, data: Dict[str, Any], **kwargs) -> None:
        """
        Store data in cache.
        
        Args:
            cache_type: Type of cache (e.g., 'file_tree', 'entities', 'stats')
            repo_url: Repository URL
            data: Data to cache
            **kwargs: Additional parameters used for cache key
        """
        cache_key = self._get_cache_key(repo_url, **kwargs)
        cache_path = self._get_cache_path(cache_key, cache_type)
        
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            # Silently fail on cache write errors
            pass
    
    def invalidate(self, cache_type: str, repo_url: str, **kwargs) -> None:
        """
        Invalidate a specific cache entry.
        
        Args:
            cache_type: Type of cache
            repo_url: Repository URL
            **kwargs: Additional parameters used for cache key
        """
        cache_key = self._get_cache_key(repo_url, **kwargs)
        cache_path = self._get_cache_path(cache_key, cache_type)
        
        if cache_path.exists():
            try:
                cache_path.unlink()
            except Exception:
                pass
    
    def clear_all(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception:
                pass
        return count
    
    def clear_expired(self) -> int:
        """
        Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if not self._is_valid(cache_file):
                try:
                    cache_file.unlink()
                    count += 1
                except Exception:
                    pass
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total = 0
        valid = 0
        expired = 0
        total_size = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            total += 1
            total_size += cache_file.stat().st_size
            if self._is_valid(cache_file):
                valid += 1
            else:
                expired += 1
        
        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": expired,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }


# Global cache instance with 1 hour TTL
_cache = CacheManager(ttl_seconds=3600)


def get_cache() -> CacheManager:
    """Get the global cache instance."""
    return _cache

