# -*- coding: utf-8 -*-

import unittest
import flask
import gisted.web

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
