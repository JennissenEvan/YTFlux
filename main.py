import sqlite3
import mutagen
from pytube import YouTube, Playlist


def run():
    db = sqlite3.connect("playlist.db")

    def execute_query(q: str):
        db.cursor().execute(q)
        db.commit()

    def fetch_query(q: str) -> list[tuple[...]]:
        c = db.cursor()
        c.execute(q)
        return c.fetchall()


if __name__ == "__main__":
    run()
