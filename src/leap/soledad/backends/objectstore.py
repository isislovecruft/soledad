"""
Abstract U1DB backend to handle storage using object stores (like CouchDB, for
example.

Right now, this is only used by CouchDatabase backend, but can also be
extended to implement OpenStack or Amazon S3 storage, for example.
"""

from u1db.backends.inmemory import (
    InMemoryDatabase,
    InMemorySyncTarget,
)
from u1db import errors


class ObjectStoreDatabase(InMemoryDatabase):
    """
    A backend for storing u1db data in an object store.
    """

    @classmethod
    def open_database(cls, url, create, document_factory=None):
        raise NotImplementedError(cls.open_database)

    def __init__(self, replica_uid=None, document_factory=None):
        super(ObjectStoreDatabase, self).__init__(
            replica_uid,
            document_factory=document_factory)
        # sync data in memory with data in object store
        if not self._get_doc(self.U1DB_DATA_DOC_ID):
            self._init_u1db_data()
        self._fetch_u1db_data()

    #-------------------------------------------------------------------------
    # methods from Database
    #-------------------------------------------------------------------------

    def _set_replica_uid(self, replica_uid):
        super(ObjectStoreDatabase, self)._set_replica_uid(replica_uid)
        self._store_u1db_data()

    def _put_doc(self, doc):
        raise NotImplementedError(self._put_doc)

    def _get_doc(self, doc):
        raise NotImplementedError(self._get_doc)

    def get_all_docs(self, include_deleted=False):
        raise NotImplementedError(self.get_all_docs)

    def delete_doc(self, doc):
        """Mark a document as deleted."""
        old_doc = self._get_doc(doc.doc_id, check_for_conflicts=True)
        if old_doc is None:
            raise errors.DocumentDoesNotExist
        if old_doc.rev != doc.rev:
            raise errors.RevisionConflict()
        if old_doc.is_tombstone():
            raise errors.DocumentAlreadyDeleted
        if old_doc.has_conflicts:
            raise errors.ConflictedDoc()
        new_rev = self._allocate_doc_rev(doc.rev)
        doc.rev = new_rev
        doc.make_tombstone()
        self._put_and_update_indexes(old_doc, doc)
        return new_rev

    # index-related methods

    def create_index(self, index_name, *index_expressions):
        """
        Create an named index, which can then be queried for future lookups.
        """
        raise NotImplementedError(self.create_index)

    def delete_index(self, index_name):
        """Remove a named index."""
        super(ObjectStoreDatabase, self).delete_index(index_name)
        self._store_u1db_data()

    def _replace_conflicts(self, doc, conflicts):
        super(ObjectStoreDatabase, self)._replace_conflicts(doc, conflicts)
        self._store_u1db_data()

    def _do_set_replica_gen_and_trans_id(self, other_replica_uid,
                                         other_generation,
                                         other_transaction_id):
        super(ObjectStoreDatabase, self)._do_set_replica_gen_and_trans_id(
            other_replica_uid,
            other_generation,
            other_transaction_id)
        self._store_u1db_data()

    #-------------------------------------------------------------------------
    # implemented methods from CommonBackend
    #-------------------------------------------------------------------------

    def _put_and_update_indexes(self, old_doc, doc):
        for index in self._indexes.itervalues():
            if old_doc is not None and not old_doc.is_tombstone():
                index.remove_json(old_doc.doc_id, old_doc.get_json())
            if not doc.is_tombstone():
                index.add_json(doc.doc_id, doc.get_json())
        trans_id = self._allocate_transaction_id()
        self._put_doc(doc)
        self._transaction_log.append((doc.doc_id, trans_id))
        self._store_u1db_data()

    #-------------------------------------------------------------------------
    # methods specific for object stores
    #-------------------------------------------------------------------------

    U1DB_DATA_DOC_ID = 'u1db_data'

    def _fetch_u1db_data(self):
        """
        Fetch u1db configuration data from backend storage.
        """
        NotImplementedError(self._fetch_u1db_data)

    def _store_u1db_data(self):
        """
        Save u1db configuration data on backend storage.
        """
        NotImplementedError(self._store_u1db_data)

    def _init_u1db_data(self):
        """
        Initialize u1db configuration data on backend storage.
        """
        NotImplementedError(self._init_u1db_data)


class ObjectStoreSyncTarget(InMemorySyncTarget):
    pass
