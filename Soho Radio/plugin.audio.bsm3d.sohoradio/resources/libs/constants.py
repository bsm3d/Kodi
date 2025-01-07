"""
    Addon : KODI - Soho Radio Streaming
    Version 1.0.0 - Kodi 21 (Omega) or Upper
    Author: BSM3D
    Description: Listen to Soho Radio live on Kodi, Last Night a D.J. Saved My Life
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

import xbmc
import xbmcaddon

_addon = xbmcaddon.Addon()

ADDON_ID = _addon.getAddonInfo('id')
ADDON_NAME = "Soho Radio"
ADDON_VERSION = "1.1.0"
ADDON_ICON = _addon.getAddonInfo('icon')

def get_stream_url():
    try:
        quality = _addon.getSetting('quality')
        xbmc.log(f"[Soho Radio] Selected quality: {quality}", level=xbmc.LOGINFO)
        
        if quality == '0':  # 128 KB
            stream_url = _addon.getSetting('stream_url_128')
        else:  # 320 KB par défaut
            stream_url = _addon.getSetting('stream_url_320')
        
        if not stream_url:  # Si l'URL est vide, utiliser l'URL 320 KB par défaut
            stream_url = "https://sohoradiomusic.doughunt.co.uk:8010/320mp3"
            
        xbmc.log(f"[Soho Radio] Stream URL: {stream_url}", level=xbmc.LOGINFO)
        return stream_url
        
    except Exception as e:
        xbmc.log(f"[Soho Radio] Error getting stream URL: {str(e)}", level=xbmc.LOGERROR)
        return "https://sohoradiomusic.doughunt.co.uk:8010/320mp3"  # URL par défaut en cas d'erreur

