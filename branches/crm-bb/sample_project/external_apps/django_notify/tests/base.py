import unittest
from django import http
from django.utils.translation import ugettext_lazy
from django_notify.storage import Storage
from django_notify.storage.base import Notification


class BaseTest(unittest.TestCase):
    storage_class = Storage

    def get_request(self):
        return http.HttpRequest()
    
    def get_response(self):
        return http.HttpResponse()

    def get_storage(self, data=None):
        """
        Return the storage backend, setting it's loaded data to the ``data``
        argument.
        
        This method avoids the storage ``_get`` method from getting called so
        that other parts of the storage backend can be tested independent of
        the message retrieval logic.
        
        """
        storage = self.storage_class(self.get_request())
        storage._loaded_data = data or []
        return storage

    def test_add(self):
        storage = self.get_storage()
        self.assertFalse(storage.added_new)
        storage.add('Test message 1')
        self.assert_(storage.added_new)
        storage.add('Test message 2', 'tag')
        self.assertEqual(len(storage), 2)

    def test_add_lazy_translation(self):
        storage = self.get_storage()
        response = self.get_response()

        storage.add(ugettext_lazy('lazy message'))
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 1)

    def test_no_update(self):
        storage = self.get_storage()
        response = self.get_response()
        storage.update(response)
        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 0)

    def test_add_update(self):
        storage = self.get_storage()
        response = self.get_response()

        storage.add('Test message 1')
        storage.add('Test message 1', 'tag')
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 2)

    def test_existing_add_read_update(self):
        storage = self.get_existing_storage()
        response = self.get_response()
        
        storage.add('Test message 3')
        list(storage)   # Simulates a read
        storage.update(response)

        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 0)

    def test_existing_read_add_update(self):
        storage = self.get_existing_storage()
        response = self.get_response()
        
        list(storage)   # Simulates a read
        storage.add('Test message 3')        
        storage.update(response)
        
        storing = self.stored_messages_count(storage, response)
        self.assertEqual(storing, 1)

    def stored_messages_count(self, storage, response):
        """
        Returns the number of messages being stored after a
        ``storage.update()`` call.
        
        """
        raise NotImplementedError('This method must be set by a subclass.')

    def test_get(self):
        raise NotImplementedError('This method must be set by a subclass.')

    def get_existing_storage(self):
        storage = self.get_storage([Notification('Test message 1'),
                                    Notification('Test message 2', 'tag')])
        return storage

    def test_existing_read(self):
        """
        Reading the existing storage doesn't cause the data to be lost.
        
        """
        storage = self.get_existing_storage()
        self.assertFalse(storage.used)
        # After iterating the storage engine directly, the used flag is set.
        data = list(storage)
        self.assert_(storage.used)
        # The data does not disappear because it has been iterated.
        self.assertEqual(data, list(storage))

    def test_existing_add(self):
        storage = self.get_existing_storage()
        self.assertFalse(storage.added_new)
        storage.add('Test message 3')
        self.assert_(storage.added_new)
