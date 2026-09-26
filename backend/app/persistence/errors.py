"""Storage boundary errors. Messages intentionally omit clinical payloads."""


class PersistenceError(Exception):
    pass


class PersistenceInputError(PersistenceError):
    pass


class RecordConflict(PersistenceError):
    pass


class ScopeMismatch(PersistenceError):
    pass


class RecordNotFound(PersistenceError):
    pass


class UnsupportedOperation(PersistenceError):
    pass


class StorageIntegrityError(PersistenceError):
    pass


class SchemaMismatch(PersistenceError):
    pass


class TransactionAborted(PersistenceError):
    pass
