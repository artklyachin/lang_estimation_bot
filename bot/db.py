import aiosqlite

DB_PATH = "/data/db.sqlite3"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS speech_results (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id               INTEGER NOT NULL,
                username              TEXT,
                speech_rate_wpm       REAL NOT NULL,
                filler_words_total    INTEGER NOT NULL,
                filler_words_per_min  REAL NOT NULL,
                pauses_per_min        REAL NOT NULL,
                pauses_avg_duration   REAL NOT NULL,
                full_report           TEXT,
                taken_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            await db.execute("ALTER TABLE speech_results ADD COLUMN username TEXT")
        except Exception:
            pass
        await db.commit()


async def save_speech_result(user_id: int, metrics: dict, full_report: str = "", username: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO speech_results
               (user_id, username, speech_rate_wpm, filler_words_total, filler_words_per_min,
                pauses_per_min, pauses_avg_duration, full_report)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                username,
                metrics["speech_rate_wpm"],
                metrics["filler_words"]["total"],
                metrics["filler_words_per_minute"],
                metrics["long_pauses"]["per_minute"],
                metrics["long_pauses"]["avg_duration"],
                full_report,
            ),
        )
        await db.commit()


async def get_daily_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT COUNT(*) FROM speech_results
               WHERE user_id = ? AND DATE(taken_at) = DATE('now')""",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_last_full_report(user_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT full_report FROM speech_results WHERE user_id = ? ORDER BY taken_at DESC LIMIT 1",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_speech_avg(user_id: int, last_n: int = 5) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT AVG(speech_rate_wpm), AVG(filler_words_total),
                      AVG(filler_words_per_min), AVG(pauses_per_min),
                      AVG(pauses_avg_duration), COUNT(*)
               FROM (
                   SELECT * FROM speech_results
                   WHERE user_id = ?
                   ORDER BY taken_at DESC
                   LIMIT ?
               )""",
            (user_id, last_n),
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row[5] == 0:
                return None
            return {
                "speech_rate_wpm":      round(row[0], 1),
                "filler_words_total":   round(row[1], 1),
                "filler_words_per_min": round(row[2], 1),
                "pauses_per_min":       round(row[3], 2),
                "pauses_avg_duration":  round(row[4], 2),
                "count":                row[5],
            }


