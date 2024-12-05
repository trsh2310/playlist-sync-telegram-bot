import requests

from api_clients.vk import VKMusic
from config import VK_REDIRECT_URI, VK_APP_ID
from models import Database
from search_and_sync import SearchAndSync


class VKPlaylistManager:
    def __init__(self):
        self.db = Database()

    def get_auth_url(self, platform):
        if platform == "vk":
            app_id = VK_APP_ID
            redirect_uri = VK_REDIRECT_URI
            scope = "audio,offline"
            auth_url = (f"https://oauth.vk.com/authorize?client_id={app_id}&display=page"
                        f"&redirect_uri={redirect_uri}&scope={scope}&response_type=token&v=5.131")
            return auth_url
        raise ValueError("Unknown platform")

    def save_token(self, platform, user_id, token_url):
        if platform != "vk":
            return "Platform not supported"

        token_data = dict(pair.split("=") for pair in token_url.split("#")[1].split("&"))
        access_token = token_data.get("access_token")
        self.db.save_token(user_id, platform, access_token)
        if not access_token:
            return "Ошибка при получении токена"

        response = requests.get("https://api.vk.com/method/users.get", params={
            "access_token": access_token,
            "v": "5.131"
        })
        if response.status_code == 200 and "response" in response.json():
            user_info = response.json()["response"][0]
            return (f"Авторизация успешна! \n"
                    f"Привет, {user_info['first_name']} {user_info['last_name']}! 🎉\n"
                    f"Отправьте ссылку на плейлист, который хотите синхронизировать.")
        else:
            return "Ошибка авторизации"

    def fetch_playlist(self, platform, user_id, playlist_url):
        token = self.db.get_token(user_id, platform)
        if not token:
            return "Сначала выполните авторизацию."

        if platform == 'vk':
            client = VKMusic(token)
            tracks = client.fetch_playlist(playlist_url)
            return f"Найдено {len(tracks)} треков."
        return "Платформа не поддерживается."

    def sync_playlist(self, platform, user_id):
        token = self.db.get_token(user_id, platform)
        if not token:
            return "Сначала выполните авторизацию."

        if platform == 'vk':
            client = VKMusic(token)
            tracks = self.db.get_tracks(user_id, platform)
            track_ids = SearchAndSync.search_tracks(client, tracks)
            playlist = client.create_playlist("Синхронизированный плейлист", "Создан ботом")
            client.add_tracks_to_playlist(playlist['id'], playlist['owner_id'], track_ids)
            return "Плейлист успешно синхронизирован!"
        return "Платформа не поддерживается."