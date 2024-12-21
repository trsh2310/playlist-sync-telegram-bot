import os
import re
import requests
import logging
from urllib.parse import urlencode
from config import SPOTIFY_REDIRECT_URI, SPOTIFY_APP_ID, SPOTIFY_SECRET_KEY
from models import Database

import spotipy
from spotipy import SpotifyOAuth, SpotifyOauthError

logging.basicConfig(level=logging.INFO)

class SpotifyManager:

    AUTH_URL = "https://accounts.spotify.com/authorize"
    API_BASE_URL = "https://api.spotify.com/v1"

    def logout(self):
        try:
            os.remove(".spotifycache")
            print("Successfully logged out.")
        except FileNotFoundError:
            print("No cache file found. Already logged out.")

    def get_auth_url(self):
        """
        Генерируем URL для авторизации пользователя через Implicit Grant Flow.
        """
        scope = 'playlist-read-collaborative playlist-read-private playlist-modify-public playlist-modify-private'

        auth_spotify = SpotifyOAuth(client_id=SPOTIFY_APP_ID,
                                    client_secret=SPOTIFY_SECRET_KEY,
                                    redirect_uri=SPOTIFY_REDIRECT_URI,
                                    scope=scope,
                                    cache_handler=spotipy.cache_handler.CacheFileHandler(cache_path=".spotifycache"))
        return auth_spotify

    def save_token(self, user_id, token, auth_spotify):
        try:
            token_info = auth_spotify.get_access_token(token)
            return token_info
        except SpotifyOauthError:
            return False




    def get_playlists(self,playlist_name, sp):
        """Получает доступ ко всем песням из плейлиста в медиатеке пользователя по его названию"""
        needed_playlist = None
        user = sp.current_user()
        current_playlists = sp.user_playlists(user['id'])['items']

        playlist_with_items = []
        for playlist in current_playlists:
            if playlist['name'] == playlist_name:
                needed_playlist = playlist

                break

        for pl in sp.playlist_items(needed_playlist['id'])['items']:
            sing = ''
            for i in range(len(pl['track']['artists'])):
                sing += pl['track']['artists'][i]['name']
                if i != len(pl['track']['artists']) - 1:
                    sing += ', '
            playlist_with_items.append(
                sing + ' - ' + pl['track']['name'])
        return playlist_with_items





    def parser(self,link: str) -> str:
        """Парсит ссылку и извлекает уникальный ID плейлиста"""
        pattern = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
        match = re.match(pattern, link)

        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid link or playlist ID not found")


    def get_playlist_by_url(self,pl_id, sp):
        """

        :param pl_id: уникальный айди плейлиста, полученный после парсинга ссылки
        :param sp: объект класса Spootify, через который и производится доступ к аккаунт юзера
        :return: все песни из плейлиста под уникальным номером pl_id
        """
        current_playlist = sp.playlist_items(pl_id)
        playlist_with_items = []
        for pl in current_playlist['items']:
            sing = ''
            for i in range(len(pl['track']['artists'])):
                sing += pl['track']['artists'][i]['name']
                if i != len(pl['track']['artists']) - 1:
                    sing += ', '
            playlist_with_items.append(
                sing + ' - ' + pl['track']['name'])
        return playlist_with_items


    def search_create_add(self, query: list, wanted_name, sp):
        """
        Функция ищет песню(а точнее ее уникальный uri код) и добавляет в плейлист с заданным названием

        :param query: список песен на добавление
        :param wanted_name: имя нового плейлиста
        :param sp:объект класса Spootify, через который и производится доступ к аккаунт юзера
        :return: новый плейлист будет добавлен в медиатеку
        """
        user_info = sp.current_user()
        uris = []
        needed_id = None
        for i in query:
            try:
                ur = sp.search(i)['tracks']['items'][0]['uri']
                uris.append(ur)
            except:
                continue
        if len(uris) >= 100:
            uris = uris[:100]
        sp.user_playlist_create(user_info['id'], name=wanted_name)
        for playlist in sp.current_user_playlists()['items']:
            if (playlist['name'] == wanted_name):
                needed_id = playlist['id']
        sp.playlist_add_items(playlist_id=needed_id, items=uris)