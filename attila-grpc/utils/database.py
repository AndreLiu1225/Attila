import os

import psycopg2
from psycopg2.extras import RealDictCursor

from roles.role import Role

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            dbname=os.environ.get("DB_NAME", "attila"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD"),
        )

    def get_cursor(self):
        return self.conn.cursor(cursor_factory=RealDictCursor)

    def save_message(self, conversation_id, sender, content,):
        if isinstance(sender, Role):
            sender = sender.value
        try:
            with self.get_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (conversation_id, sender, content)
                    VALUES (%s, %s, %s)
                    RETURNING id, conversation_id, sender, content, created_at
                    """,
                    (conversation_id, sender, content,),
                )
                row = cur.fetchone()
            self.conn.commit()
            return row
        
        except Exception:
            self.conn.rollback()
            raise

    def list_messages(self, conversation_id):
        with self.get_cursor() as cur:
            cur.execute(
                """
                SELECT id, sender, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at, id
                """,
                (conversation_id,),
            )
            return cur.fetchall()

    def ensure_conversation(self, user_id, conversation_id):
            with self.get_cursor() as cur:
                cur.execute(
                    "INSERT INTO users (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
                    (user_id,),
                )
                cur.execute(
                    """
                    INSERT INTO conversations (id, user_id)
                    VALUES (%s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (conversation_id, user_id,),
                )
            self.conn.commit()