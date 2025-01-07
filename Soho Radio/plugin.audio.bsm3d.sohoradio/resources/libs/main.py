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

import sys
import urllib.parse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from resources.lib.constants import get_stream_url, ADDON_ICON

class Main:
    def __init__(self):
        self.addon_handle = int(sys.argv[1])
        self.addon = xbmcaddon.Addon()
        self.args = urllib.parse.parse_qs(sys.argv[2][1:])
        self.action = self.args.get('action', [None])[0]
        self.route()

    def route(self):
        if self.action == 'setup':
            self.addon.openSettings()
            xbmc.executebuiltin('Container.Refresh')
        else:
            self.list_menu()

    def list_menu(self):
        fanart_path = xbmcaddon.Addon().getAddonInfo('path') + '/fanart.jpg'

        # Récupérer la qualité actuelle
        quality = self.addon.getSetting('quality')
        quality_text = "128 KB" if quality == '0' else "320 KB"

        # Ajouter l'option "Play Soho Live" avec la qualité
        stream_url = get_stream_url()
        if stream_url:
            name = f"Play Soho Live ({quality_text})"
            item = xbmcgui.ListItem(name)
            item.setArt({'icon': ADDON_ICON, 'fanart': fanart_path})
            item.setProperty('IsPlayable', 'true')

            info_tag = item.getMusicInfoTag()
            info_tag.setTitle(name)

            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle,
                url=stream_url,
                listitem=item,
                isFolder=False
            )

        # Ajouter l'option "Setup"
        name = "Setup"
        item = xbmcgui.ListItem(name)
        item.setArt({'icon': ADDON_ICON, 'fanart': fanart_path})
        item.setProperty('IsPlayable', 'false')

        setup_url = 'plugin://{}/?action=setup'.format(self.addon.getAddonInfo('id'))
        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle,
            url=setup_url,
            listitem=item,
            isFolder=False
        )

        xbmcplugin.endOfDirectory(self.addon_handle)

if __name__ == '__main__':
    Main()