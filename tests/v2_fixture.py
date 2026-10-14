"""Synthetic, process-local persistence for V2 API acceptance tests.

This deliberately does not read application .env files or connect to MongoDB. It
implements the Motor collection operations used by V2 and fails on unsupported
operators instead of silently accepting a query that a real database rejects.
All documents returned to the application are copies, as they are with MongoDB.
"""

from copy import deepcopy
from dataclasses import dataclass
import re
import uuid


MISSING = object()


def get_path(document, key, default=MISSING):
    value = document
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def set_path(document, key, value):
    parts = key.split(".")
    target = document
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = deepcopy(value)


def unset_path(document, key):
    parts = key.split(".")
    target = document
    for part in parts[:-1]:
        target = target.get(part, {})
    target.pop(parts[-1], None)


def match_value(value, expected):
    if not isinstance(expected, dict) or not any(k.startswith("$") for k in expected):
        return (value is MISSING and expected is None) or value == expected or (
            isinstance(value, list) and not isinstance(expected, list) and expected in value)
    for operator, operand in expected.items():
        if operator == "$eq":
            valid = value == operand
        elif operator == "$ne":
            valid = value != operand
        elif operator == "$exists":
            valid = (value is not MISSING) == bool(operand)
        elif operator == "$in":
            valid = any(v in operand for v in value) if isinstance(value, list) else value in operand
        elif operator == "$nin":
            valid = all(v not in operand for v in value) if isinstance(value, list) else value not in operand
        elif operator in ("$gt", "$gte", "$lt", "$lte"):
            valid = False if value is MISSING else {
                "$gt": lambda: value > operand,
                "$gte": lambda: value >= operand,
                "$lt": lambda: value < operand,
                "$lte": lambda: value <= operand,
            }[operator]()
        elif operator == "$regex":
            flags = re.I if "i" in expected.get("$options", "") else 0
            valid = value is not MISSING and re.search(operand, str(value), flags) is not None
        elif operator == "$options":
            continue
        elif operator == "$type":
            expected_type = {"string": str, "object": dict, "array": list, "bool": bool, "number": (int, float)}.get(operand)
            valid = value is not MISSING and expected_type is not None and isinstance(value, expected_type)
        elif operator == "$elemMatch":
            valid = isinstance(value, list) and any(matches(v, operand) for v in value)
        elif operator == "$not":
            valid = not match_value(value, operand)
        else:
            raise NotImplementedError(f"Unsupported Mongo query operator {operator}")
        if not valid:
            return False
    return True


def matches(document, query):
    for key, expected in (query or {}).items():
        if key == "$or":
            valid = any(matches(document, q) for q in expected)
        elif key == "$and":
            valid = all(matches(document, q) for q in expected)
        elif key == "$nor":
            valid = not any(matches(document, q) for q in expected)
        elif key.startswith("$"):
            raise NotImplementedError(f"Unsupported Mongo query {key}")
        else:
            valid = match_value(get_path(document, key), expected)
        if not valid:
            return False
    return True


def project(document, projection=None):
    result = deepcopy(document)
    if not projection:
        return result
    includes = [key for key, value in projection.items() if value and key != "_id"]
    if includes:
        result = {}
        for key in includes:
            value = get_path(document, key)
            if value is not MISSING:
                set_path(result, key, value)
        if projection.get("_id", 1) and "_id" in document:
            result["_id"] = document["_id"]
    else:
        for key, value in projection.items():
            if not value:
                unset_path(result, key)
    return result


@dataclass
class WriteResult:
    matched_count: int = 0
    modified_count: int = 0
    deleted_count: int = 0
    inserted_id: str | None = None
    upserted_id: str | None = None


class Cursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, field, direction=1):
        fields = field if isinstance(field, list) else [(field, direction)]
        for key, order in reversed(fields):
            self.documents.sort(key=lambda d: (get_path(d, key, None) is not None, get_path(d, key, "")), reverse=order < 0)
        return self

    def limit(self, length):
        self.documents = self.documents[:length] if length else self.documents
        return self

    def skip(self, count):
        self.documents = self.documents[count:]
        return self

    async def to_list(self, length=None):
        return deepcopy(self.documents if length is None else self.documents[:length])

    def __aiter__(self):
        self.iterator = iter(self.documents)
        return self

    async def __anext__(self):
        try:
            return deepcopy(next(self.iterator))
        except StopIteration:
            raise StopAsyncIteration


