import asyncpg
import os

SQL_URL = os.environ.get("SQLALCHEMY_DATABASE_URI")


async def update_record_driveurl(record, url):
    conn = await asyncpg.connect(SQL_URL)
    await conn.execute(
        """
      UPDATE records
      SET drive_file_url = $1
      WHERE id = $2""",
        url,
        record.id,
    )
    await conn.close()
