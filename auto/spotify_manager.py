import requests
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from urllib.parse import urlencode
from config import SPOTIFY_APP_ID, SPOTIFY_REDIRECT_URI, SPOTIFY_SECRET_KEY
from models import Database

logging.basicConfig(level=logging.INFO)

class SpotifySync:
    AUTH_URL = "https://accounts.spotify.com/authorize"
    API_BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, database: Database):
        self.db = database

    def get_auth_url(self, user_id):
        """
        Генерируем URL для авторизации пользователя через Implicit Grant Flow.
        """
        auth_manager = SpotifyOAuth(client_id=SPOTIFY_APP_ID,
                                    client_secret=SPOTIFY_SECRET_KEY,
                                    redirect_uri=SPOTIFY_REDIRECT_URI,
                                    scope='playlist-read-collaborative playlist-read-private playlist-modify-public playlist-modify-private')
        auth_url = auth_manager.get_authorize_url()
        return auth_url

    def save_token(self, user_id, token):
        """
        Сохраняем токен в базе данных.
        """
        self.db.save_token(user_id, "spotify", token)

    def get_user_playlists(self, user_id):
        """
        Получаем список плейлистов пользователя.
        """
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
        """
        Получаем список треков из выбранного плейлиста.
        """
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