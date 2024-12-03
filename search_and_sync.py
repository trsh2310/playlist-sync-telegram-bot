class SearchAndSync:
    @staticmethod
    def search_tracks(api_client, tracks):
        found_tracks = []
        for track in tracks:
            result = api_client.search_track(f"{track['artist']} {track['title']}")
            if result:
                found_tracks.append(result['id'])
        return found_tracks
