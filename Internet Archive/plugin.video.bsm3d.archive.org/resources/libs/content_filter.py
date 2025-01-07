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

import re

class ContentFilter:
    def __init__(self, excluded_keywords=None, additional_filters=None):
        # Expand and refine filter categories
        self.filter_categories = {
            'adult_content': [
                'adult', 'mature', 'nsfw', 'xxx', 'erotic',
                'nudity', 'naked', 'nude', 'sex', 'porn', 'hardcore',
                'explicit', 'intimate'
            ],
            
            'religious_extreme': [
                'extremist', 'radical', 'fundamentalist', 
                'militant', 'intolerant', 'sectarian'
            ],
            
            'political_sensitive': [
                'propaganda', 'extremism', 'conspiracy', 
                'radical', 'militant', 'hate', 'violence'
            ],
            
            'sensitive_content': [
                'isis', 'isil', 'daesh', 'jihad', 'terrorist', 
                'terrorism', 'martyrdom', 'caliphate', 
                'antisemitic', 'holocaust denial', 
                'al qaeda', 'ethnic conflict'
            ],
            
            'spam_keywords': [
                'free', 'download', 'hack', 'crack', 'pirate',
                'leaked', 'stolen', 'torrent', 'keygen', 
                'serial', 'activation', 'cheat'
            ],
            
            'low_quality_content': [
                'amateur', 'random', 'compilation', 
                'low quality', 'poor quality', 'bad quality',
                'low resolution', 'poor resolution'
            ],
            
            'promotional_content': [
                'advertisement', 'commercial', 'promo', 
                'sponsored', 'marketing', 'selling'
            ]
        }
        
        # Refined regex patterns with more context
        self.regex_patterns = {
            'social_handles': r'(@\w+)',
            'hashtags': r'(#\w+)',
            'urls': r'(https?://\S+)',
            'email': r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
            'quality_indicators': r'\b(1080p|720p|480p|360p|240p|144p)\b',
            'file_extensions': r'\.(mp4|avi|mkv|mov|wmv)$',
            'timestamps': r'\b(\d{1,2}:\d{2}(:\d{2})?)\b',
            'episode_markers': r'\b(ep|episode|part)\s*\d+\b',
            'season_markers': r'\b(s|season)\s*\d+\b',
            'download_links': r'\b(download|télécharger)\s*(here|ici)?\b'
        }
        
        # Add custom keywords
        if excluded_keywords:
            self.excluded_keywords = set(self._flatten_filter_categories())
            self.excluded_keywords.update(excluded_keywords)
        else:
            self.excluded_keywords = set(self._flatten_filter_categories())
        
        # Add additional regex filters
        if additional_filters:
            self.regex_patterns.update(additional_filters)
    
    def _flatten_filter_categories(self):
        return [word for category in self.filter_categories.values() 
                for word in category]

    def sanitize_title(self, text):
        """
        Advanced title validation and cleaning
        """
        if not text:
            return None
        
        # Convert and clean
        text = str(text).strip()
        
        # Extensive validation rules
        rules = [
            lambda t: len(t) >= 3,                     # Minimum length
            lambda t: any(c.isalpha() for c in t),     # Contains letters
            lambda t: not t.isnumeric(),               # Not only numbers
            lambda t: not all(c.isupper() for c in t), # Not all uppercase
        ]
        
        # Apply validation rules
        if not all(rule(text) for rule in rules):
            return None
        
        # Advanced cleaning
        text = re.sub(r'^\W+|\W+$', '', text)  # Remove non-alphanumeric chars at ends
        text = ' '.join(text.split())  # Normalize spaces
        
        # Final validation
        return text if len(text) >= 3 else None
    
    def is_filtered_category(self, search_text, category):
        """
        Check if content belongs to a specific filter category
        """
        if category not in self.filter_categories:
            return False
        
        keywords = self.filter_categories.get(category, [])
        
        for keyword in keywords:
            if keyword in search_text:
                return True
        
        return False

    def is_filtered(self, title, description=None):
        if not title:
            return True
        
        # Convertir en minuscules
        search_text = (title + ' ' + (description or '')).lower()
        
        # Expressions à bloquer complètement
        blocking_patterns = [
            r'terrorist',
            r'islamist',
            r'extremist', 
            r'ethnic cleansing',
            r'backed.*terrorists',
            r'evict.*from.*home',
            r'religious violence',
            r'sectarian conflict'
        ]
        
        # Vérification stricte des expressions
        for pattern in blocking_patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                return True
        
        # Listes de mots-clés bloquants
        blocking_keywords = [
            'genocide', 
            'massacre', 
            'ethnic conflict', 
            'religious war',
            'holy war',
            'violent extremism',
            'radical militia'
        ]
        
        # Vérification des mots-clés bloquants
        for keyword in blocking_keywords:
            if keyword in search_text:
                return True
        
        # Scoring système
        def calculate_sensitivity_score(text):
            score = 0
            sensitive_words = {
                'terrorist': 10,
                'islamist': 8,
                'violence': 6,
                'conflict': 5,
                'war': 5,
                'militia': 7,
                'extremist': 9,
                'radical': 8
            }
            
            for word, points in sensitive_words.items():
                if word in text:
                    score += points
            
            return score
        
        # Score de sensibilité
        sensitivity_score = calculate_sensitivity_score(search_text)
        
        # Bloquer si score trop élevé
        if sensitivity_score > 15:
            return True
        
        return False

    def get_filter_categories(self):
        return list(self.filter_categories.keys())

    def enable_category(self, category):
        if category in self.filter_categories:
            self.excluded_keywords.update(self.filter_categories[category])

    def disable_category(self, category):
        if category in self.filter_categories:
            self.excluded_keywords.difference_update(self.filter_categories[category])

    def add_custom_keywords(self, keywords):
        if isinstance(keywords, (list, set)):
            self.excluded_keywords.update(keywords)
        elif isinstance(keywords, str):
            self.excluded_keywords.add(keywords)

    def add_custom_regex(self, name, pattern):
        self.regex_patterns[name] = pattern