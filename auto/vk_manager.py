import logging
logger = logging.getLogger(__name__)

class VKMusicManager:
    def __init__(self, vk_session):
        self.vk_session = vk_session
        self.vk = vk_session.get_api()

    def list_playlists(self):
        try:
            response = self.vk.audio.getPlaylists()
            playlists = response.get('items', [])
            return [(playlist['title'], playlist['id']) for playlist in playlists]
        except Exception as e:
            logger.error(f"Error fetching playlists: {e}")
            return []

    def list_songs_in_playlist(self, owner_id, playlist_id):
        try:
            response = self.vk.audio.get(owner_id=owner_id, album_id=playlist_id)
            songs = response.get('items', [])
            return [(song['title'], song['artist']) for song in songs]
        except Exception as e:
            logger.error(f"Error fetching songs: {e}")
            return []