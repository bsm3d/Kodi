"""
    Addon : KODI - Internet Archive Browser
    Version 1.0.0 - Kodi 21 (Omega) or Upper
    Author: BSM3D
    Description: This Kodi addon allows users to browse and search the Internet Archive's video and audio collections
    Copyright (C) 2025 BSM3D

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import hashlib
import json
import pickle
import threading
import time
import zlib
import xbmcvfs
import xbmcaddon
from sqlite3 import dbapi2 as db, Binary
from resources.lib import constants

class EnhancedCache:
    def __init__(self, 
                 cache_file=None, 
                 max_size_mb=100, 
                 default_duration=24):
        """
        Advanced caching mechanism
        
        Args:
            cache_file: Path to cache database
            max_size_mb: Maximum cache size in MB
            default_duration: Default cache duration in hours
        """
        self._addon = xbmcaddon.Addon()
        self.cache_file = cache_file or constants.CACHE_FILE
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_duration = default_duration
        self._lock = threading.Lock()
        
        self._ensure_cache_dir()
        self._init_database()
    
    def _ensure_cache_dir(self):
        """Create cache directory if not exists"""
        profile_path = xbmcvfs.translatePath(
            self._addon.getAddonInfo('profile')
        )
        if not xbmcvfs.exists(profile_path):
            try:
                xbmcvfs.mkdirs(profile_path)
            except Exception as e:
                constants.log(f"Cache dir error: {e}", "ERROR")
    
    def _init_database(self):
        """Initialize cache database"""
        with self._connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    timestamp INTEGER,
                    size INTEGER,
                    hits INTEGER DEFAULT 1,
                    expires INTEGER
                )
            ''')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires)'
            )
    
    def _connection(self):
        """Create SQLite connection"""
        conn = db.connect(self.cache_file)
        conn.row_factory = self._dict_factory
        return conn
    
    def _dict_factory(self, cursor, row):
        """Convert row to dictionary"""
        return {
            cursor.description[i][0]: row[i] 
            for i in range(len(cursor.description))
        }
    
    def _generate_key(self, function, *args, **kwargs):
        """Generate unique cache key"""
        key_parts = [
            str(function.__name__),
            *map(str, args),
            json.dumps(kwargs, sort_keys=True)
        ]
        return hashlib.md5('_'.join(key_parts).encode()).hexdigest()
    
    def get(self, 
            function, 
            duration=None, 
            *args, 
            **kwargs):
        """
        Get cached value or compute and cache
        
        Args:
            function: Function to cache
            duration: Cache duration in hours
            *args: Function positional arguments
            **kwargs: Function keyword arguments
        """
        duration = duration or self.default_duration
        key = self._generate_key(function, *args, **kwargs)
        
        with self._lock:
            with self._connection() as conn:
                # Check existing cache
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT value, expires FROM cache WHERE key = ?', 
                    (key,)
                )
                result = cursor.fetchone()
                
                current_time = int(time.time())
                
                # Valid cache exists
                if (result and 
                    result['expires'] > current_time):
                    # Update hit count
                    conn.execute(
                        'UPDATE cache SET hits = hits + 1 WHERE key = ?', 
                        (key,)
                    )
                    return pickle.loads(
                        zlib.decompress(result['value'])
                    )
                
                # Compute fresh result
                fresh_result = function(*args, **kwargs)
                
                if fresh_result is not None:
                    # Compress and store
                    compressed_value = Binary(
                        zlib.compress(pickle.dumps(fresh_result))
                    )
                    value_size = len(compressed_value)
                    
                    # Insert or replace cache entry
                    conn.execute('''
                        INSERT OR REPLACE INTO cache 
                        (key, value, timestamp, size, expires) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        key, 
                        compressed_value, 
                        current_time, 
                        value_size, 
                        current_time + (duration * 3600)
                    ))
                
                # Manage cache size
                self._manage_cache_size(conn)
                
                return fresh_result
    
    def _manage_cache_size(self, conn):
        """
        Manage cache size by removing least used entries
        """
        conn.execute('''
            DELETE FROM cache 
            WHERE key IN (
                SELECT key FROM cache 
                ORDER BY hits ASC, timestamp ASC 
                LIMIT 100
            )
        ''')
    
    def clear(self):
        """Clear entire cache"""
        with self._lock:
            with self._connection() as conn:
                conn.execute(f'DROP TABLE IF EXISTS cache')
                conn.execute('VACUUM')

# Global cache instance
cache_manager = EnhancedCache()

# Compatibility functions
def get(function, duration, *args, **kwargs):
    return cache_manager.get(function, duration, *args, **kwargs)

def cache_clear():
    cache_manager.clear()

def remove(function, *args, **kwargs):
    key = cache_manager._generate_key(function, *args, **kwargs)
    with cache_manager._connection() as conn:
        conn.execute('DELETE FROM cache WHERE key = ?', (key,))
        conn.commit()