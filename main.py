import sqlite3
from mutagen.mp4 import MP4, MP4Cover
from pytube import YouTube, Playlist
from pytube.exceptions import VideoUnavailable, VideoPrivate
import re
import os
import requests
from PIL import Image
import io

CURRENT_VER = "100"

MUSIC_PATH = "music"

PLAYLIST_URL_FORMAT = "https://youtube.com/playlist?list={id_}"
VIDEO_URL_FORMAT = "https://www.youtube.com/watch?v={id_}"


def is_available(vid: YouTube):
    try:
        vid.check_availability()
    except (VideoUnavailable, VideoPrivate) as e:
        return False

    return True


def run():
    if not os.path.isdir(MUSIC_PATH):
        os.mkdir(MUSIC_PATH)

    db = sqlite3.connect("playlist.db")

    def execute_query(q: str, *args):
        db.cursor().execute(q, tuple(args))
        db.commit()

    def fetch_query(q: str, *args) -> list[tuple[...]]:
        c = db.cursor()
        c.execute(q, tuple(args))
        return c.fetchall()

    # Initialize database
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
            is_available BOOLEAN NULL,
            song_file_name NTEXT NULL
        );
    """)

    playlist_id = fetch_query("""
        SELECT playlist_id FROM Env
    """)[0][0]

    # Prompt user for playlist ID/URL if it is not initialized
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

    def label(vid: YouTube):
        return f"{vid.title} ({vid.video_id})"

    # Check if video is available (not deleted or private, etc.) and update video's data
    def update_availability(vid: YouTube):
        availabe = is_available(vid)

        execute_query("""
            UPDATE Playlist
            SET is_available = ?
            WHERE vid_id = ?
        """, 1 if availabe else 0, vid.video_id)

        return availabe

    # Download .mp4 audio file of given video ID and attach metadata, then update file name in database
    def download(vid_id: str):
        vid = YouTube(VIDEO_URL_FORMAT.format(id_=vid_id), use_oauth=True)

        vid_num = fetch_query("""
            SELECT num
            FROM Playlist
            WHERE vid_id = ?
        """, vid_id)[0][0]

        print(f"Downloading {label(vid)}...")
        params = {
            "output_path": "music",
            "filename_prefix": f"[{str(vid_num).rjust(5, '0')}]",
            "skip_existing": False
        }
        file_path = vid.streams.get_audio_only().download(**params)

        mp4 = MP4(file_path)

        if mp4.tags is None:
            mp4.add_tags()

        mp4["\xa9nam"] = vid.title
        mp4["\xa9ART"] = vid.author
        mp4["desc"] = vid.description

        # Download thumbnail, convert to PNG for the sake of consistency
        thumbnail_response = requests.get(vid.thumbnail_url)
        thumbnail = Image.open(io.BytesIO(thumbnail_response.content))
        b = io.BytesIO()
        thumbnail.save(b, "PNG")
        b.seek(0)
        # Attach thumbnail image to mp4
        mp4["covr"] = [MP4Cover(b.read(), imageformat=MP4Cover.FORMAT_PNG)]

        mp4["fver"] = "100"

        mp4.save()

        file_name = re.split(r"\\", file_path)[-1]
        execute_query("""
            UPDATE Playlist
            SET song_file_name = ?
            WHERE vid_id = ?
        """, file_name, vid.video_id)

    playlist = Playlist(PLAYLIST_URL_FORMAT.format(id_=playlist_id))
    videos = list(playlist.videos)

    #
    # Phase 1: Add new videos to database
    #
    print("Checking for new videos...")
    total = 0
    for vid in videos:
        if fetch_query("""
            SELECT COUNT(*)
            FROM Playlist
            WHERE vid_id = ?
        """, vid.video_id)[0][0] == 0:
            execute_query("""
                INSERT INTO Playlist (vid_id)
                VALUES(?)
            """, vid.video_id)
            print(f"Added new video {label(vid)}")
            total += 1
    print(f"Added {total} new video(s) to playlist.")

    #
    # Phase 2: Check avalability for all videos
    #
    print("Checking video availability...")
    vid_id_query = fetch_query("""
        SELECT vid_id
        FROM Playlist
        WHERE is_available = TRUE OR is_available IS NULL
    """)
    vid_ids = tuple(qr[0] for qr in vid_id_query)
    total = 0
    for vid_id in vid_ids:
        vid = YouTube(VIDEO_URL_FORMAT.format(id_=vid_id))
        if not update_availability(vid):
            print(f"{label(vid)} no longer available.")
            total += 1
    print(f"Status of {total} video(s) updated to unavailable.")

    #
    # Phase 3: Delete videos not in playlist
    #
    print("Checking for videos removed from playlist...")
    query = """
        SELECT vid_id
        FROM Playlist
        WHERE is_available = TRUE
    """
    playlist_vid_ids = set(v.video_id for v in videos)
    removed_vid_ids = tuple(r[0] for r in fetch_query(query) if r[0] not in playlist_vid_ids)
    for vid_id in removed_vid_ids:
        file_name = fetch_query("""
            SELECT song_file_name
            FROM Playlist
            WHERE vid_id = ?
        """, vid_id)[0][0]

        if file_name is not None:
            file_path = f"{MUSIC_PATH}/{file_name}"
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted {file_name}")

        execute_query("""
            DELETE FROM Playlist
            WHERE vid_id = ?
        """, vid_id)

        vid = YouTube(VIDEO_URL_FORMAT.format(id_=vid_id))
        print(f"Removed {label(vid)} from playlist.")
    print(f"Removed {len(removed_vid_ids)} video(s) from playlist.")

    #
    # Phase 4: Download undownloaded videos
    #
    print("Downloading undownloaded videos...")
    undownloaded_id_query = fetch_query("""
        SELECT vid_id
        FROM Playlist
        WHERE song_file_name IS NULL
    """)
    undownloaded_ids = tuple(qr[0] for qr in undownloaded_id_query)
    total = len(undownloaded_ids)
    for i, vid_id in enumerate(undownloaded_ids):
        download(vid_id)
        print(f"Finished downloading video ({i + 1}/{total})")
    print(f"Downloaded {total} video(s).")

    #
    # Phase 5: Verify integrity
    #
    # TODO


if __name__ == "__main__":
    run()
