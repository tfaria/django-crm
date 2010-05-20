from django.utils.encoding import force_unicode, StrAndUnicode


class Notification(StrAndUnicode):
    """
    A notification message.
    
    """
    def __init__(self, message, tags=None, extras=None):
        self.message = message
        self.tags = tags or ''
        self.extras = extras or {}

    def _prepare(self):
        """
        Prepare the notification for serialization by forcing the ``message``
        and ``tags`` to unicode in case they are lazy translations.
        
        Known "safe" types (None, int, etc.) are not converted (see Django's
        ``force_unicode`` implementation for details).
        
        """
        self.message = force_unicode(self.message, strings_only=True)
        self.tags = force_unicode(self.tags, strings_only=True)

    def __unicode__(self):
        return force_unicode(self.message)


class EOFNotification:
    """
    A notification class which indicates the end of the message stream (i.e. no
    further message retrieval is required).
    
    Not used in all storage classes.
    
    """


class BaseStorage(object):
    """
    Base backend for temporary notification storage.
    
    This is not a complete class, to be a usable storage backend, it must be
    subclassed and the two methods ``_get`` and ``_store`` overridden.
    
    """
    store_serialized = True

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self._queued_messages = []
        self.used = False
        self.added_new = False
        super(BaseStorage, self).__init__(*args, **kwargs)

    def __len__(self):
        return len(self._loaded_messages) + len(self._queued_messages)

    def __iter__(self):
        self.used = True
        if self._queued_messages:
            self._loaded_messages.extend(self._queued_messages)
            self._queued_messages = []
        return iter(self._loaded_messages)

    def __contains__(self, item):
        return item in self._loaded_messages or item in self._queued_messages

    @property
    def _loaded_messages(self):
        """
        Return a list of loaded messages, retrieving them first if they have
        not been loaded yet.
        
        """
        if not hasattr(self, '_loaded_data'):
            self._loaded_data = self._get() or []
        return self._loaded_data

    def _get(self, *args, **kwargs):
        """
        Retrieve a list of stored messages.
        
        **This method must be implemented by a subclass.**
        
        If it is possible to tell if the backend was not used (as opposed to
        just containing no messages) then ``None`` should be returned.
        
        """
        raise NotImplementedError()

    def _store(self, messages, response, *args, **kwargs):
        """
        Store a list of messages, returning a list of any messages which could
        not be stored.
        
        **This method must be implemented by a subclass.**
        
        """
        raise NotImplementedError()

    def _prepare_notifications(self, notifications):
        """
        Prepare a list of notifications for storage.
        
        """
        if self.store_serialized:
            for notification in notifications:
                notification._prepare()

    def update(self, response, fail_silently=True):
        """
        Store all unread messages.
        
        If the backend has yet to be iterated, previously stored messages will
        be stored again. Otherwise, only messages added after the last
        iteration will be stored.
        
        """
        if self.used:
            self._prepare_notifications(self._queued_messages)
            return self._store(self._queued_messages, response)
        elif self.added_new:
            notifications = self._loaded_messages + self._queued_messages
            self._prepare_notifications(notifications)
            return self._store(notifications, response)

    def add(self, message, tags='', **extras):
        """
        Queue a message to be stored.
        
        """
        if not message:
            return
        self.added_new = True
        notification = Notification(message, tags, extras)
        self._queued_messages.append(notification)
