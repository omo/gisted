# -*- coding: utf-8 -*-

import unittest
import flask
import gisted.web

class WebTest(unittest.TestCase):
    def setUp(self):
        self.app = gisted.web.app.test_client()

    def get_test_show(self):
        resp = self.app.get("/testshow")
        self.assertTrue("200" in resp.status)
