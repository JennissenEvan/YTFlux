import sqlite3
import mutagen
from pytube import YouTube, Playlist


FILENAME_FORMAT = "'[' || SUBSTR('00000' || CAST({num} AS TEXT), -5, 5) || ']' || ' ' || {title} || '.mp4'"


def run():
    db = sqlite3.connect("playlist.db")

    def execute_query(q: str):
        db.cursor().execute(q)
        db.commit()

    def fetch_query(q: str) -> list[tuple[...]]:
        c = db.cursor()
        c.execute(q)
        return c.fetchall()

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


if __name__ == "__main__":
    run()
