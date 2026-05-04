import os

_client = None


def get_db():
    """Return a DB client. Prefers DATABASE_URL (local postgres) over SUPABASE_URL."""
    global _client
    if _client is not None:
        return _client

    if os.environ.get("DATABASE_URL"):
        _client = LocalDBClient(os.environ["DATABASE_URL"])
    else:
        from supabase import create_client
        _client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    return _client


# ---------------------------------------------------------------------------
# Local PostgreSQL client — same chain API as supabase-py
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data: list, count: int | None = None):
        self.data = data
        self.count = count


class _Query:
    def __init__(self, database_url: str, table: str):
        self._url = database_url
        self._table = table
        self._filters: list = []
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._updates: dict | None = None
        self._inserts: list | None = None

    def select(self, _cols, **_kwargs):
        return self

    def eq(self, col: str, val):
        self._filters.append(("eq", col, val))
        return self

    def ilike(self, col: str, pattern: str):
        self._filters.append(("ilike", col, pattern))
        return self

    def order(self, col: str, desc: bool = False):
        self._order_col = col
        self._order_desc = desc
        return self

    def update(self, values: dict):
        self._updates = values
        return self

    def insert(self, record):
        self._inserts = record if isinstance(record, list) else [record]
        return self

    def upsert(self, records):
        self._inserts = records if isinstance(records, list) else [records]
        return self

    def _where(self) -> tuple[str, list]:
        if not self._filters:
            return "", []
        parts, params = [], []
        for op, col, val in self._filters:
            if op == "eq":
                parts.append(f'"{col}" = %s')
                params.append(val)
            elif op == "ilike":
                parts.append(f'"{col}" ILIKE %s')
                params.append(val)
        return "WHERE " + " AND ".join(parts), params

    def execute(self) -> _Result:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(self._url)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if self._updates is not None:
                    set_clause = ", ".join(f'"{k}" = %s' for k in self._updates)
                    where, where_params = self._where()
                    cur.execute(
                        f'UPDATE "{self._table}" SET {set_clause} {where}',
                        list(self._updates.values()) + where_params,
                    )
                    conn.commit()
                    return _Result([])

                if self._inserts is not None:
                    for rec in self._inserts:
                        cols = list(rec.keys())
                        ph = ", ".join(["%s"] * len(cols))
                        col_names = ", ".join(f'"{c}"' for c in cols)
                        cur.execute(
                            f'INSERT INTO "{self._table}" ({col_names}) VALUES ({ph})',
                            [rec[c] for c in cols],
                        )
                    conn.commit()
                    return _Result(self._inserts)

                where, params = self._where()
                order = ""
                if self._order_col:
                    direction = "DESC" if self._order_desc else "ASC"
                    order = f'ORDER BY "{self._order_col}" {direction}'
                cur.execute(f'SELECT * FROM "{self._table}" {where} {order}'.strip(), params)
                rows = [dict(r) for r in cur.fetchall()]
                return _Result(rows, count=len(rows))
        finally:
            conn.close()


class LocalDBClient:
    def __init__(self, database_url: str):
        self._url = database_url

    def table(self, name: str) -> _Query:
        return _Query(self._url, name)
