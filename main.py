import sqlite3
import mutagen
import pytube
from pytube import YouTube, Playlist
import re

PLAYLIST_URL_FORMAT = "https://youtube.com/playlist?list={id_}"

FILENAME_FORMAT = "'[' || SUBSTR('00000' || CAST({num} AS TEXT), -5, 5) || ']' || ' ' || {title} || '.mp4'"


def run():
    db = sqlite3.connect("playlist.db")

    def execute_query(q: str, *args):
        db.cursor().execute(q, tuple(args))
        db.commit()

    def fetch_query(q: str, *args) -> list[tuple[...]]:
        c = db.cursor()
        c.execute(q, tuple(args))
        return c.fetchall()

    execute_query("""
        CREATE TABLE IF NOT EXISTS Env (
            id INTEGER NOT NULL PRIMARY KEY CHECK (id = 0),
            playlist_id TEXT NULL
        )
    """)

    execute_query("""
        INSERT INTO Env(id) VALUES(0)
    """)

    execute_query("""
        CREATE TABLE IF NOT EXISTS Playlist (
            num INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            vid_id CHAR(11) NOT NULL,
            title NTEXT NULL,
            is_downloaded BOOLEAN NOT NULL DEFAULT FALSE,
            is_available BOOLEAN NULL
        );
    """)

    execute_query(f"""
        CREATE VIEW IF NOT EXISTS PlaylistExpanded AS
        SELECT
            *, 
            {FILENAME_FORMAT.format(num="num", title="title")} AS song_file_name 
        FROM Playlist;
    """)

    playlist_id = fetch_query("""
        SELECT playlist_id FROM Env
    """)[0][0]

    if playlist_id is None:
        while True:
            entry = input("Enter YouTube playlist URL: ")

            match = re.match(r"(https:\/\/)?(youtube.com\/playlist\?list=)?(.*)", entry)
            new_id = match[3]

            try:
                pytube.Playlist(PLAYLIST_URL_FORMAT.format(id_=new_id))
                break
            except KeyError:
                print("Could not find playlist.")

        execute_query("""
            UPDATE Env SET playlist_id = ?
        """, new_id)

        playlist_id = fetch_query("""
            SELECT playlist_id FROM Env
        """)[0][0]




if __name__ == "__main__":
    run()
