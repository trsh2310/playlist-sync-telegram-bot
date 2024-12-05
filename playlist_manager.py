from api_clients.vk import VKMusic
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




