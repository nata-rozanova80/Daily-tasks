import os
import sqlite3
from typing import List, Optional, Iterable, Dict

_DB_PATH = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "ChecklistNotes", "app.db") if os.name == "nt" \
    else os.path.join(os.path.expanduser("~"), ".local", "share", "ChecklistNotes", "app.db")

_conn: Optional[sqlite3.Connection] = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn:
        return _conn
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    _conn = sqlite3.connect(_DB_PATH)
    _conn.row_factory = sqlite3.Row
    init_db(_conn)
    return _conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(r["name"] == column for r in cur.fetchall())


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        checked INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(list_id) REFERENCES lists(id) ON DELETE CASCADE
    );
    """)
    # миграции
    if not _column_exists(conn, "lists", "updated_at"):
        conn.execute("ALTER TABLE lists ADD COLUMN updated_at TIMESTAMP")
        conn.execute("UPDATE lists SET updated_at = created_at WHERE updated_at IS NULL")
    if not _column_exists(conn, "lists", "pinned"):
        conn.execute("ALTER TABLE lists ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
    if not _column_exists(conn, "lists", "archived"):
        conn.execute("ALTER TABLE lists ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
    if not _column_exists(conn, "lists", "color"):
        conn.execute("ALTER TABLE lists ADD COLUMN color TEXT DEFAULT '#ffffff'")
    if not _column_exists(conn, "lists", "deleted_at"):
        conn.execute("ALTER TABLE lists ADD COLUMN deleted_at TIMESTAMP")
    # для текстовых заметок
    if not _column_exists(conn, "lists", "kind"):
        conn.execute("ALTER TABLE lists ADD COLUMN kind TEXT NOT NULL DEFAULT 'checklist'")
    if not _column_exists(conn, "lists", "note_text"):
        conn.execute("ALTER TABLE lists ADD COLUMN note_text TEXT")

    # индексы для ускорения поиска
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lists_title ON lists(title)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lists_note_text ON lists(note_text)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_list_text ON items(list_id, text)")
    conn.commit()


def _touch_updated(list_id: int):
    conn = get_conn()
    conn.execute("UPDATE lists SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (list_id,))
    conn.commit()


def create_list(title: str,
                items: Iterable[str],
                color: str = "#ffffff",
                pinned: bool = False,
                kind: str = "checklist",
                note_text: Optional[str] = None) -> int:
    """
    kind: 'checklist' | 'text'
    Для 'text' – содержимое в note_text.
    """
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO lists (title, color, pinned, archived, kind, note_text, updated_at) "
        "VALUES (?, ?, ?, 0, ?, ?, CURRENT_TIMESTAMP)",
        (title, color, 1 if pinned else 0, kind, note_text)
    )
    list_id = cur.lastrowid
    if kind == "checklist":
        for t in items:
            conn.execute("INSERT INTO items (list_id, text, checked) VALUES (?, ?, 0)", (list_id, t))
    conn.commit()
    return list_id


def add_item(list_id: int, text: str) -> int:
    conn = get_conn()
    cur = conn.execute("INSERT INTO items (list_id, text, checked) VALUES (?, ?, 0)", (list_id, text))
    _touch_updated(list_id)
    return cur.lastrowid


def get_items(list_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.execute("SELECT id, text, checked FROM items WHERE list_id=? ORDER BY id", (list_id,))
    return cur.fetchall()


def set_item_checked(item_id: int, checked: bool) -> None:
    conn = get_conn()
    conn.execute("UPDATE items SET checked=? WHERE id=?", (1 if checked else 0, item_id))
    # touch parent
    cur = conn.execute("SELECT list_id FROM items WHERE id=?", (item_id,))
    row = cur.fetchone()
    if row:
        _touch_updated(row["list_id"])
    conn.commit()


def uncheck_checked_items(list_id: int) -> None:
    conn = get_conn()
    conn.execute("UPDATE items SET checked=0 WHERE list_id=? AND checked=1", (list_id,))
    _touch_updated(list_id)


def set_pinned(list_id: int, pinned: bool) -> None:
    conn = get_conn()
    conn.execute("UPDATE lists SET pinned=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (1 if pinned else 0, list_id))
    conn.commit()


def set_archived(list_id: int, archived: bool) -> None:
    conn = get_conn()
    conn.execute("UPDATE lists SET archived=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (1 if archived else 0, list_id))
    conn.commit()


def soft_delete(list_id: int) -> None:
    conn = get_conn()
    conn.execute("UPDATE lists SET deleted_at=CURRENT_TIMESTAMP WHERE id=?", (list_id,))
    conn.commit()


def get_lists(include_archived: bool = False,
              include_deleted: bool = False,
              query: Optional[str] = None) -> List[Dict]:
    """
    Возвращает списки с агрегированными счётчиками.
    Если передан query, ищем без учёта регистра по:
      - названию списка (lists.title),
      - пунктам чеклиста (items.text),
      - текстовым заметкам (lists.note_text).
    """
    conn = get_conn()
    where = ["1=1"]
    params: List = []

    if not include_archived:
        where.append("l.archived=0")
    if not include_deleted:
        where.append("l.deleted_at IS NULL")

    if query:
        qnorm = (query or "").strip().lower()
        like = f"%{qnorm}%"
        where.append("""
            (
              LOWER(l.title) LIKE ? OR
              EXISTS (
                SELECT 1 FROM items it
                WHERE it.list_id = l.id AND LOWER(it.text) LIKE ?
              ) OR
              (l.note_text IS NOT NULL AND LOWER(l.note_text) LIKE ?)
            )
        """)
        params.extend([like, like, like])

    sql = f"""
    SELECT
      l.id, l.title, l.color, l.pinned, l.archived, l.kind, l.note_text,
      l.created_at, l.updated_at,
      (SELECT COUNT(*) FROM items i WHERE i.list_id=l.id) AS item_count,
      (SELECT COUNT(*) FROM items i WHERE i.list_id=l.id AND i.checked=1) AS done_count
    FROM lists l
    WHERE {' AND '.join(where)}
    ORDER BY l.pinned DESC, COALESCE(l.updated_at, l.created_at) DESC, l.created_at DESC
    """
    cur = conn.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]
