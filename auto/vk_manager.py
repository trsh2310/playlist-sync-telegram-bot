import requests
import vk_api
from vk_api.audio import VkAudio
from config import VK_REDIRECT_URI, VK_APP_ID
from models import Database


class VKSync:
    def __init__(self):
        self.db = Database()

    def get_auth_url(self, platform):
        """Выводит ссылку для регистрации"""
        if platform == "vk":
            app_id = VK_APP_ID
            redirect_uri = VK_REDIRECT_URI
            scope = "audio,offline"
            auth_url = (f"https://oauth.vk.com/authorize?client_id={app_id}&display=page"
                        f"&redirect_uri={redirect_uri}&scope={scope}&response_type=token&v=5.131")
            return auth_url
        raise ValueError("Unknown platform")

    def vk_save_token(self, user_id, platform, token_url):
        """Сохраняет токен в ДБ"""
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

    def get_vk_audio(self, user_id):
        """
        Возвращает экземпляр VkAudio, авторизованный с помощью токена пользователя.
        """
        vk_token = self.db.get_token(user_id, "vk")
        if not vk_token:
            raise ValueError("VK token not found.")

        session = vk_api.VkApi(token=vk_token)
        return VkAudio(session)

    def list_playlists(self, user_id):
        """
        Возвращает список плейлистов пользователя из VK.
        """
        vk_token = self.db.get_token(user_id, "vk")
        vk_id = get_user_id(vk_token)
        vk_audio = self.get_vk_audio(user_id)
        playlists = vk_audio.get_albums()
        return playlists

    def list_songs_in_playlist(self, user_id, playlist_number):
        """
        Выводит список песен в указанном плейлисте.
        """
        vk_audio = self.get_vk_audio(user_id)
        playlists = vk_audio.get_albums(user_id)

        if playlist_number < 1 or playlist_number > len(playlists):
            raise ValueError("Invalid playlist number.")

        playlist = playlists[playlist_number - 1]
        songs = vk_audio.get(album_id=playlist['id'], owner_id=playlist['owner_id'])

        for idx, song in enumerate(songs, start=1):
            print(f"{idx}. {song['artist']} - {song['title']}")

        return songs

    def save_playlist_to_db(self, user_id, playlist_number):
        """
        Сохраняет треки указанного плейлиста в базу данных.
        """
        songs = self.list_songs_in_playlist(user_id, playlist_number)
        tracks = [{
            'track_id': song['id'],
            'artist': song['artist'],
            'title': song['title']
        } for song in songs]

        self.db.save_tracks(user_id, tracks, platform="vk")
