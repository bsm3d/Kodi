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
import random
import re
import sys
import time
import urllib.parse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from html import unescape
from resources.lib import client, cache, constants
from resources.lib.content_filter import ContentFilter

_addon = xbmcaddon.Addon()

class Main:
    def __init__(self):
        """Initialize the Internet Archive addon"""
        # URLs
        self.base_url = constants.BASE_URL
        self.search_url = self.base_url + 'services/search/beta/page_production/'
        self.img_path = self.base_url + 'services/img/'
        self.item_path = self.base_url + 'details/'
        
        # Headers and data
        self.headers = {'Referer': self.base_url}
        self.threads = []
        self.cache = {}
        
        # Addon configuration
        self._addon = xbmcaddon.Addon()
        
        # User interface settings
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
        
        # Define available actions
        self.actions = {
            'list_items': lambda: self.list_items(self.parameters('target'), 
                                                int(self.parameters('page') or 1), 
                                                self.parameters('content_type')),
            'play': lambda: self.play(self.parameters('target'), 
                                    self.parameters('content_type')),
            'clear_cache': self.clear_cache,
            'clear_history': lambda: self.clear_history(self.parameters('type')),
            'clear_favorites': lambda: self.clear_favorites(self.parameters('content_type')),
            'search': lambda: self.search(),
            'search_results': lambda: self.search_media(self.parameters('query'), 
                                                    int(self.parameters('page') or 1), 
                                                    self.parameters('media_type') or 'all'),
            'show_history': lambda: self.show_history(self.parameters('content_type')),
            'show_search_history': lambda: self.show_search_history(),
            'french_content': lambda: self.get_french_content(int(self.parameters('page') or 1), 
                                                            self.parameters('content_type')),
            'category': lambda: self.get_category_content(self.parameters('cat'), 
                                                        int(self.parameters('page') or 1), 
                                                        self.parameters('content_type')),
            'categories': lambda: self.categories_menu(self.parameters('content_type')),
            'favorites_menu': self.favorites_menu,
            'history_menu': self.history_menu,
            'show_favorites_section': lambda: self.show_favorites_section(),
            'show_history_section': lambda: self.show_history_section(),
            'toggle_favorite': lambda: self.toggle_favorite(self.parameters('target'), 
                                                        urllib.parse.unquote(self.parameters('title'))),
            'settings': lambda: self.open_settings()
        }
        
        # Add the remove_search_history action here
        self.actions.update({
            'remove_search_history': lambda: self.remove_search_history_item(
                urllib.parse.unquote(self.parameters('query')),
                self.parameters('type')
            )
        })
        
        # Start routing
        action = self.parameters('action')
        self.actions.get(action, self.main_menu)()

    def get_french_content(self, page, content_type='video'):
        # Build filter map based on content type
        if content_type == 'video':
            filter_map = {
                'mediatype': {'movies': 'inc'},
                'format': {
                    'h.264': 'inc',
                    'mp4': 'inc',
                    'mpeg4': 'inc',
                    '512kb MPEG4': 'inc',
                    'MPEG2': 'inc',
                    'Matroska': 'inc',
                    'HDV': 'inc',
                    'MKV': 'inc',
                    'AVI': 'inc',
                    'OGG': 'inc',
                    'Video': 'inc'
                }
            }
        else:
            filter_map = {
                'mediatype': {'audio': 'inc'}
            }

        params = {
            'service_backend': 'metadata',
            'hits_per_page': 100,
            'page': page,
            'filter_map': json.dumps(filter_map),
            'user_query': 'language:french OR description:français OR description:french OR description:"en français"',
            'sort': 'addeddate:desc',
            'aggregations': 'false'
        }
        resp = client.request(constants.SEARCH_URL, headers=self.headers, params=params)
        data = resp.get('response', {}).get('body', {}).get('hits', {})
        self.display_results(data, page, 'french_content', content_type=content_type)


    def get_category_content(self, category, page, content_type):
        # Build filter map based on content type
        if content_type == 'video':
            filter_map = {
                'mediatype': {'movies': 'inc'},
                'format': {
                    'h.264': 'inc',
                    'mp4': 'inc',
                    'mpeg4': 'inc',
                    'MPEG2': 'inc',
                    'Matroska': 'inc',
                    'MKV': 'inc',
                    'AVI': 'inc',
                    'Video': 'inc'
                }
            }
        else:
            filter_map = {
                'mediatype': {'audio': 'inc'}
            }

        params = {
            'service_backend': 'metadata',
            'hits_per_page': 100,
            'page': page,
            'filter_map': json.dumps(filter_map),
            'user_query': f'collection:{category}',
            'sort': 'addeddate:desc',
            'aggregations': 'false'
        }
        resp = client.request(constants.SEARCH_URL, headers=self.headers, params=params)
        data = resp.get('response', {}).get('body', {}).get('hits', {})
        self.display_results(data, page, 'category', cat=category, content_type=content_type)

    def search(self):
        """Display the search dialog"""
        keyboard = xbmc.Keyboard()
        keyboard.setHeading("Search")
        keyboard.doModal()
        
        if keyboard.isConfirmed():
            query = keyboard.getText().strip()
            if not query:
                return
                
            media_types = ['All', 'Movies', 'Audio']
            media_type_idx = xbmcgui.Dialog().select('Media Type', media_types)
            
            if media_type_idx != -1:
                media_type_map = {'0': 'all', '1': 'video', '2': 'audio'}
                media_type = media_type_map[str(media_type_idx)]
                
                # Perform the search and add to history if successful
                if self.search_media(query, 1, media_type):
                    self.add_to_search_history(query, media_type)

    def search_media(self, query, page=1, media_type='all'):
        """Perform the search and display results"""
        query = urllib.parse.unquote_plus(query)
        filter_map = {
            'video': '{"mediatype":{"movies":"inc"}}',
            'audio': '{"mediatype":{"audio":"inc"}}'
        }
        
        params = {
            'service_backend': 'metadata',
            'user_query': query,
            'hits_per_page': 100,
            'page': page,
            'filter_map': filter_map.get(media_type, '{}'),
            'aggregations': 'false'
        }
        
        try:
            raw_resp = client.request(constants.SEARCH_URL, headers=self.headers, params=params)
            
            # If the response is a string, try to parse it as JSON
            if isinstance(raw_resp, str):
                try:
                    resp = json.loads(raw_resp)
                except json.JSONDecodeError:
                    constants.log("Failed to parse search response as JSON", "ERROR")
                    return False
            else:
                resp = raw_resp
                
            if not resp or not isinstance(resp, dict):
                constants.log("Invalid response format", "ERROR")
                return False

            hits_data = resp.get('response', {}).get('body', {}).get('hits', {})
            
            if not hits_data or not hits_data.get('hits', []):
                xbmcgui.Dialog().notification(
                    constants.ADDON_NAME, 
                    "No results", 
                    constants.ADDON_ICON
                )
                xbmcplugin.endOfDirectory(int(sys.argv[1]))
                return False
                
            self.display_results(hits_data, page, 'search_results', 
                            query=query, media_type=media_type)
            return True
            
        except Exception as e:
            constants.log(f"Search error: {str(e)}", "ERROR")
            xbmcgui.Dialog().notification(
                constants.ADDON_NAME, 
                "Search error", 
                constants.ADDON_ICON
            )
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
            return False

    def add_to_search_history(self, query, media_type):
        """Add a search to the history"""
        try:
            current_history = json.loads(self._addon.getSetting('search_history') or '[]')
            
            # Format: [{"query": "text", "type": "video", "date": timestamp}, ...]
            new_entry = {
                'query': query,
                'type': media_type,
                'date': time.time()
            }
            
            # Check for duplicates and update the date if exists
            exists = False
            for item in current_history:
                if item['query'] == query and item['type'] == media_type:
                    item['date'] = time.time()
                    exists = True
                    break
            
            if not exists:
                current_history.insert(0, new_entry)
                current_history = current_history[:20]  # Keep the last 20
            
            self._addon.setSetting('search_history', json.dumps(current_history))
            
        except Exception as e:
            constants.log(f"Error adding to search history: {e}", "ERROR")

    def show_search_history(self):
        """Display the search history"""
        try:
            # Load the history and reorder with the most recent first
            history = sorted(
                json.loads(self._addon.getSetting('search_history') or '[]'),
                key=lambda x: x.get('date', 0) if isinstance(x, dict) else 0,
                reverse=True
            )

            if not history:
                xbmcgui.Dialog().notification(
                    constants.ADDON_NAME,
                    "No history",
                    constants.ADDON_ICON
                )
                xbmcplugin.endOfDirectory(int(sys.argv[1]))
                return

            # Add the option to clear the history
            clear_item = xbmcgui.ListItem("[Clear history]")
            clear_item.setArt({
                'icon': constants.ADDON_ICON,
                'fanart': constants.ADDON_FANART
            })
            url_clear = f"{sys.argv[0]}?action=clear_history&type=search"
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url_clear, clear_item, False)

            # Display each item in the history
            for item in history:
                # If the item is a string (old format), convert it to a dictionary
                if isinstance(item, str):
                    query = item
                    media_type = 'all'
                else:
                    query = item.get('query', '')
                    media_type = item.get('type', 'all')

                # URL to re-run the search
                url = (f"{sys.argv[0]}?action=search_results&"
                    f"query={urllib.parse.quote_plus(query)}&"
                    f"page=1&media_type={media_type}")

                # Create the list item
                list_item = xbmcgui.ListItem(query)
                list_item.setArt({
                    'icon': constants.ADDON_ICON,
                    'fanart': constants.ADDON_FANART
                })

                # Context menu to delete
                context_menu = [(
                    'Remove from history',
                    f"RunPlugin({sys.argv[0]}?action=remove_search_history&"
                    f"query={urllib.parse.quote(query)}&type={media_type})"
                )]
                list_item.addContextMenuItems(context_menu)

                # Add the item to the list
                xbmcplugin.addDirectoryItem(
                    int(sys.argv[1]),
                    url,
                    list_item,
                    True
                )

            xbmcplugin.endOfDirectory(int(sys.argv[1]))

        except Exception as e:
            constants.log(f"Error showing search history: {e}", "ERROR")
            xbmcgui.Dialog().notification(
                constants.ADDON_NAME,
                "Error displaying history",
                constants.ADDON_ICON
            )
            xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=False)
            
    def _add_favorite_item(self, slug, info, content_type):
        """Helper method to add a favorite item to the list"""
        title = info['title']
        url = f"{sys.argv[0]}?action=play&target={slug}&content_type={content_type}"
        
        li = xbmcgui.ListItem(title)
        
        if content_type == 'video':
            info_labels = {
                'title': title,
                'plot': info.get('description', ''),
                'director': info.get('creator', ''),
                'year': info.get('year', ''),
                'genre': info.get('genre', []),
                'duration': info.get('duration', ''),
                'mediatype': 'video'
            }
            li.setInfo('video', info_labels)
        else:
            info_labels = {
                'title': title,
                'artist': info.get('creator', ''),
                'genre': info.get('genre', []),
                'duration': info.get('duration', ''),
                'comment': info.get('description', ''),
                'mediatype': 'song'
            }
            li.setInfo('music', info_labels)
            
        li.setArt({
            'icon': constants.IMG_PATH + slug,
            'thumb': constants.IMG_PATH + slug,
            'fanart': constants.ADDON_FANART
        })
        
        li.setProperty('IsPlayable', 'true')
        
        fav_action = f"RunPlugin({sys.argv[0]}?action=toggle_favorite&target={slug}&title={urllib.parse.quote(title)})"
        li.addContextMenuItems([('Remove from favorites', fav_action)])
        
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, False)

    def _add_history_item(self, item_id, info, content_type):
        """Helper method to add a history item to the list"""
        title = info['title']
        url = f"{sys.argv[0]}?action=play&target={item_id}&content_type={content_type}"
        li = xbmcgui.ListItem(title)
        li.setProperty('IsPlayable', 'true')
        li.setArt({
            'icon': constants.IMG_PATH + item_id,
            'fanart': constants.ADDON_FANART
        })
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, False)

    def show_favorites(self):
        """Display favorites filtered by content type"""
        content_type = self.parameters('content_type')
        favorites = json.loads(self._addon.getSetting('favorites') or '{}')
        
        # Filter favorites by content type
        filtered_favorites = {
            k: v for k, v in favorites.items() 
            if v.get('content_type') == content_type
        }
        
        if not filtered_favorites:
            xbmcgui.Dialog().notification(
                constants.ADDON_NAME, 
                f"No {content_type} favorites", 
                constants.ADDON_ICON
            )
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
            return

        for slug, info in filtered_favorites.items():
            title = info['title']
            url = f"{sys.argv[0]}?action=play&target={slug}&content_type={content_type}"
            
            li = xbmcgui.ListItem(title)
            
            # Set metadata according to content type
            if content_type == 'video':
                info_labels = {
                    'title': title,
                    'plot': info.get('description', ''),
                    'director': info.get('creator', ''),
                    'year': info.get('year', ''),
                    'genre': info.get('genre', []),
                    'duration': info.get('duration', ''),
                    'mediatype': 'video'
                }
                li.setInfo('video', info_labels)
            else:
                info_labels = {
                    'title': title,
                    'artist': info.get('creator', ''),
                    'genre': info.get('genre', []),
                    'duration': info.get('duration', ''),
                    'comment': info.get('description', ''),
                    'mediatype': 'song'
                }
                li.setInfo('music', info_labels)
                
            li.setArt({
                'icon': constants.IMG_PATH + slug,
                'thumb': constants.IMG_PATH + slug,
                'fanart': constants.ADDON_FANART
            })
            
            li.setProperty('IsPlayable', 'true')
            
            # Context menu to remove from favorites
            fav_action = f"RunPlugin({sys.argv[0]}?action=toggle_favorite&target={slug}&title={urllib.parse.quote(title)})"
            li.addContextMenuItems([('Remove from favorites', fav_action)])
            
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, False)

        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def clear_favorites(self, content_type):
        """Clear favorites for a specific content type"""
        # Ask for confirmation
        if not xbmcgui.Dialog().yesno(
            constants.ADDON_NAME, 
            f"Clear {content_type} favorites?"
        ):
            return

        # Get current favorites
        favorites = json.loads(self._addon.getSetting('favorites') or '{}')
        
        # Keep only items of the other content type
        updated_favorites = {
            k: v for k, v in favorites.items() 
            if v.get('content_type') != content_type
        }
        
        # Save updated favorites
        self._addon.setSetting('favorites', json.dumps(updated_favorites))
        
        # Show notification
        xbmcgui.Dialog().notification(
            constants.ADDON_NAME, 
            f"{content_type.title()} favorites cleared", 
            constants.ADDON_ICON
        )
        
        # Refresh the container to show changes
        xbmc.executebuiltin('Container.Refresh')

    def toggle_favorite(self, slug, title):
        try:
            # Get current favorites from addon settings
            favorites = json.loads(self._addon.getSetting('favorites') or '{}')
            
            if slug in favorites:
                # Remove from favorites
                del favorites[slug]
                message = "Removed from favorites"
            else:
                # Decode metadata
                metadata = json.loads(urllib.parse.unquote(self.parameters('metadata')))
                
                # Add to favorites with enriched metadata
                favorites[slug] = {
                    'title': title,
                    'added_date': time.time(),
                    'content_type': self.parameters('content_type') or 'video',
                    'description': metadata.get('plot', ''),
                    'creator': metadata.get('creator', ''),
                    'year': metadata.get('year', ''),
                    'genre': metadata.get('genre', []),
                    'duration': metadata.get('duration', ''),
                    'language': metadata.get('language', ''),
                    'collection': metadata.get('collection', [])
                }
                message = "Added to favorites"

            # Save to settings
            self._addon.setSetting('favorites', json.dumps(favorites))
            xbmcgui.Dialog().notification(constants.ADDON_NAME, message, constants.ADDON_ICON)
            
            # Refresh the interface
            xbmc.executebuiltin('Container.Refresh')
            
        except Exception as e:
            constants.log(f"Favorite toggle error: {e}", "ERROR")
            xbmcgui.Dialog().notification(constants.ADDON_NAME, 
                                        "Error modifying favorite", 
                                        constants.ADDON_ICON)
        
    def show_history(self, content_type):
        setting_key = f"{content_type}_history"
        history = json.loads(_addon.getSetting(setting_key) or '{}')
        
        if not history:
            xbmcgui.Dialog().notification(constants.ADDON_NAME, f"No {content_type} history", 
                                          constants.ADDON_ICON)
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
            return

        for item_id, info in sorted(history.items(), key=lambda x: x[1]['timestamp'], reverse=True):
            title = info['title']
            url = f"{sys.argv[0]}?action=play&target={item_id}&content_type={content_type}"
            li = xbmcgui.ListItem(title)
            li.setProperty('IsPlayable', 'true')
            li.setArt({'icon': constants.IMG_PATH + item_id, 'fanart': constants.ADDON_FANART})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, False)

        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        
    def show_favorites_section(self):
        """Display favorites section with Clear button on top"""
        content_type = self.parameters('content_type')
        favorites = json.loads(self._addon.getSetting('favorites') or '{}')
        
        # Filter favorites by content type
        filtered_favorites = {k: v for k, v in favorites.items() if v.get('content_type') == content_type}
        
        # Add Clear button at the top
        clear_item = xbmcgui.ListItem(f"[COLOR red]Clear {content_type.title()} Favorites[/COLOR]")
        clear_item.setArt({
            'icon': constants.ADDON_ICON,
            'fanart': constants.ADDON_FANART
        })
        clear_url = f"{sys.argv[0]}?action=clear_favorites&content_type={content_type}"
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), clear_url, clear_item, False)
        
        # Display favorites
        if not filtered_favorites:
            xbmcgui.Dialog().notification(
                constants.ADDON_NAME, 
                f"No {content_type} favorites", 
                constants.ADDON_ICON
            )
        else:
            for slug, info in filtered_favorites.items():
                self._add_favorite_item(slug, info, content_type)
        
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_history_section(self):
        """Display history section with Clear button on top"""
        content_type = self.parameters('content_type')
        setting_key = f"{content_type}_history"
        history = json.loads(self._addon.getSetting(setting_key) or '{}')
        
        # Add Clear button at the top
        clear_item = xbmcgui.ListItem(f"[COLOR red]Clear {content_type.title()} History[/COLOR]")
        clear_item.setArt({
            'icon': constants.ADDON_ICON,
            'fanart': constants.ADDON_FANART
        })
        clear_url = f"{sys.argv[0]}?action=clear_history&type={content_type}"
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), clear_url, clear_item, False)
        
        # Display history
        if not history:
            xbmcgui.Dialog().notification(
                constants.ADDON_NAME, 
                f"No {content_type} history", 
                constants.ADDON_ICON
            )
        else:
            for item_id, info in sorted(history.items(), key=lambda x: x[1]['timestamp'], reverse=True):
                self._add_history_item(item_id, info, content_type)
        
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def play(self, item_id, content_type='video'):
        url = self.item_path + item_id
        html = client.request(url, headers=self.headers)
        
        if not html:
            xbmcgui.Dialog().notification(constants.ADDON_NAME, 
                                        "Unable to load item", 
                                        constants.ADDON_ICON)
            return

        jsob = re.search(r'class="js-play8-playlist".+?value=\'([^\']+)', html)
        if jsob:
            data = json.loads(jsob.group(1))
            total = len(data)
            
            if total > 1:
                sources = [(i.get('title'), i.get('sources')[0].get('file')) for i in data]
                
                if content_type == 'video':
                    sources = [i for i in data[0]['sources'] if 'height' in i.keys() and '.jpg' not in i.get('name')]
                    
                    if len(sources) > 1:
                        sources.sort(key=lambda x: (int(x.get('height')), x.get('source'), int(x.get('size'))), reverse=True)
                        srcs = [f"{i.get('name').split('.')[-1]} ({i.get('source')} {i.get('height')}p) {self.format_bytes(int(i.get('size')))}" 
                            for i in sources]
                        ret = xbmcgui.Dialog().select("Select quality", srcs)
                        if ret == -1:
                            return
                    else:
                        ret = 0

                    title = data[0]['title']
                    # Add to video history
                    self.add_to_history(item_id, title, 'video')
                else:
                    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
                    playlist.clear()
                    
                    # Get metadata of the audio item
                    metadata = client.request(url.replace('/details/', '/metadata/'))
                    
                    # Use album cover image as fanart if available
                    album_cover = metadata.get('misc', {}).get('image')
                    
                    for title, source in sources:
                        li = xbmcgui.ListItem(title)
                        full_url = urllib.parse.urljoin(self.base_url, source)
                        li.setPath(full_url)
                        
                        # Set fanart using album cover image
                        li.setArt({
                            'thumb': constants.IMG_PATH + item_id,
                            'fanart': album_cover or constants.ADDON_FANART,
                            'clearlogo': album_cover or (constants.IMG_PATH + item_id)
                        })
                        
                        # Other audio metadata
                        li.setInfo('music', {
                            'title': title,
                            'artist': metadata.get('creator', ''),
                            'album': metadata.get('album', ''),
                            'year': metadata.get('year', None)
                        })
                        
                        li.setProperty('IsPlayable', 'true')
                        playlist.add(url=full_url, listitem=li)
                    
                    # Add to audio history
                    self.add_to_history(item_id, title, 'audio')
                    xbmc.Player().play(playlist)
            
            elif total == 1:
                jd = client.request(url.replace('/details/', '/metadata/'))
                if content_type == 'video':
                    sources = [i for i in jd.get('files') if 'height' in i.keys() and '.jpg' not in i.get('name')]
                    
                    if len(sources) > 1:
                        sources.sort(key=lambda x: (int(x.get('height')), x.get('source'), int(x.get('size'))), reverse=True)
                        srcs = [f"{i.get('name').split('.')[-1]} ({i.get('source')} {i.get('height')}p) {self.format_bytes(int(i.get('size')))}" 
                            for i in sources]
                        ret = xbmcgui.Dialog().select("Select quality", srcs)
                        if ret == -1:
                            return
                    else:
                        ret = 0

                    title = jd.get('title', item_id)
                    # Add to video history
                    self.add_to_history(item_id, title, 'video')
                else:
                    # Audio management
                    sources = [i for i in jd.get('files') if 
                            i.get('source') == 'original' and 
                            i.get('name').endswith(('.mp3', '.ogg', '.m4a', '.flac'))]
                    if not sources:
                        xbmcgui.Dialog().notification(constants.ADDON_NAME, 
                                                    "No audio source found", 
                                                    constants.ADDON_ICON)
                        return
                    ret = 0
                    title = jd.get('title', item_id)
                    # Add to audio history
                    self.add_to_history(item_id, title, 'audio')
                        
                surl = f"https://{random.choice(jd.get('workable_servers'))}{jd.get('dir')}/{urllib.parse.quote(sources[ret].get('name'))}"
                
                li = xbmcgui.ListItem(title)
                li.setPath(surl)
                
                if content_type == 'audio':
                    # Set fanart using album cover image
                    album_cover = jd.get('misc', {}).get('image')
                    li.setArt({
                        'thumb': constants.IMG_PATH + item_id,
                        'fanart': album_cover or constants.ADDON_FANART,
                        'cover': album_cover or (constants.IMG_PATH + item_id)
                    })
                    
                    li.setInfo('music', {
                        'title': title,
                        'artist': jd.get('creator', ''),
                        'album': jd.get('album', ''),
                        'year': jd.get('year', None)
                    })
                
                li.setProperty('IsPlayable', 'true')
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem=li)
            
    def format_bytes(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"
    
    def add_to_history(self, item_id, title, content_type):
        setting_key = f"{content_type}_history"
        current_history = json.loads(_addon.getSetting(setting_key) or '{}')
        current_history[item_id] = {'title': title, 'timestamp': time.time()}
        _addon.setSetting(setting_key, json.dumps(current_history))

    def clear_history(self, history_type):
        # Ask for confirmation
        if not xbmcgui.Dialog().yesno(constants.ADDON_NAME, 
                                      f"Clear {history_type} history?"):
            return

        if history_type == 'video':
            _addon.setSetting('video_history', '{}')
        elif history_type == 'audio':
            _addon.setSetting('audio_history', '{}')
        elif history_type == 'search':
            _addon.setSetting('search_history', '[]')
        elif history_type == 'cache':
            cache.cache_clear()
            
        xbmcgui.Dialog().notification(constants.ADDON_NAME, 
                                      f"{history_type} history cleared", 
                                      constants.ADDON_ICON)

    def clear_cache(self):
        # Clear the cache and display a notification
        try:
            # Ask for confirmation
            if not xbmcgui.Dialog().yesno(constants.ADDON_NAME, "Clear cache?"):
                return

            # Clear the cache via the cache module
            cache.cache_clear()
            
            # Success notification
            xbmcgui.Dialog().notification(
                constants.ADDON_NAME,
                "Cache cleared successfully",
                constants.ADDON_ICON
            )
        except Exception as e:
            # Log the error and notification
            constants.log(f"Error clearing cache: {str(e)}", "ERROR")
            xbmcgui.Dialog().notification(
                constants.ADDON_NAME,
                "Error clearing cache",
                constants.ADDON_ICON
            )

    def list_items(self, target, page, content_type):
        filter_map = '{"mediatype":{"' + ('movies' if content_type == 'video' else 'audio') + '":"inc"}}'
        data = cache.get(self.get_items, constants.CACHE_DURATION, filter_map, target, page)
        
        if data:
            self.display_results(data, page, 'list_items', target=target, content_type=content_type)

    def get_items(self, filter_map, target, page):
        params = {
            'page_type': 'collection_details',
            'page_target': target,
            'hits_per_page': 100,
            'page': page,
            'filter_map': filter_map,
            'aggregations': 'false',
            'client_url': constants.BASE_URL
        }
        resp = client.request(constants.SEARCH_URL, headers=self.headers, params=params)
        return resp.get('response', {}).get('body', {}).get('hits', {})

    def display_results(self, data, page, action, **kwargs):
        # Get current favorites
        favorites = json.loads(self._addon.getSetting('favorites') or '{}')
        
        # Process results
        items = self.filter_results(data.get('hits', []))
        for item in items:
            fields = item.get('fields', {})
            title = self.clean_text(fields.get('title', ''))
            description = self.clean_text(unescape(fields.get('description', '')))
            identifier = fields.get('identifier')
            content_type = kwargs.get('content_type', 'video')

            # Create item URL and listitem
            url = f"{sys.argv[0]}?action=play&target={identifier}&content_type={content_type}"
            li = xbmcgui.ListItem(title)
            
            # Build metadata
            metadata = {
                'title': title,
                'plot': description,
                'mediatype': content_type,
                'creator': fields.get('creator', ''),
                'year': fields.get('year', ''),
                'genre': fields.get('subject', []),
                'duration': fields.get('runtime', ''),
                'language': fields.get('language', ''),
                'collection': fields.get('collection', []),
            }
            
            # Set info based on content type
            if content_type == 'video':
                info_type = 'video'
                info_labels = {
                    'title': title,
                    'plot': description,
                    'mediatype': 'video',
                    'director': metadata['creator'],
                    'year': metadata['year'],
                    'genre': metadata['genre'],
                    'duration': metadata['duration']
                }
            else:
                info_type = 'music'
                info_labels = {
                    'title': title,
                    'artist': metadata['creator'],
                    'album': fields.get('album', ''),
                    'comment': description,
                    'mediatype': 'song',
                    'genre': metadata['genre'],
                    'duration': metadata['duration']
                }
            
            # Set item info and art
            li.setInfo(info_type, info_labels)
            li.setArt({
                'icon': constants.IMG_PATH + identifier,
                'thumb': constants.IMG_PATH + identifier,
                'fanart': constants.ADDON_FANART
            })
            
            # Add favorites context menu
            is_favorite = identifier in favorites
            menu_label = 'Remove from favorites' if is_favorite else 'Add to favorites'
            
            # Create favorite action URL
            encoded_metadata = urllib.parse.quote(json.dumps(metadata))
            fav_action = (f"RunPlugin({sys.argv[0]}?action=toggle_favorite"
                        f"&target={identifier}"
                        f"&title={urllib.parse.quote(title)}"
                        f"&content_type={content_type}"
                        f"&metadata={encoded_metadata})")
            
            li.addContextMenuItems([(menu_label, fav_action)])
            li.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, False)
        
        # Handle pagination
        total_hits = data.get('total', 0)
        if page < (total_hits + 99) // 100:
            next_url = f"{sys.argv[0]}?action={action}&page={page + 1}"
            
            # Add action specific parameters 
            if action == 'search_results':
                next_url += f"&query={kwargs['query']}&media_type={kwargs.get('media_type', 'all')}"
            elif action == 'category':
                next_url += f"&content_type={kwargs.get('content_type', 'video')}&cat={kwargs.get('cat', '')}"
            elif action == 'list_items':
                next_url += f"&content_type={kwargs.get('content_type', 'video')}&target={kwargs.get('target', '')}"
            elif action == 'french_content':
                next_url += f"&content_type={kwargs.get('content_type', 'video')}"
                
            # Add next page item
            li = xbmcgui.ListItem("Next page")
            li.setArt({'icon': constants.ADDON_ICON, 'fanart': constants.ADDON_FANART})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), next_url, li, True)

        # End directory
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def categories_menu(self, content_type):
        film_cats, audio_cats = constants.load_categories()
        categories = film_cats if content_type == 'video' else audio_cats
        
        for title, category in categories.items():
            url = f"{sys.argv[0]}?action=category&cat={category}&content_type={content_type}&page=1"
            li = xbmcgui.ListItem(title)
            li.setArt({'icon': constants.ADDON_ICON, 'fanart': constants.ADDON_FANART})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, True)

        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def open_settings(self):
        xbmc.executebuiltin('Addon.OpenSettings(plugin.video.bsm3d.archive.org)')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=False)
    
    def main_menu(self):
        items = [
            {"title": "Audio", "action": "categories", "content_type": "audio"},
            {"title": "Movies", "action": "categories", "content_type": "video"},
            {"title": "French Movies", "action": "french_content", "content_type": "video", "page": 1},
            {"title": "[B]Favorites[/B]", "action": "favorites_menu"},
            {"title": "[B]History[/B]", "action": "history_menu"},
            {"title": "Search History", "action": "show_search_history"},
            {"title": "Search", "action": "search"},
            {"title": "Setup", "action": "settings"}
        ]

        for item in items:
            listitem = xbmcgui.ListItem(item["title"])
            listitem.setArt({'icon': constants.ADDON_ICON, 'fanart': constants.ADDON_FANART})
            url = f"{sys.argv[0]}?" + urllib.parse.urlencode({k: v for k, v in item.items() if k != 'title'})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, True)

        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        
    def favorites_menu(self):
        """Display the favorites sections"""
        items = [
            {"title": "[B]Audio Favorites[/B]", "action": "show_favorites_section", "content_type": "audio"},
            {"title": "[B]Video Favorites[/B]", "action": "show_favorites_section", "content_type": "video"}
        ]

        for item in items:
            listitem = xbmcgui.ListItem(item["title"])
            listitem.setArt({'icon': constants.ADDON_ICON, 'fanart': constants.ADDON_FANART})
            url = f"{sys.argv[0]}?" + urllib.parse.urlencode({k: v for k, v in item.items() if k != 'title'})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, True)

        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def history_menu(self):
        """Display the history sections"""
        items = [
            {"title": "[B]Audio History[/B]", "action": "show_history_section", "content_type": "audio"},
            {"title": "[B]Video History[/B]", "action": "show_history_section", "content_type": "video"}
        ]

        for item in items:
            listitem = xbmcgui.ListItem(item["title"])
            listitem.setArt({'icon': constants.ADDON_ICON, 'fanart': constants.ADDON_FANART})
            url = f"{sys.argv[0]}?" + urllib.parse.urlencode({k: v for k, v in item.items() if k != 'title'})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, True)

        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def parameters(self, arg):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(sys.argv[2]).query)
        return params.get(arg, [''])[0]
    
    def sanitize_title(self, text):
        """
        Clean and validate a title
        Returns None if the title is not valid
        """
        if not text:
            return None
            
        # Convert to string and clean spaces
        text = str(text).strip()
        
        # Basic checks
        if (
            len(text) < 3 or                                # Too short 
            text.isnumeric() or                            # Only numbers
            not any(c.isalpha() for c in text) or         # No letters
            all(c.isupper() for c in text if c.isalpha()) # All uppercase
        ):
            return None
            
        # Patterns to reject (via regex)
        reject_patterns = [
            r'^\d+$',                    # Numbers only
            r'^[0-9\-_.]+$',            # Numbers and special chars only
            r'^test[0-9]*$',            # Test, test1, test2, etc.
            r'^[^a-zA-Z]*$',            # No letters
            r'^new\s*folder',           # "new folder"
            r'^untitled',               # "untitled"
            r'^copy\s*of',              # "copy of"
            r'^\[.*\]$',                # Text in brackets only
            r'^\(.*\)$',                # Text in parentheses only
            r'^[a-zA-Z0-9]{32,}$',      # Long alphanumeric strings (hashes)
        ]
        
        for pattern in reject_patterns:
            if re.match(pattern, text.lower()):
                return None

        # Basic cleaning
        text = text.strip('._-[]() ')
        text = ' '.join(text.split())  # Normalize spaces
        
        # Final length check after cleaning
        if len(text) < 3:
            return None
            
        return text

    def filter_results(self, data):
        # Skip if no data
        if not data:
            return []
            
        # Check if keywords filtering is enabled globally
        if not constants.USE_KEYWORDS_FILTER:
            return data
        
        # Get specific filter settings
        filter_settings = {
            'adult': self._addon.getSettingBool('filter_adult'),
            'religious': self._addon.getSettingBool('filter_religious'),
            'sensitive': self._addon.getSettingBool('filter_sensitive'),
            'educational': self._addon.getSettingBool('filter_educational'),
            'promotional': self._addon.getSettingBool('filter_promotional'),
            'low_quality': self._addon.getSettingBool('filter_lowquality'),
            'social': self._addon.getSettingBool('filter_social'),
            'spam': self._addon.getSettingBool('filter_spam'),
            'gaming': self._addon.getSettingBool('filter_gaming'),
            'unwanted': self._addon.getSettingBool('filter_unwanted'),
            'french': self._addon.getSettingBool('filter_french')
        }
        
        # Create a content filter with the specific settings
        content_filter = ContentFilter()
        filtered_data = []
        
        # Process each item
        for item in data:
            fields = item.get('fields', {})
            
            # Basic check for required fields
            if not fields.get('identifier'):
                continue
                
            # Get title and description for content checking
            title = str(fields.get('title', '')).strip()
            description = str(fields.get('description', '')).strip()
            subject = str(fields.get('subject', '')).strip()
            creator = str(fields.get('creator', '')).strip()
            collection = str(fields.get('collection', '')).strip()
            
            # Skip items with no title or too short
            if not title or len(title) < 2:
                continue
            
            # Prepare content for comprehensive checking
            content_to_check = ' '.join([title, description, subject, creator, collection]).lower()
            
            # Flag to determine if item should be filtered
            should_filter = False
            
            # Check each filter category
            if filter_settings['adult'] and content_filter.is_filtered_category(content_to_check, 'adult_content'):
                should_filter = True
            
            if filter_settings['religious'] and content_filter.is_filtered_category(content_to_check, 'religious_content'):
                should_filter = True
            
            if filter_settings['sensitive'] and content_filter.is_filtered_category(content_to_check, 'sensitive_content'):
                should_filter = True
            
            # Additional category checks can be added similarly
            
            # Final comprehensive filtering
            if should_filter or content_filter.is_filtered(title, content_to_check):
                continue
                
            # Store cleaned title
            fields['title'] = title
            filtered_data.append(item)
        
        return filtered_data
    
    def clean_text(self, text):
        """Remove non-ASCII characters and control characters"""
        return text.encode('ascii', 'ignore').decode()

if __name__ == '__main__':
    Main()