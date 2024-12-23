import logging
import re
import logging
from yandex_music.exceptions import UnauthorizedError

from platform_manager.vk_manager import VKMusicManager
logger = logging.getLogger(__name__)


class Playlist:
    def __init__(self):
        self.name = None
        self.tracks = []
        self.platform = None

    #обработка плейлиста из спотифая
    def from_spotify(self, url, spotify_user):
        uri = self.spotify_url_parser(url)
        try:
            current_playlist = spotify_user.playlist_items(uri)
        except ValueError:
            logging.error(f"Invalid playlist URI: {url}")
            raise ValueError("Не удалось найти плейлист по данному URL.")
        except Exception as e:
            logging.error(f"Ошибка при получении плейлиста из Spotify: {e}")
            raise Exception("Ошибка при получении плейлиста из Spotify.")

        self.name = current_playlist['name']
        self.platform = "Spotify"
        self.tracks = []

        for i in current_playlist['items']:
            try:
                track_artists = ", ".join(i['track']['artists'])
                track_name = i['track']['name']
                self.tracks.append((track_artists, track_name))
            except KeyError as e:
                logging.error(f"Ошибка в структуре данных трека: {e}")
                continue  # Пропускаем трек, если есть ошибка в данных
            except Exception as e:
                logging.error(f"Неизвестная ошибка при обработке трека: {e}")
                continue  # Пропускаем трек, если произошла непредвиденная ошибка

    @staticmethod
    def spotify_url_parser(playlist_url):
        pattern = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
        match = re.match(pattern, playlist_url)
        if match:
            uri = match.group(1)
            return uri
        else:
            raise ValueError("Invalid Spotify playlist link")

    # обработка плейлиста из яндекса
    # обработка плейлиста из яндекса
    def from_yandex(self, url, yandex_user):
        yandex_user_id, yandex_playlist_id = self.yandex_url_parser(url)
        try:
            pl = yandex_user.users_playlists(yandex_playlist_id, yandex_user_id)
        except:
            raise ValueError
        self.name = pl.title
        self.platform = "Яндекс"
        self.tracks = []
        for i in pl.tracks:
            track_artists = ''
            for j, artist in enumerate(i.track.artists):
                if j != 0:
                    track_artists += ', '
                track_artists += artist.name
            track_name = i.track.title
            self.tracks.append((track_artists, track_name))

    @staticmethod
    def yandex_url_parser(playlist_url):
        pattern = r"https://music\.yandex\.(?:ru|com)/users/([^/]+)/playlists/(\d+)"
        match = re.match(pattern, playlist_url)
        if match:
            user_id, playlist_id = match.groups()
            return user_id, playlist_id
        else:
            raise ValueError("Invalid Yandex Music playlist link")


    def from_vk(self, name: str, vk_user: VKMusicManager):
        playlists = vk_user.get_playlists()

        if not playlists:
            logging.error(f"Не удалось получить плейлисты для пользователя: {name}")
            raise ValueError("Не удалось получить плейлисты из ВКонтакте.")

        for playlist in playlists:
            if name == playlist['title']:
                self.name = name
                self.platform = "ВК"
                self.tracks = []
                try:
                    current_playlist = vk_user.audio.get(owner_id=playlist['owner_id'], album_id=playlist['id'])
                except Exception as e:
                    logging.error(f"Ошибка при получении треков из ВКонтакте: {e}")
                    raise Exception("Ошибка при получении треков из ВКонтакте.")

                for i in current_playlist:
                    try:
                        track_artist = i['artist']
                        track_title = i['title']
                        self.tracks.append((track_artist, track_title))
                    except KeyError as e:
                        logging.error(f"Ошибка в структуре данных трека ВКонтакте: {e}")
                        continue  # Пропускаем трек с ошибкой
                    except Exception as e:
                        logging.error(f"Неизвестная ошибка при обработке трека ВКонтакте: {e}")
                        continue  # Пропускаем трек, если произошла непредвиденная ошибка
                break
        else:
            logging.error(f"Плейлист с именем '{name}' не найден в ВКонтакте.")
            raise ValueError(f"Плейлист с именем '{name}' не найден в ВКонтакте.")

