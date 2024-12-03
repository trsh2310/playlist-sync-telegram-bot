class VKScraper:
    @staticmethod
    def extract_track_info(track):
        return {
            'artist': track['artist'],
            'title': track['title'],
            'id': track['id']
        }
