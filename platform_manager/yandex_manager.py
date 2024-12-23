import logging
from yandex_music import Client
from yandex_music.exceptions import UnauthorizedError, YandexMusicError

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def instruct():
    reg_link = 'https://chromewebstore.google.com/detail/yandex-music-token/lcbjeookjibfhjjopieifgjnhlegmkib'
    instruction = (f"Чтобы зайти в свой аккаунт Yandex Music, выполни следующие действия: \n"
                    f"1. Установи расширение в Google Chrome по  [ссылке] ({reg_link}) \n" +
                    "2. Залогинься в свой аккаунт Яндекса через расширение \n"
                    "3. Оно автоматически направит в заблокированного бота, просто закрой его \n"
                    "4. Нажми на иконку расширения в браузере, снизу слева у появившегося окна есть кнопка 'Скопировать токен' \n"
                    "5. Ответным сообщением отправь токен")
    return instruction


def new_playlist(playlist, yandex_user, token):
    query = playlist.tracks
    playlist_name = f"{playlist.name} from {playlist.platform}"

    try:
        yandex_playlist = yandex_user.users_playlists_create(playlist_name, visibility='private', user_id=token)
    except UnauthorizedError:
        logger.error("Ошибка авторизации. Проверьте токен для Yandex Music.")
        raise UnauthorizedError("Ошибка авторизации. Проверьте токен.")
    except YandexMusicError as e:
        logger.error(f"Ошибка при создании плейлиста в Yandex Music: {e}")
        raise YandexMusicError("Ошибка при создании плейлиста в Yandex Music.")
    except Exception as e:
        logger.exception(f"Неизвестная ошибка при создании плейлиста: {e}")
        raise Exception("Не удалось создать плейлист в Yandex Music.")

    not_found = []
    j = 1

    for artist, title in query:
        name = f"{artist} - {title}"
        try:
            best_search = yandex_user.search(name).best.result
            best_search_artists = ', '.join([artist.name for artist in best_search.artists])

            if best_search.title == title and best_search_artists == artist:
                try:
                    yandex_user.users_playlists_insert_track(yandex_playlist.kind, best_search.id,
                                                             best_search.albums[0].id, revision=j)
                    j += 1
                except YandexMusicError as e:
                    logger.error(f"Ошибка при добавлении трека '{name}' в плейлист: {e}")
                    not_found.append(name)
                except Exception as e:
                    logger.exception(f"Неизвестная ошибка при добавлении трека '{name}' в плейлист: {e}")
                    not_found.append(name)
            else:
                not_found.append(name)
        except YandexMusicError as e:
            logger.error(f"Ошибка при поиске трека '{name}': {e}")
            not_found.append(name)
        except Exception as e:
            logger.exception(f"Неизвестная ошибка при обработке трека '{name}': {e}")
            not_found.append(name)

    if not_found:
        logger.warning(f"Не удалось найти или добавить следующие треки в плейлист: {', '.join(not_found)}")

    return not_found