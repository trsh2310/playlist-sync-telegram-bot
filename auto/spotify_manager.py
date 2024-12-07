from urllib.parse import urlencode, urlparse, parse_qs
import requests

from config import SPOTIFY_APP_ID, SPOTIFY_REDIRECT_URI, SPOTIFY_SECRET_KEY
from models import Database

class SpotifyPlaylistManager:
    def __init__(self):
        self.db = Database()

    def get_spotify_auth_url(self):
        params = {
            "response_type": "code",
            "client_id": SPOTIFY_APP_ID,
            "scope": "user-library-read",
            "redirect_uri": SPOTIFY_REDIRECT_URI,
        }
        return f"https://accounts.spotify.com/authorize?{urlencode(params)}"

    def spotify_save_token(self, user_id, platform, token_url):
        parsed_url = urlparse(token_url)
        query_params = parse_qs(parsed_url.query)
        auth_code = query_params.get("code", [None])[0]

        if not auth_code:
            return("Ошибка авторизации. Попробуйте снова.")

        token_url = "https://accounts.spotify.com/api/token"
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": SPOTIFY_REDIRECT_URI,
            "client_id": SPOTIFY_APP_ID,
            "client_secret": SPOTIFY_SECRET_KEY,
        }

        response = requests.post(token_url, data=token_data)
        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info["access_token"]
            self.db.save_token(user_id, platform, access_token)
            refresh_token = token_info["refresh_token"]
            return ("Авторизация успешно завершена!")
        else:
            return ("Ошибка при получении токена. Попробуйте снова.")

    def list_playlists(self, user_id):
        token = self.db.get_token(user_id, 'spotify')
        if not token:
            raise ValueError("Spotify token not found for this user.")

        url = "https://api.spotify.com/v1/me/playlists"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception("Error fetching playlists from Spotify.")

        playlists = response.json()['items']
        return [{'name': playlist['name'], 'id': playlist['id']} for playlist in playlists]

    def list_songs_in_playlist(self, user_id, playlist_id):
        token = self.db.get_token(user_id, 'spotify')
        if not token:
            raise ValueError("Spotify token not found for this user.")

        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception("Error fetching songs from playlist.")

        tracks = response.json()['items']
        songs = [{'track_id': track['track']['id'],
                  'artist': track['track']['artists'][0]['name'],
                  'title': track['track']['name']} for track in tracks]

        # Save songs to the database
        self.db.save_tracks(user_id, songs, platform='spotify')
        return songs


