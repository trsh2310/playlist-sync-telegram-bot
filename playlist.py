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

        # Присваиваем имя и платформу
        self.name = ""
        self.platform = "Spotify"

        # Собираем список песен
        self.tracks = self.get_playlist_tracks(current_playlist)
        print (self.tracks)

    # Получаем список треков в формате "artist - track name"
    from typing import List, Tuple

    def get_playlist_tracks(self, current_playlist) -> List[Tuple[str, str]]:
        playlist_with_items = []
        for pl in current_playlist['items']:
            try:
                # Собираем список артистов
                artists = ", ".join([artist['name'] for artist in pl['track']['artists']])
                track_name = pl['track']['name']

                # Добавляем кортеж (артисты, название трека) в список
                playlist_with_items.append((artists, track_name))
            except KeyError as e:
                logging.error(f"Ошибка в структуре данных трека: {e}")
                continue  # Пропускаем трек, если есть ошибка в данных
            except Exception as e:
                logging.error(f"Неизвестная ошибка при обработке трека: {e}")
                continue  # Пропускаем трек, если произошла непредвиденная ошибка
        return playlist_with_items

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

    def extract_yandex_album_id(url: str) -> str:
        """
        Извлекает идентификатор альбома из ссылки на Яндекс.Музыку.

        :param url: Строка с URL альбома на Яндекс.Музыке
        :return: Идентификатор альбома (строка) или None, если идентификатор не найден
        """
        pattern = r"https://music\.yandex\.ru/album/(\d+)"
        match = re.match(pattern, url)
        if match:
            return match.group(1)
        else:
            return None
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

