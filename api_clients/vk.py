import vk_api

class VKClient:
    def __init__(self, token):
        self.vk_session = vk_api.VkApi(token=token)
        self.api = self.vk_session.get_api()

    def fetch_playlist(self, playlist_url):
        playlist_id = playlist_url.split('_')[-1]
        owner_id = playlist_url.split('_')[-2].split('/')[-1]
        response = self.api.audio.getPlaylist(owner_id=owner_id, playlist_id=playlist_id)
        return response['response']['items']

    def create_playlist(self, title, description):
        return self.api.audio.addPlaylist(title=title, description=description)

    def add_tracks_to_playlist(self, playlist_id, owner_id, track_ids):
        for track_id in track_ids:
            self.api.audio.addToPlaylist(owner_id=owner_id, playlist_id=playlist_id, audio_ids=[track_id])