class Collection:
    def __init__(self, name):
        self.name = name
        self.documents = []
        self.indexes = []

    async def create_index(self, keys, **options):
        fields = [keys] if isinstance(keys, str) else [key for key, _ in keys]
        if options.get("unique"):
            self.indexes.append((fields, options.get("sparse", False), options.get("partialFilterExpression")))
        return options.get("name", "_".join(fields))

    def _check_unique(self, proposed, ignore_id=None):
        for fields, sparse, partial in self.indexes:
            if partial and not matches(proposed, partial):
                continue
            values = [get_path(proposed, field) for field in fields]
            if sparse and any(value is MISSING for value in values):
                continue
            for existing in self.documents:
                if existing.get("_id") == ignore_id or (partial and not matches(existing, partial)):
                    continue
                if values == [get_path(existing, field) for field in fields]:
                    try:
                        from pymongo.errors import DuplicateKeyError
                    except ImportError:
                        DuplicateKeyError = ValueError
                    raise DuplicateKeyError(f"Duplicate fixture index in {self.name}")

    async def insert_one(self, document):
        proposed = deepcopy(document)
        proposed.setdefault("_id", str(uuid.uuid4()))
        self._check_unique(proposed)
        self.documents.append(proposed)
        return WriteResult(inserted_id=proposed["_id"])

    async def insert_many(self, documents, **options):
        ids = [(await self.insert_one(document)).inserted_id for document in documents]
        return type("InsertManyResult", (), {"inserted_ids": ids})()

    async def find_one(self, query=None, projection=None, sort=None):
        cursor = self.find(query, projection)
        if sort:
            cursor.sort(sort)
        values = await cursor.to_list(1)
        return values[0] if values else None

    def find(self, query=None, projection=None):
        return Cursor([project(document, projection) for document in self.documents if matches(document, query)])

    async def count_documents(self, query):
        return sum(matches(document, query) for document in self.documents)

    async def estimated_document_count(self):
        return len(self.documents)

    @staticmethod
    def _update(document, updates, inserted=False):
        if not any(key.startswith("$") for key in updates):
            original_id = document.get("_id")
            document.clear()
            document.update(deepcopy(updates))
            document.setdefault("_id", original_id)
            return
        for operator, fields in updates.items():
            for key, value in fields.items():
                if operator == "$set" or (operator == "$setOnInsert" and inserted):
                    set_path(document, key, value)
                elif operator == "$setOnInsert":
                    continue
                elif operator == "$unset":
                    unset_path(document, key)
                elif operator == "$inc":
                    set_path(document, key, get_path(document, key, 0) + value)
                elif operator == "$push":
                    current = get_path(document, key, [])
                    current.extend(deepcopy(value["$each"])) if isinstance(value, dict) and "$each" in value else current.append(deepcopy(value))
                    if isinstance(value, dict) and "$slice" in value:
                        current = current[:value["$slice"]] if value["$slice"] >= 0 else current[value["$slice"]:]
                    set_path(document, key, current)
                elif operator == "$addToSet":
                    current = get_path(document, key, [])
                    values = value["$each"] if isinstance(value, dict) and "$each" in value else [value]
                    for item in values:
                        if item not in current:
                            current.append(deepcopy(item))
                    set_path(document, key, current)
                elif operator == "$pull":
                    current = get_path(document, key, [])
                    set_path(document, key, [v for v in current if not (matches(v, value) if isinstance(v, dict) and isinstance(value, dict) else match_value(v, value))])
                elif operator == "$max":
                    old = get_path(document, key)
                    if old is MISSING or old < value:
                        set_path(document, key, value)
                else:
                    raise NotImplementedError(f"Unsupported fixture update {operator}")

    async def update_one(self, query, updates, upsert=False, **options):
        for index, document in enumerate(self.documents):
            if matches(document, query):
                proposed = deepcopy(document)
                self._update(proposed, updates)
                self._check_unique(proposed, document.get("_id"))
                self.documents[index] = proposed
                return WriteResult(matched_count=1, modified_count=int(proposed != document))
        if upsert:
            proposed = {key: deepcopy(value) for key, value in query.items() if not key.startswith("$") and not isinstance(value, dict)}
            self._update(proposed, updates, inserted=True)
            inserted = await self.insert_one(proposed)
            return WriteResult(upserted_id=inserted.inserted_id)
        return WriteResult()

    async def update_many(self, query, updates, **options):
        ids = [document["_id"] for document in self.documents if matches(document, query)]
        results = [await self.update_one({"_id": ident}, updates) for ident in ids]
        return WriteResult(matched_count=len(ids), modified_count=sum(r.modified_count for r in results))

    async def find_one_and_update(self, query, updates, return_document=False, upsert=False, **options):
        before = await self.find_one(query)
        result = await self.update_one(query, updates, upsert=upsert)
        if not return_document:
            return before
        ident = before.get("_id") if before else result.upserted_id
        return await self.find_one({"_id": ident}) if ident else None

    async def delete_one(self, query):
        for index, document in enumerate(self.documents):
            if matches(document, query):
                self.documents.pop(index)
                return WriteResult(deleted_count=1)
        return WriteResult()

    async def delete_many(self, query):
        before = len(self.documents)
        self.documents = [d for d in self.documents if not matches(d, query)]
        return WriteResult(deleted_count=before - len(self.documents))

    async def distinct(self, field, query=None):
        values = []
        for document in self.documents:
            value = get_path(document, field)
            if matches(document, query) and value is not MISSING and value not in values:
                values.append(deepcopy(value))
        return values


class Database:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, Collection(name))

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    async def list_collection_names(self):
        return list(self.collections)

    def snapshot(self):
        return {name: deepcopy(collection.documents) for name, collection in self.collections.items()}
