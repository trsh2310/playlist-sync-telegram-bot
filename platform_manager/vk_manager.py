import logging
from vk_api.audio import VkAudio
from vk_api.exceptions import VkApiError

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class VKMusicManager:
    def __init__(self, session):
        self.session = session
        self.api = session.get_api()
        self.audio = VkAudio(session)

    def get_playlists(self):
        try:
            user_id = self.session.get_api().users.get()[0]['id']
            playlists = self.audio.get_albums(user_id)
            if not playlists:
                logger.warning("Плейлисты не найдены для пользователя.")
            return playlists
        except VkApiError as e:
            logger.error(f"Ошибка при взаимодействии с VK API: {e}")
            return []
        except KeyError as e:
            logger.error(f"Ошибка при получении данных пользователя: {e}")
            return []
        except Exception as e:
            logger.exception(f"Неизвестная ошибка при получении плейлистов: {e}")
            return []