import unittest
from unittest.mock import MagicMock

from spotipy import SpotifyException
from vk_api import VkApiError

from platform_manager.spotify_manager import get_playlists, new_playlist
from platform_manager.vk_manager import VKMusicManager
from playlist import Playlist


class TestPlaylist(unittest.TestCase):
    def setUp(self):
        self.playlist = Playlist()

    def test_spotify_url_parser_valid(self):
        url = "https://open.spotify.com/playlist/1234567890abcdef"
        expected = "1234567890abcdef"
        self.assertEqual(self.playlist.spotify_url_parser(url), expected)

    def test_spotify_url_parser_invalid(self):
        url = "https://example.com/playlist/invalid"
        with self.assertRaises(ValueError):
            self.playlist.spotify_url_parser(url)

    def test_yandex_url_parser_valid(self):
        url = "https://music.yandex.ru/users/test_user/playlists/12345"
        expected = ("test_user", "12345")
        self.assertEqual(self.playlist.yandex_url_parser(url), expected)

    def test_yandex_url_parser_invalid(self):
        url = "https://example.com/playlists/invalid"
        with self.assertRaises(ValueError):
            self.playlist.yandex_url_parser(url)

    def test_get_playlist_tracks(self):
        mock_playlist = {
            'items': [
                {
                    'track': {
                        'name': 'Test Track',
                        'artists': [{'name': 'Test Artist'}]
                    }
                }
            ]
        }
        expected = [('Test Artist', 'Test Track')]
        self.assertEqual(self.playlist.get_playlist_tracks(mock_playlist), expected)


class TestSpotifyFunctions(unittest.TestCase):
    def setUp(self):
        self.mock_spotify_user = MagicMock()

    def test_get_playlists_success(self):
        self.mock_spotify_user.current_user.return_value = {'id': 'test_user'}
        self.mock_spotify_user.user_playlists.return_value = {'items': [{'name': 'Test Playlist'}]}
        error, playlists = get_playlists(self.mock_spotify_user)
        self.assertFalse(error)
        self.assertEqual(playlists, [{'name': 'Test Playlist'}])

    def test_new_playlist_creation(self):
        playlist_mock = MagicMock()
        playlist_mock.name = "Test Playlist"
        playlist_mock.platform = "Spotify"
        playlist_mock.tracks = [("Test Artist", "Test Track")]

        self.mock_spotify_user.current_user.return_value = {'id': 'test_user'}
        self.mock_spotify_user.search.return_value = {
            'tracks': {'items': [{'uri': 'test_uri'}]}
        }
        self.mock_spotify_user.user_playlist_create.return_value = {'id': 'new_playlist_id'}
        new_playlist(playlist_mock, self.mock_spotify_user)
        self.mock_spotify_user.playlist_add_items.assert_called_once_with(
            playlist_id='new_playlist_id', items=['test_uri']
        )