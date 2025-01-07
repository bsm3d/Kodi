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

import gzip
import json
import re
import ssl
import time
import urllib.request
import urllib.parse
import urllib.error
from io import BytesIO
from resources.lib import constants

class RobustHTTPClient:
    def __init__(self, 
                 base_timeout=20, 
                 max_retries=3, 
                 backoff_factor=2):
        """
        Robust HTTP client for the Internet Archive addon
        
        Args:
            base_timeout: Base timeout in seconds
            max_retries: Maximum number of retries
            backoff_factor: Factor to increase delay between retries
        """
        self.base_timeout = base_timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def _create_ssl_context(self):
        """Create a secure SSL context"""
        ctx = ssl.create_default_context(cafile=constants.CERT_FILE)
        ctx.set_alpn_protocols(['http/1.1'])
        return ctx
    
    def _add_request_header(self, request, headers):
        """Add headers to the request"""
        try:
            scheme = urllib.parse.urlparse(request.get_full_url()).scheme
            host = request.host
            referer = headers.get('Referer', '') or f'{scheme}://{host}/'
            request.add_unredirected_header('Host', host)
            request.add_unredirected_header('Referer', referer)
            for key, value in headers.items():
                request.add_header(key, value)
        except Exception as e:
            constants.log(f"Header error: {str(e)}", "ERROR")
    
    def _detect_encoding(self, response, content):
        """Detect content encoding"""
        content_type = response.headers.get('content-type', '').lower()
        
        if 'charset=' in content_type:
            return content_type.split('charset=')[-1]

        patterns = [
            r'<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"',
            r'xml\s*version.+encoding="([^"]+)"'
        ]
        
        for pattern in patterns:
            pattern = pattern.encode('utf8')
            if match := re.search(pattern, content, re.IGNORECASE):
                return match.group(1).decode('utf8')
        
        return None
    
    def _process_response(self, response):
        """Process the HTTP response"""
        content = response.read()
        
        # Decompress if gzip
        if response.headers.get('content-encoding', '').lower() == 'gzip':
            content = gzip.GzipFile(fileobj=BytesIO(content)).read()

        # If JSON, parse directly
        if 'json' in response.headers.get('content-type', '').lower():
            try:
                return json.loads(content.decode('utf-8'))
            except json.JSONDecodeError as e:
                constants.log(f"JSON decode error: {e}", "ERROR")
                return {}

        # If not JSON, try to detect encoding
        encoding = self._detect_encoding(response, content)
        
        if encoding:
            return content.decode(encoding, errors='ignore')
        else:
            return content.decode('utf-8', errors='ignore')
    
    def request(self, 
                url: str, 
                headers: dict = None, 
                params: dict = None, 
                timeout: int = None):
        """
        Send an HTTP request with retry mechanism
        
        Args:
            url: Request URL
            headers: Custom headers
            params: Request parameters
            timeout: Custom timeout
        
        Returns:
            Response content
        """
        # Prepare headers
        _headers = constants.DEFAULT_HEADERS.copy()
        if headers:
            _headers.update(headers)

        # Handle parameters
        if params:
            params = urllib.parse.urlencode(params) if isinstance(params, dict) else params
            url = f"{url}?{params}"

        # Timeout
        timeout = timeout or self.base_timeout

        for attempt in range(self.max_retries):
            try:
                # Create request
                req = urllib.request.Request(url)
                self._add_request_header(req, _headers)
                
                # SSL configuration
                ssl_ctx = self._create_ssl_context()
                handlers = [urllib.request.HTTPSHandler(context=ssl_ctx)]
                opener = urllib.request.build_opener(*handlers)
                urllib.request.install_opener(opener)
                
                # Send request
                response = urllib.request.urlopen(req, timeout=timeout)
                return self._process_response(response)
            
            except (urllib.error.URLError, TimeoutError) as e:
                # Handle network errors
                constants.log(f"Request attempt {attempt + 1} failed: {str(e)}", "ERROR")
                
                # Exponential backoff between retries
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    constants.log(f"Request error for {url}: {str(e)}", "ERROR")
                    return ''
        
        return ''

# Compatibility function with old code
def request(url, headers=None, params=None, timeout='20'):
    client = RobustHTTPClient(base_timeout=int(timeout))
    return client.request(url, headers=headers, params=params)