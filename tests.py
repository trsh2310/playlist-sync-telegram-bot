import unittest
from unittest.mock import MagicMock, patch
from playlist import Playlist, VKMusicManager  # Импортируйте ваши классы из реального модуля
from yandex_music import Client
class TestPlaylistMethods(unittest.TestCase):

    def test_spotify_url_parser_valid_url(self):
        playlist_url = "https://open.spotify.com/playlist/123abc"
        playlist = Playlist()
        uri = playlist.spotify_url_parser(playlist_url)
        self.assertEqual(uri, "123abc")

    def test_spotify_url_parser_invalid_url(self):
        playlist_url = "https://invalid.spotify.com/playlist/123abc"
        playlist = Playlist()
        with self.assertRaises(ValueError):
            playlist.spotify_url_parser(playlist_url)

    @patch('playlist.SpotifyUser')  # Мокаем объект пользователя Spotify
    def test_from_spotify_valid(self, MockSpotifyUser):
        spotify_user = MockSpotifyUser()
        playlist_url = "https://open.spotify.com/playlist/123abc"

        # Мокаем возвращаемые данные для теста
        mock_playlist = {
            'name': 'Test Playlist',
            'items': [
                {'track': {'name': 'Track1', 'artists': ['Artist1']}},
                {'track': {'name': 'Track2', 'artists': ['Artist2']}},
            ]
        }
        spotify_user.playlist_items = MagicMock(return_value=mock_playlist)

        playlist = Playlist()
        playlist.from_spotify(playlist_url, spotify_user)

        self.assertEqual(playlist.name, 'Test Playlist')
        self.assertEqual(len(playlist.tracks), 2)
        self.assertEqual(playlist.tracks[0], ('Artist1', 'Track1'))
        self.assertEqual(playlist.tracks[1], ('Artist2', 'Track2'))

    @patch('playlist.YandexUser')  # Мокаем объект пользователя Yandex
    def test_from_yandex_valid(self, MockYandexUser):
        yandex_user = MockYandexUser()
        playlist_url = "https://music.yandex.ru/users/user123/playlists/12345"

        # Мокаем возвращаемые данные для теста
        mock_playlist = MagicMock()
        mock_playlist.title = 'Test Playlist'
        mock_playlist.tracks = [
            MagicMock(track=MagicMock(artists=[MagicMock(name='Artist1')], title='Track1')),
            MagicMock(track=MagicMock(artists=[MagicMock(name='Artist2')], title='Track2'))
        ]
        yandex_user.users_playlists = MagicMock(return_value=mock_playlist)

        playlist = Playlist()
        playlist.from_yandex(playlist_url, yandex_user)

        self.assertEqual(playlist.name, 'Test Playlist')
        self.assertEqual(len(playlist.tracks), 2)
        self.assertEqual(playlist.tracks[0], ('Artist1', 'Track1'))
        self.assertEqual(playlist.tracks[1], ('Artist2', 'Track2'))

    @patch('playlist_module.VKMusicManager')  # Мокаем объект пользователя ВКонтакте
    def test_from_vk_valid(self, MockVKUser):
        vk_user = MockVKUser()
        playlist_name = "Test Playlist"

        # Мокаем возвращаемые данные для теста
        mock_playlists = [
            {'title': 'Test Playlist', 'owner_id': 123, 'id': 456},
        ]
        vk_user.get_playlists = MagicMock(return_value=mock_playlists)
        vk_user.audio.get = MagicMock(return_value=[
            {'artist': 'Artist1', 'title': 'Track1'},
            {'artist': 'Artist2', 'title': 'Track2'},
        ])

        playlist = Playlist()
        playlist.from_vk(playlist_name, vk_user)

        self.assertEqual(playlist.name, 'Test Playlist')
        self.assertEqual(len(playlist.tracks), 2)
        self.assertEqual(playlist.tracks[0], ('Artist1', 'Track1'))
        self.assertEqual(playlist.tracks[1], ('Artist2', 'Track2'))

    def test_yandex_url_parser_valid(self):
        url = "https://music.yandex.ru/users/user123/playlists/12345"
        user_id, playlist_id = Playlist.yandex_url_parser(url)
        self.assertEqual(user_id, "user123")
        self.assertEqual(playlist_id, "12345")

    def test_yandex_url_parser_invalid(self):
        url = "https://music.yandex.com/invalid/url"
        with self.assertRaises(ValueError):
            Playlist.yandex_url_parser(url)


if __name__ == '__main__':
    unittest.main()
