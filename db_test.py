import pytest
import sqlite3
from models import Database

from unittest.mock import MagicMock, patch
from platform_manager.spotify_manager import SpotifySync
from platform_manager.vk_manager import VKSync

@pytest.fixture
def mock_database():
    return MagicMock()

@pytest.fixture
def spotify_sync(mock_database):
    return SpotifySync(database=mock_database)

@pytest.fixture
def vk_sync():
    vk_sync_instance = VKSync()
    vk_sync_instance.db = MagicMock()  # Мокируем базу данных
    return vk_sync_instance

@pytest.fixture
def test_db():
    connection = sqlite3.connect(":memory:")
    database = Database(db_path=":memory:")
    yield database
    connection.close()

def test_create_tables(test_db):
    cursor = test_db.connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "users" in tables, "Таблица users должна быть создана."
    assert "playlists" in tables, "Таблица playlists должна быть создана."

def test_save_token(test_db):
    user_id = 1
    platform = "spotify"
    token = "sample_token"
    test_db.save_token(user_id, platform, token)
    saved_token = test_db.get_token(user_id, platform)
    assert saved_token == token, "Token должен сохраняться и быть доступным."

def test_save_and_get_tracks(test_db):
    user_id = 1
    tracks = [
        {"track_id": "1", "artist": "Artist 1", "title": "Track 1"},
        {"track_id": "2", "artist": "Artist 2", "title": "Track 2"}
    ]
    platform = "spotify"
    test_db.save_tracks(user_id, tracks, platform)
    saved_tracks = test_db.get_tracks(user_id, platform)
    assert len(saved_tracks) == len(tracks), "Количество сохраненных треков должно совпадать."
    for track, saved_track in zip(tracks, saved_tracks):
        assert track == saved_track, "Данные треков должны совпадать."

#спотик
def test_save_token_to_database_spotify():
    mock_db = MagicMock()
    spotify_sync = SpotifySync(database=mock_db)
    user_id = 1
    token = "test_spotify_token"
    spotify_sync.save_token(user_id, token)
    mock_db.save_token.assert_called_once_with(user_id, "spotify", token)

def test_get_user_playlists_error_handling_spotify():
    mock_db = MagicMock()
    mock_db.get_token.return_value = None
    spotify_sync = SpotifySync(database=mock_db)
    with pytest.raises(ValueError, match="Spotify token not found for user."):
        spotify_sync.get_user_playlists(1)

def test_get_auth_url_spotify(spotify_sync):
    user_id = 1
    expected_url_fragment = "response_type=token"
    auth_url = spotify_sync.get_auth_url(user_id)
    assert "response_type=token" in auth_url, "URL авторизации должен содержать 'response_type=token'."
    assert f"state={user_id}" in auth_url, "URL авторизации должен содержать правильный user_id."

def test_save_token_spotify(spotify_sync, mock_database):
    user_id = 1
    token = "test_token"
    spotify_sync.save_token(user_id, token)
    mock_database.save_token.assert_called_once_with(user_id, "spotify", token)

#вк
def test_save_token_vk():
    mock_db = MagicMock()
    vk_sync = VKSync()
    vk_sync.db = mock_db
    user_id = 1
    token_url = "https://oauth.vk.com/blank.html#access_token=test_token&expires_in=86400&user_id=123"
    vk_sync.vk_save_token(user_id, "vk", token_url)
    mock_db.save_token.assert_called_once_with(user_id, "vk", "test_token")

def test_get_auth_url_vk(vk_sync):
    auth_url = vk_sync.get_auth_url("vk")
    assert "https://oauth.vk.com/authorize" in auth_url, "URL авторизации должен быть корректным."
    assert "scope=audio,offline" in auth_url, "URL должен содержать scope=audio,offline."
