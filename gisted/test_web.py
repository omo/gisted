# -*- coding: utf-8 -*-

import unittest
import flask
import bs4
import urllib
import gisted.web
import gisted

class WebTest(unittest.TestCase):
    def setUp(self):
        gisted.web.app.config["DEBUG"] = True
        self.app = gisted.web.app.test_client()

    def test_show(self):
        resp = self.app.get("/testshow")
        self.assertTrue("200" in resp.status)

    def test_login(self):
        resp = self.app.get("/login")
        self.assertTrue("302" in resp.status)

    def test_logout(self):
        resp = self.app.get("/logout")
        self.assertTrue("302" in resp.status)

    def test_debug_login(self):
        resp = self.app.get("/debug_login")
        self.assertTrue("302" in resp.status)

    def fake_login(self):
        with self.app.session_transaction() as sess:
            gisted.Auth.make(sess).fake_login()
        return self.app.get("/")

    def test_index_flash(self):
        with self.app as c:
            self.fake_login()
            resp = c.post("/", data = { "canary": flask.session["canary"], "u": "http://example.com/notsupported" })
            self.assertTrue("302" in resp.status)
            resp = c.get("/")
            soup = bs4.BeautifulSoup(resp.data)
            error_notices = soup.find_all("li")
            self.assertEquals(1, len(error_notices))

    def test_index_bookmarklet(self):
        with self.app as c:
            self.fake_login()
            resp = c.get("/?u={u}".format(u=urllib.quote("http://example.com/")))
            self.assertTrue("200" in resp.status)
            soup = bs4.BeautifulSoup(resp.data)
            urlfield = [ i for i in soup.find_all("input") if i["name"] == "u" ][0]
            self.assertEquals("http://example.com/", urlfield["value"])

