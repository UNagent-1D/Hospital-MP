"""In-memory Supabase client fake for tests. Implements the method chain used in app.py."""


class _Result:
    def __init__(self, data: list, count: int | None = None):
        self.data = data
        self.count = count


class _Query:
    def __init__(self, store: list):
        self._store = store
        self._filters: list = []
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._updates: dict | None = None
        self._inserts: list | None = None

    # --- builder methods ---

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

    # --- execution ---

    def _match(self, row: dict) -> bool:
        for op, col, val in self._filters:
            if op == "eq" and row.get(col) != val:
                return False
            if op == "ilike":
                needle = val.strip("%").lower()
                if needle not in str(row.get(col, "")).lower():
                    return False
        return True

    def execute(self) -> _Result:
        if self._updates is not None:
            matched = [r for r in self._store if self._match(r)]
            for row in matched:
                row.update(self._updates)
            return _Result(matched)

        if self._inserts is not None:
            self._store.extend(self._inserts)
            return _Result(self._inserts)

        result = [r for r in self._store if self._match(r)]
        if self._order_col:
            result.sort(key=lambda r: r.get(self._order_col, ""), reverse=self._order_desc)
        return _Result(result, count=len(result))


class FakeSupabaseClient:
    def __init__(self, doctors: list, appointments: list):
        self._stores = {"doctors": doctors, "appointments": appointments}

    def table(self, name: str) -> _Query:
        return _Query(self._stores[name])
