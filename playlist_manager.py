from api_clients.vk import VKClient
from models import Database
from scrapers.vk_scraper import VKScraper
from search_and_sync import SearchAndSync


class PlaylistManager:
    def __init__(self):
        self.db = Database()

    def get_auth_url(self, platform):
        if platform == 'vk':
            return (
                f"https://oauth.vk.com/authorize?"
                f"client_id=52764217&display=page&redirect_uri=https://oauth.vk.com/blank.html&"
                f"scope=audio,offline&response_type=token&v=5.131"
            )

    def save_token(self, platform, user_id, token_url):
        token = token_url.split('access_token=')[1].split('&')[0]
        self.db.save_token(user_id, platform, token)
        return f"Токен для {platform} сохранён."

    def fetch_playlist(self, platform, user_id, playlist_url):
        token = self.db.get_token(user_id, platform)
        if not token:
            return "Сначала выполните авторизацию."

        if platform == 'vk':
            client = VKClient(token)
            tracks = client.fetch_playlist(playlist_url)
            track_info = [VKScraper.extract_track_info(track) for track in tracks]
            self.db.save_tracks(user_id, track_info, platform)
            return f"Найдено и сохранено {len(tracks)} треков."
        return "Платформа не поддерживается."

    def sync_playlist(self, platform, user_id):
        token = self.db.get_token(user_id, platform)
        if not token:
            return "Сначала выполните авторизацию."

        if platform == 'vk':
            client = VKClient(token)
            tracks = self.db.get_tracks(user_id, 'vk')
            track_ids = SearchAndSync.search_tracks(client, tracks)
            playlist = client.create_playlist("Синхронизированный плейлист", "Создан ботом")
            client.add_tracks_to_playlist(playlist['id'], playlist['owner_id'], track_ids)
            return "Плейлист успешно синхронизирован!"
        return "Платформа не поддерживается."

