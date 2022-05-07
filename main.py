import sqlite3
from mutagen.mp4 import MP4
from pytube import YouTube, Playlist
from pytube.exceptions import VideoUnavailable, VideoPrivate
import re
import os

PLAYLIST_URL_FORMAT = "https://youtube.com/playlist?list={id_}"
VIDEO_URL_FORMAT = "https://www.youtube.com/watch?v={id_}"

FILENAME_FORMAT = "'[' || SUBSTR('00000' || CAST({num} AS TEXT), -5, 5) || ']' || ' ' || {title} || '.mp4'"


def is_available(vid: YouTube):
    try:
        vid.check_availability()
    except (VideoUnavailable, VideoPrivate) as e:
        return False

    return True


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
        INSERT OR IGNORE INTO Env(id) VALUES(0)
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
                pl = Playlist(PLAYLIST_URL_FORMAT.format(id_=new_id))
                pl.title
                break
            except KeyError:
                print("Error: Could not find the entered playlist ID/URL.")

        execute_query("""
            UPDATE Env SET playlist_id = ?
        """, new_id)

        playlist_id = fetch_query("""
            SELECT playlist_id FROM Env
        """)[0][0]

    def update_availability(vid: YouTube):
        availabe = is_available(vid)

        execute_query("""
            UPDATE Playlist
            SET is_available = ?
            WHERE vid_id = ?
        """, 1 if availabe else 0, vid.video_id)

        return availabe

    def download(vid_id: str):
        if not os.path.isdir("music"):
            os.mkdir("music")

        vid = YouTube(VIDEO_URL_FORMAT.format(id_=vid_id), use_oauth=True)

        filename = fetch_query("""
            SELECT song_file_name
            FROM PlaylistExpanded
            WHERE vid_id = ?
        """, vid_id)[0][0]

        file_path = vid.streams.get_audio_only().download("music", filename)

        mp4 = MP4(file_path)

        if mp4.tags is None:
            mp4.add_tags()

        mp4["\xa9nam"] = vid.title
        mp4["\xa9ART"] = vid.author
        mp4["desc"] = vid.description
        mp4["purl"] = vid.watch_url
        # TODO: cover art

    playlist = Playlist(PLAYLIST_URL_FORMAT.format(id_=playlist_id))


if __name__ == "__main__":
    run()
