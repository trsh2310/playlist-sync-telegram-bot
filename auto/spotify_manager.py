import requests
import logging
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
        Генерируем URL для авторизации.
        """
        params = {
            "client_id": SPOTIFY_APP_ID,
            "client_secret" : SPOTIFY_SECRET_KEY,
            "response_type": "token",
            "redirect_uri": SPOTIFY_REDIRECT_URI,
            "scope": "playlist-read-private playlist-read-collaborative"
        }
        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        logging.info(f"Generated auth URL for user {user_id}: {auth_url}")
        print (auth_url)
        return auth_url

    def save_token(self, user_id, token):
        """
        Сохраняем токен в базе данных.
        """
        self.db.save_token(user_id, "spotify", token)

    def get_saved_albums(access_token, limit=20, offset=0, market=None):
        """
        Получает список альбомов, сохранённых в библиотеке текущего пользователя Spotify
        :param access_token: str. Токен доступа
        :param limit: int. Максимальное количество альбомов
        :param offset: int. Смещение для пагинации
        :param market: str. Код страны
        :return: list. Список альбомов
        """
        url = "https://api.spotify.com/v1/me/albums"

        params = {
            "limit": limit,
            "offset": offset
        }
        if market:
            params["market"] = market

        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        # Выполнение GET-запроса
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            albums = []
            for item in data.get("items", []):
                album = item["album"]
                albums.append({
                    "name": album["name"],
                    "artist": ", ".join([artist["name"] for artist in album["artists"]]),
                    "release_date": album["release_date"],
                    "total_tracks": album["total_tracks"],
                    "url": album["external_urls"]["spotify"]
                })

            return albums
        else:
            # Обработка ошибок
            return {"error": response.status_code,
                    "message": response.json().get("error", {}).get("message", "Unknown error")}

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