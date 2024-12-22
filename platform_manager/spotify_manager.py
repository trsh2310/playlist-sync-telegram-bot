import requests
import logging
from urllib.parse import urlencode
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

    def save_token(self, user_id, token, auth_spotify):
        try:
            token_info = auth_spotify.get_access_token(token)
            return True
        except SpotifyOauthError:
            return False

    def get_user_playlists(self, user_id):
        
        """Получаем список плейлистов пользователя."""
        
        token = self.db.get_token(user_id, "spotify")
        if not token:
            raise ValueError("Spotify token not found for user.")

        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = requests.get(f"{self.API_BASE_URL}/me/playlists", headers=headers)
        if response.status_code != 200:
            logging.error(f"Failed to fetch playlists: {response.text}")
            raise ValueError("Failed to fetch playlists.")

        playlists = response.json()["items"]
        logging.info(f"Fetched {len(playlists)} playlists for user {user_id}.")

        # Формируем список плейлистов с порядковым номером
        return [{"name": playlist["name"], "id": playlist["id"]} for playlist in playlists]

    def get_playlist_tracks(self, user_id, playlist_id):
        
        """Получаем список треков из выбранного плейлиста."""
        
        token = self.db.get_token(user_id, "spotify")
        if not token:
            raise ValueError("Spotify token not found for user.")

        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = requests.get(f"{self.API_BASE_URL}/playlists/{playlist_id}/tracks", headers=headers)
        if response.status_code != 200:
            logging.error(f"Failed to fetch tracks: {response.text}")
            raise ValueError("Failed to fetch tracks.")

        tracks = response.json()["items"]
        logging.info(f"Fetched {len(tracks)} tracks from playlist {playlist_id} for user {user_id}.")

        # Формируем список треков
        track_list = []
        for item in tracks:
            track = item["track"]
            track_list.append({
                "track_id": track["id"],
                "artist": ", ".join([artist["name"] for artist in track["artists"]]),
                "title": track["name"]
            })

        return track_list