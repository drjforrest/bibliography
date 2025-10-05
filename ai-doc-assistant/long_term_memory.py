import sqlite3
from pathlib import Path
from loguru import logger
from datetime import datetime
import json

import config


def save_interaction(question, answer, source_docs=None, metadata=None):
    """Save a question-answer interaction to the database."""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        # Prepare source docs and metadata as JSON strings
        source_docs_json = json.dumps(source_docs) if source_docs else None
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute(
            """
            INSERT INTO log (q, a, source_docs, metadata) 
            VALUES (?, ?, ?, ?)
        """,
            (question, answer, source_docs_json, metadata_json),
        )

        conn.commit()
        conn.close()

        logger.debug(f"Saved interaction to database: {question[:50]}...")

    except Exception as e:
        logger.error(f"Failed to save interaction to database: {e}")


def get_recent_interactions(limit=10):
    """Get recent question-answer interactions."""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT timestamp, q, a, source_docs, metadata 
            FROM log 
            ORDER BY timestamp DESC 
            LIMIT ?
        """,
            (limit,),
        )

        results = []
        for row in cursor.fetchall():
            timestamp, question, answer, source_docs, metadata = row

            # Parse JSON fields
            source_docs_parsed = json.loads(source_docs) if source_docs else []
            metadata_parsed = json.loads(metadata) if metadata else {}

            results.append(
                {
                    "timestamp": timestamp,
                    "question": question,
                    "answer": answer,
                    "source_docs": source_docs_parsed,
                    "metadata": metadata_parsed,
                }
            )

        conn.close()
        return results

    except Exception as e:
        logger.error(f"Failed to retrieve interactions: {e}")
        return []


def get_interaction_count():
    """Get total number of interactions stored."""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM log")
        count = cursor.fetchone()[0]

        conn.close()
        return count

    except Exception as e:
        logger.error(f"Failed to get interaction count: {e}")
        return 0


def search_interactions(query, limit=20):
    """Search interactions by question content."""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT timestamp, q, a, source_docs, metadata 
            FROM log 
            WHERE q LIKE ? OR a LIKE ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """,
            (f"%{query}%", f"%{query}%", limit),
        )

        results = []
        for row in cursor.fetchall():
            timestamp, question, answer, source_docs, metadata = row

            # Parse JSON fields
            source_docs_parsed = json.loads(source_docs) if source_docs else []
            metadata_parsed = json.loads(metadata) if metadata else {}

            results.append(
                {
                    "timestamp": timestamp,
                    "question": question,
                    "answer": answer,
                    "source_docs": source_docs_parsed,
                    "metadata": metadata_parsed,
                }
            )

        conn.close()
        return results

    except Exception as e:
        logger.error(f"Failed to search interactions: {e}")
        return []
