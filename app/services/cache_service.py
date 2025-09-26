"""
Caching service for API responses.
"""

import json
import hashlib
import logging
from typing import Optional, Any, Dict
import asyncio
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from ..models.intent import IntentResult
from config.settings import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching API responses."""
    
    def __init__(self):
        self.enabled = REDIS_AVAILABLE and settings.REDIS_URL is not None
        self.ttl = settings.CACHE_TTL
        self._redis: Optional[redis.Redis] = None
        self._local_cache: Dict[str, Dict[str, Any]] = {}
        self._local_cache_timestamps: Dict[str, datetime] = {}
        
    async def get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if not REDIS_AVAILABLE:
            return None
            
        if self._redis is None:
            try:
                if settings.REDIS_URL:
                    self._redis = redis.from_url(settings.REDIS_URL)
                else:
                    self._redis = redis.Redis(
                        host=settings.REDIS_HOST,
                        port=settings.REDIS_PORT,
                        db=settings.REDIS_DB,
                        password=settings.REDIS_PASSWORD,
                        decode_responses=True
                    )
                
                # Test connection
                await self._redis.ping()
                logger.info("Redis connection established")
                
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self._redis = None
                
        return self._redis
    
    def _generate_cache_key(self, user_input: str, context: Optional[str] = None) -> str:
        """Generate cache key for user input."""
        key_data = f"{user_input}:{context or ''}"
        return f"intent:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get(self, user_input: str, context: Optional[str] = None) -> Optional[IntentResult]:
        """Get cached result for user input."""
        cache_key = self._generate_cache_key(user_input, context)
        
        # Try Redis first
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    result = IntentResult(**data)
                    logger.debug(f"Cache hit (Redis): {cache_key}")
                    return result
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")
        
        # Fall back to local cache
        if cache_key in self._local_cache:
            # Check if cache entry has expired
            if cache_key in self._local_cache_timestamps:
                age = datetime.now() - self._local_cache_timestamps[cache_key]
                if age.total_seconds() > self.ttl:
                    # Expired, remove from cache
                    del self._local_cache[cache_key]
                    del self._local_cache_timestamps[cache_key]
                    return None
            
            data = self._local_cache[cache_key]
            result = IntentResult(**data)
            logger.debug(f"Cache hit (local): {cache_key}")
            return result
        
        return None
    
    async def set(self, user_input: str, result: IntentResult, context: Optional[str] = None):
        """Cache result for user input."""
        cache_key = self._generate_cache_key(user_input, context)
        data = result.dict()
        
        # Try Redis first
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                await redis_client.setex(
                    cache_key, 
                    self.ttl, 
                    json.dumps(data, ensure_ascii=False)
                )
                logger.debug(f"Cached to Redis: {cache_key}")
                return
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
        
        # Fall back to local cache
        self._local_cache[cache_key] = data
        self._local_cache_timestamps[cache_key] = datetime.now()
        
        # Clean up old local cache entries periodically
        await self._cleanup_local_cache()
        
        logger.debug(f"Cached locally: {cache_key}")
    
    async def _cleanup_local_cache(self):
        """Clean up expired entries from local cache."""
        current_time = datetime.now()
        expired_keys = []
        
        for key, timestamp in self._local_cache_timestamps.items():
            age = current_time - timestamp
            if age.total_seconds() > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._local_cache[key]
            del self._local_cache_timestamps[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    async def clear(self, pattern: Optional[str] = None):
        """Clear cache entries."""
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                if pattern:
                    keys = await redis_client.keys(pattern)
                    if keys:
                        await redis_client.delete(*keys)
                else:
                    await redis_client.flushdb()
                logger.info("Redis cache cleared")
            except Exception as e:
                logger.warning(f"Redis cache clear error: {e}")
        
        # Clear local cache
        if pattern:
            keys_to_remove = [k for k in self._local_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._local_cache[key]
                if key in self._local_cache_timestamps:
                    del self._local_cache_timestamps[key]
        else:
            self._local_cache.clear()
            self._local_cache_timestamps.clear()
        
        logger.info("Local cache cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "enabled": self.enabled,
            "local_cache_size": len(self._local_cache),
            "ttl_seconds": self.ttl
        }
        
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                info = await redis_client.info()
                stats["redis_connected"] = True
                stats["redis_memory_used"] = info.get("used_memory_human", "N/A")
                stats["redis_keys"] = await redis_client.dbsize()
            except Exception as e:
                stats["redis_connected"] = False
                stats["redis_error"] = str(e)
        else:
            stats["redis_connected"] = False
        
        return stats
    
    async def health_check(self) -> bool:
        """Check cache service health."""
        try:
            # Test local cache
            test_key = "health_check_test"
            test_data = {"test": True}
            self._local_cache[test_key] = test_data
            result = self._local_cache.get(test_key)
            del self._local_cache[test_key]
            
            if result != test_data:
                return False
            
            # Test Redis if available
            redis_client = await self.get_redis_client()
            if redis_client:
                await redis_client.ping()
            
            return True
        
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False
    
    async def close(self):
        """Close cache connections."""
        if self._redis:
            await self._redis.close()


# Global cache service instance
cache_service = CacheService()