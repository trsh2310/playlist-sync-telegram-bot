import sqlite3

class Database:
    def __init__(self, db_path='database.db'):
        self.connection = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    vk_token TEXT,
                    spotify_token TEXT,
                    yandex_token TEXT,
                    zvook_token TEXT
                )
            """)
            self.connection.execute("""
                        CREATE TABLE IF NOT EXISTS playlists (
                            user_id INTEGER,
                            track_id TEXT,
                            artist TEXT,
                            title TEXT,
                            platform TEXT,
                            FOREIGN KEY(user_id) REFERENCES users(user_id)
                        )
                    """)

    def save_token(self, user_id, platform, token):
        with self.connection:
            self.connection.execute(f"""
                INSERT INTO users (user_id, {platform}_token)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET {platform}_token = excluded.{platform}_token
            """, (user_id, token))

    def get_token(self, user_id, platform):
        with self.connection:
            result = self.connection.execute(f"""
                SELECT {platform}_token FROM users WHERE user_id = ?
            """, (user_id,)).fetchone()
        return result[0] if result else None

    def get_tracks(self, user_id, platform):
        with self.connection:
            result = self.connection.execute("""
                SELECT track_id, artist, title
                FROM playlists
                WHERE user_id = ? AND platform = ?
            """, (user_id, platform)).fetchall()
        return [{'track_id': row[0], 'artist': row[1], 'title': row[2]} for row in result]

    def save_tracks(self, user_id, tracks, platform):
        with self.connection:
            self.connection.executemany("""
                INSERT INTO playlists (user_id, track_id, artist, title, platform)
                VALUES (?, ?, ?, ?, ?)
            """, [(user_id, track['track_id'], track['artist'], track['title'], platform) for track in tracks])

