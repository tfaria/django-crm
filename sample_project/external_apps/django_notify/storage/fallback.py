from django_notify.storage.base import BaseStorage, EOFNotification
from django_notify.storage.cookie import CookieStorage
from django_notify.storage.session import SessionStorage


def strip_eof_messages(messages):
    """
    Return a 2 part tuple consisting of a stripped message list and EOF boolean. 
    
    The stripped message list is the original list of messages, with any
    ``EOFNotification`` instances removed
    
    The EOF boolean is calculated from whether there *were* any
    ``EOFNotification`` instances in the original messages list.
    
    """
    if not messages:
        return messages, False
    stripped_messages = [message for message in messages
                         if not isinstance(message, EOFNotification)]
    found_eof = len(stripped_messages) != len(messages)
    return stripped_messages, found_eof


def attempt_store(storage, messages, response):
    """
    Attempt to store all messages in a backend, ensuring that if there were
    unstored messages, that they included the EOFNotification.
    
    If there *were* unstored messages and they didn't contain the EOF, store
    the messages stripped of EOF, then reattach the EOF to the list of unstored
    messages.
    
    """
    unstored_messages = storage._store(messages, response, remove_oldest=False)
    if unstored_messages and not strip_eof_messages(unstored_messages)[1]:
        messages = strip_eof_messages(messages)[0]
        unstored_messages = storage._store(messages, response,
                                           remove_oldest=False) or []
        unstored_messages.append(EOFNotification())
    return unstored_messages


class FallbackStorage(BaseStorage):
    """
    A combination storage backend which tries to store all messages in the
    first backend, storing any unstored messages in each subsequent backend.
    backend.
     
    """
    storage_classes = (CookieStorage, SessionStorage)

    def __init__(self, *args, **kwargs):
        super(FallbackStorage, self).__init__(*args, **kwargs)
        self.storages = [storage_class(*args, **kwargs)
                         for storage_class in self.storage_classes]

    def _get(self, *args, **kwargs):
        """
        Get a single list of messages from all storage backends.
        
        """
        all_messages = []
        for storage in self.storages:
            messages, eof = strip_eof_messages(storage._get())
            # If the backend hasn't been used, no more retrieval is necessary.
            if messages is None:
                break
            all_messages.extend(messages)
            # If we hit an EOFNotification instance, no more retrieval is
            # necessary.
            if eof:
                break
        return all_messages

    def _store(self, messages, response, *args, **kwargs):
        """
        Store the messages, returning any unstored messages after trying all
        backends.
        
        For each storage backend, any messages not stored are passed on to the
        next backend.
        
        """
        messages = strip_eof_messages(messages)[0] or []
        messages.append(EOFNotification())
        for storage in self.storages:
            messages = attempt_store(storage, messages, response)
            # If there are no more messages, we don't need to continue storing.
            if not messages:
                break
        # Strip any EOF notifications before we return any unstored messages
        # since it is specific to this backend.
        messages = strip_eof_messages(messages)[0]
        return messages
