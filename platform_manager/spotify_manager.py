import logging
from config import SPOTIFY_REDIRECT_URI, SPOTIFY_APP_ID, SPOTIFY_SECRET_KEY
import os
import spotipy
from spotipy import SpotifyOAuth, SpotifyOauthError
from spotipy.exceptions import SpotifyException

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTH_URL = "https://accounts.spotify.com/authorize"
API_BASE_URL = "https://api.spotify.com/v1"


def get_auth_url():
    """Генерируем URL для авторизации пользователя через Implicit Grant Flow."""
    scope = 'playlist-read-collaborative playlist-read-private playlist-modify-public playlist-modify-private'
    try:
        auth_spotify = SpotifyOAuth(client_id=SPOTIFY_APP_ID,
                                    client_secret=SPOTIFY_SECRET_KEY,
                                    redirect_uri=SPOTIFY_REDIRECT_URI,
                                    scope=scope,
                                    cache_handler=spotipy.cache_handler.CacheFileHandler(cache_path=".spotifycache"))
        return auth_spotify
    except Exception as e:
        logger.error(f"Ошибка при генерации URL авторизации: {e}")
        raise Exception("Ошибка при генерации URL авторизации.")


def save_token(code, auth_spotify):
    try:
        token_info = auth_spotify.get_access_token(code)
        return token_info
    except SpotifyOauthError as e:
        logger.error(f"Ошибка при получении токена: {e}")
        return False
    except Exception as e:
        logger.error(f"Неизвестная ошибка при получении токена: {e}")
        return False


def logout():
    try:
        os.remove(".spotifycache")
        logger.info("Successfully logged out.")
    except FileNotFoundError:
        logger.warning("No cache file found. Already logged out.")
    except Exception as e:
        logger.error(f"Ошибка при выходе из аккаунта: {e}")


def get_playlists(spotify_user):
    try:
        user_data = spotify_user.current_user()
        playlists = spotify_user.user_playlists(user_data['id'])['items']
        return False, playlists
    except SpotifyException as e:
        logger.error(f"Ошибка при получении плейлистов из Spotify API: {e}")
        return True, []
    except Exception as e:
        logger.error(f"Неизвестная ошибка при получении плейлистов: {e}")
        return True, []


def new_playlist(playlist, spotify_user):
    query = [f"{artist} - {name}" for artist, name in playlist.tracks]
    playlist_name = f"{playlist.name} from {playlist.platform}"
    try:
        user_info = spotify_user.current_user()
    except SpotifyException as e:
        logger.error(f"Ошибка при получении данных пользователя: {e}")
        raise Exception("Ошибка при получении данных пользователя.")

    uris = []
    needed_id = None
    for i in query:
        try:
            ur = spotify_user.search(i)['tracks']['items'][0]['uri']
            uris.append(ur)
        except IndexError:
            logger.warning(f"Трек не найден: {i}")
        except SpotifyException as e:
            logger.error(f"Ошибка при поиске трека '{i}' в Spotify: {e}")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при поиске трека '{i}': {e}")

    if len(uris) >= 100:
        uris = uris[:100]
    try:
        playlist_obj = spotify_user.user_playlist_create(user_info['id'], name=playlist_name)
        needed_id = playlist_obj['id']
        spotify_user.playlist_add_items(playlist_id=needed_id, items=uris)
    except SpotifyException as e:
        logger.error(f"Ошибка при создании или добавлении треков в плейлист: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при создании нового плейлиста: {e}")