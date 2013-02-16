# -*- coding: utf-8 -*-

import os.path
import StringIO
import unittest
import base64
import urllib2
import json
import gisted
import gisted.conf as conf

TESTDATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".testdata")

if not os.path.exists(TESTDATA_DIR):
    os.makedirs(TESTDATA_DIR)


def fetch(url):
    filename = os.path.join(TESTDATA_DIR, base64.b64encode(url))
    if not os.path.exists(filename):
        resp = urllib2.urlopen(url)
        with open(filename, "w") as f:
            f.write(resp.read())
    return open(filename)
    
    
class ExtractorTest(unittest.TestCase):
    def test_hello(self):
        with fetch("http://www.ted.com/talks/clay_shirky_how_the_internet_will_one_day_transform_government.html") as f:
            target = gisted.Extractor(f.read())
            self.assertEquals(target.title, "Clay Shirky: How the Internet will (one day) transform government | Video on TED.com")
            paras = target.transcript_paragraphs
            self.assertEquals(len(paras), 34)
            self.assertTrue("I want to talk to you today about something" in paras[0])
            self.assertTrue("Let's start here." in paras[0])
            self.assertTrue("Thank you for listening." in paras[-1])

            text = target.transcript_text
            self.assertTrue("I want to talk to you today about something" in text)
            self.assertTrue("Thank you for listening." in text)


class UploaderTest(unittest.TestCase):
    def test_hello(self):
        fake_result_url = "https://api.github.com/gists/xxxx"
        class TestingUploader(gisted.Uploader):
            def _open(self, req):
                self._req = req
                return StringIO.StringIO(json.dumps({ "url": fake_result_url }))

        u = TestingUploader.make()
        ret = u.upload("http://example.com/", "Hello, World!", "Hello?")
        self.assertEquals(ret["url"], fake_result_url)
        self.assertTrue("https://api.github.com/" in u._req.get_full_url())
        json.loads(u._req.get_data()) # Should be a JSON
        self.assertEquals("xxxx", u.created_id)

    def test_make_filename(self):
        target = gisted.Uploader.make()
        self.assertEquals("hello.md", target._make_filename("Hello"))
        self.assertEquals("hello-world.md", target._make_filename("Hello, World"))
        self.assertEquals("hello-world.md", target._make_filename("\\Hello, World//"))
        self.assertEquals("hello-012.md", target._make_filename("hello-012"))
        self.assertEquals("transcript.md", target._make_filename("***"))
        self.assertEquals("young-ha-kim-be-an-artist-right-now.md", target._make_filename("Young-ha Kim: Be an artist, right now! | Video on TED.com"))


class PostTest(unittest.TestCase):
    def test_parser(self):
        body = open(conf.data_path("hello-post.md")).read()
        target = gisted.Post.make("12345", body)
        self.assertEquals(target.title, "Commencement Address to Atlanta’s John Marshall Law School")
        self.assertEquals(target.original_url, "http://lessig.tumblr.com/post/24065401182/commencement-address-to-atlantas-john-marshall-law")
        self.assertEquals(target.original_hostname, "lessig.tumblr.com")
        self.assertEquals(len(target.paragraphs), 2)
