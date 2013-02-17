# -*- coding: utf-8 -*-
# Based on http://flask.pocoo.org/snippets/75/

import json
from datetime import timedelta
from Crypto.Cipher import DES
import base64
from werkzeug.datastructures import CallbackDict
from flask.sessions import SessionInterface, SessionMixin

class Session(CallbackDict, SessionMixin):
    def __init__(self, initial=None, new=False):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)
        self.modified = False

class Crypter(object):
    key_length = 8
    block_length = 8

    def _pad(self, text):
        return text + (self.block_length - len(text)%self.block_length)*' '

    def __init__(self, key):
        if len(key) != self.key_length:
            raise ValueError("Session: Encryption key should be 8 byte")
        self._impl = DES.new(key, DES.MODE_ECB)

    def encrypt(self, text):
        return base64.b64encode(self._impl.encrypt(self._pad(text)))

    def decrypt(self, ciph):
        return self._impl.decrypt(base64.b64decode(ciph)).strip()
    

class SessionInterface(SessionInterface):
    serializer = json
    session_class = Session
    # https://www.dlitz.net/software/pycrypto/doc/

    def __init__(self, key):
        self._crypter = Crypter(key)

    def open_session(self, app, request):
        ciph = request.cookies.get(app.session_cookie_name)
        if not ciph:
            return self.session_class(new=True)
        try:
            text = self._crypter.decrypt(ciph)
            return self.session_class(initial=self.serializer.loads(text))
        except ValueError, e:
            # XXX: log
            return self.session_class(new=True)

    def save_session(self, app, session, response):
        if not session.modified:
            # For saving bandwidth, we don't save any unmodified session even if it is created.
            # This means we create fresh session each time for non-login user.
            return
        domain = self.get_cookie_domain(app)
        if not session:
            response.delete_cookie(app.session_cookie_name,
                                   domain=domain)
            return
        cookie_exp = self.get_expiration_time(app, session)
        text = self.serializer.dumps(dict(session))
        ciph = self._crypter.encrypt(text)
        response.set_cookie(app.session_cookie_name, ciph,
                            expires=cookie_exp, httponly=True,
                            domain=domain)
