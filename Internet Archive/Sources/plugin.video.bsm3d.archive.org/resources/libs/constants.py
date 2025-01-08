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

import json
import xbmcaddon
import xbmcvfs
import xbmc

_addon = xbmcaddon.Addon()

# Addon Info
ADDON_ID = _addon.getAddonInfo('id')
ADDON_NAME = _addon.getAddonInfo('name')
ADDON_VERSION = _addon.getAddonInfo('version')
ADDON_ICON = _addon.getAddonInfo('icon')
ADDON_FANART = _addon.getAddonInfo('fanart')

# File Paths
CACHE_FILE = xbmcvfs.translatePath(_addon.getAddonInfo('profile') + '/cache.db')
CERT_FILE = xbmcvfs.translatePath('special://xbmc/system/certs/cacert.pem')

# URLs
BASE_URL = 'https://archive.org/'
SEARCH_URL = BASE_URL + 'services/search/beta/page_production/'
IMG_PATH = BASE_URL + 'services/img/'
ITEM_PATH = BASE_URL + 'details/'

# Database
CACHE_TABLE = 'cache'

# HTTP Headers
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en',
    'Accept-Encoding': 'gzip'
}

def log(msg, level=xbmc.LOGDEBUG):
    if _addon.getSettingBool('debug_mode'):
        xbmc.log(f"[{ADDON_ID}] {msg}", level)

def load_categories():
    try:
        film_cats = json.loads(_addon.getSetting('custom_film_categories'))
        audio_cats = json.loads(_addon.getSetting('custom_audio_categories'))
        return film_cats, audio_cats
    except json.JSONDecodeError as e:
        log(f"Error loading categories: {e}", xbmc.LOGERROR)
        return DEFAULT_FILM_CATEGORIES, DEFAULT_AUDIO_CATEGORIES

def load_keywords():
    try:
        return json.loads(_addon.getSetting('excluded_keywords'))
    except json.JSONDecodeError as e:
        log(f"Error loading keywords: {e}", xbmc.LOGERROR)
        return DEFAULT_EXCLUDED_KEYWORDS

# Default categories Fall back
FILM_CATEGORIES = {
    "All Movies": "movies",
    "Anime": "anime",
    "Animation/Cartoons": "animationandcartoons",
    "Classics": "feature_films",
    "Classics 50": "classic_tv_1950s",
    "Classics 60": "classic_tv_1960s",
    "Classics 70": "classic_tv_1970s",
    "Classics 80": "classic_tv_1980s",
    "Classics 90": "classic_tv_1990s",
    "Colorized": "colorized-movies",
    "Film Noir": "Film_Noir",
    "SciFi/Horror": "SciFi_Horror",
    "Ted Talks": "tedtalks",
}

AUDIO_CATEGORIES = {
    "All Audios": "audio",
    "Vinyl Box": "the-vinyl-box",
    "HIFI": "hifidelity",
    "HipHop": "hiphopmixtapes",
    "Opera": "vinyl_frank-defreytas-memoria-opera",
    "OldTime Radio": "oldtimeradio",
    "SoundTracks": "hifidelity_soundtracks",
    "78 RPM": "78rpm",
}

DEFAULT_EXCLUDED_KEYWORDS = []  # Empty list, as keywords are now in content_filter.py

# Settings
CACHE_DURATION = int(_addon.getSetting('cache_duration'))
DEBUG_MODE = _addon.getSettingBool('debug_mode')
USE_KEYWORDS_FILTER = _addon.getSettingBool('use_keywords_filter')