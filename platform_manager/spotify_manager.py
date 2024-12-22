import logging
from config import SPOTIFY_REDIRECT_URI, SPOTIFY_APP_ID, SPOTIFY_SECRET_KEY
from models import Database

import spotipy
from spotipy import SpotifyOAuth, SpotifyOauthError

logging.basicConfig(level=logging.INFO)

class SpotifyManager:
    AUTH_URL = "https://accounts.spotify.com/authorize"
    API_BASE_URL = "https://api.spotify.com/v1"
    def get_auth_url(self):
        """
        Генерируем URL для авторизации пользователя через Implicit Grant Flow.
        """
        scope = 'playlist-read-collaborative playlist-read-private playlist-modify-public playlist-modify-private'
        auth_spotify = SpotifyOAuth(client_id=SPOTIFY_APP_ID,
                                    client_secret=SPOTIFY_SECRET_KEY,
                                    redirect_uri=SPOTIFY_REDIRECT_URI,
                                    scope=scope,
                                    cache_handler=spotipy.cache_handler.CacheFileHandler(cache_path=".spotifycache"))
        return auth_spotify

    def save_token(self, user_id, code, auth_spotify):
        try:
            token_info = auth_spotify.get_access_token(code)
            return token_info
        except SpotifyOauthError:
            return False