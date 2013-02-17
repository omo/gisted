# -*- coding: utf-8 -*-

import os.path
import StringIO
import unittest
import base64
import urllib2
import urlparse
import json
import types
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
    
    
class FetcherTest(unittest.TestCase):
    class TestingFetcher(gisted.Fetcher):
        def open(self, req):
            return fetch(req.get_full_url())

    def test_ted_hello(self):
        target = self.TestingFetcher("http://www.ted.com/talks/clay_shirky_how_the_internet_will_one_day_transform_government.html")
        self.assertEquals(target.extractor.title, "Clay Shirky: How the Internet will (one day) transform government | Video on TED.com")
        paras = target.extractor.transcript_paragraphs
        self.assertEquals(len(paras), 34)
        self.assertTrue("I want to talk to you today about something" in paras[0])
        self.assertTrue("Let's start here." in paras[0])
        self.assertTrue("Thank you for listening." in paras[-1])

        text = target.extractor.body
        self.assertTrue("I want to talk to you today about something" in text)
        self.assertTrue("Thank you for listening." in text)

        md = target.post.to_markdown()
        self.assertIn("I want to talk to you today about something", md)

    def test_infoq_hello(self):
        target = self.TestingFetcher("http://www.infoq.com/interviews/sadek-drobi-play2-story-new-21")
        post = target.post
        paras = post.paragraphs
        self.assertEquals(35, len(paras))
        self.assertTrue(paras[0].startswith("*") and paras[0].endswith("*"))
        

class UploaderTest(unittest.TestCase):
    def test_hello(self):
        fake_result_url = "https://api.github.com/gists/xxxx"
        class TestingUploader(gisted.Uploader):
            def open(self, req):
                self._req = req
                return StringIO.StringIO(json.dumps({ "url": fake_result_url }))

        u = TestingUploader.make()
        ret = u.upload(gisted.Post.make("Hello, World!", "Hello?", "http://example.com/"))
        self.assertEquals(ret["url"], fake_result_url)
        self.assertTrue("https://api.github.com/gists" in u._req.get_full_url())
        q = urlparse.parse_qs(urlparse.urlparse(u._req.get_full_url()).query)
        self.assertIn("client_id", q)
        self.assertIn("client_secret", q)
        json.loads(u._req.get_data()) # Should be a JSON
        self.assertEquals("xxxx", u.created_id)

        withauth = TestingUploader.make("testtoken")
        ret = withauth.upload(gisted.Post.make("Hello, World!", "Hello?", "http://example.com/"))
        self.assertEquals("https://api.github.com/gists", withauth._req.get_full_url())
        q = urlparse.parse_qs(urlparse.urlparse(withauth._req.get_full_url()).query)
        self.assertNotIn("client_id", q)
        self.assertNotIn("client_secret", q)
        self.assertEquals("token testtoken", withauth._req.get_header("Authorization"))

    def test_make_body(self):
        target = gisted.Uploader.make()
        body = target._make_body(gisted.Post.make("Hello, World!", "Hello?", "http://example.com/"))
        body_dict = json.loads(body)
        self.assertIn("Hello?", body_dict["files"]["hello-world.md"]["content"])
        self.assertIn("----", body_dict["files"]["hello-world.md"]["content"])


class PostTest(unittest.TestCase):
    def test_parser(self):
        body = open(conf.data_path("hello-post.md")).read().decode("utf-8")
        target = gisted.Post.parse("12345", body)
        self.assertEquals(target.title, u"Commencement Address to Atlanta’s John Marshall Law School")
        self.assertEquals(target.source_url, "http://lessig.tumblr.com/post/24065401182/commencement-address-to-atlantas-john-marshall-law")
        self.assertEquals(target.source_hostname, "lessig.tumblr.com")
        self.assertEquals(target.way_url, "http://gisted.in/")
        self.assertEquals(target.way_hostname, "gisted.in")
        self.assertEquals(len(target.paragraphs), 56)
        self.assertIn("Congratulations to you", target.body)
        markdown = target.to_markdown()
        self.assertIn("----", markdown)

    def test_filename(self):
        def with_title(title):
            return gisted.Post.make(title, None, None)

        target = gisted.Uploader.make()
        self.assertEquals("hello.md", with_title("Hello").filename)
        self.assertEquals("hello-world.md", with_title("Hello, World").filename)
        self.assertEquals("hello-world.md", with_title("\\Hello, World//").filename)
        self.assertEquals("hello.md", with_title("hello-012").filename)
        self.assertEquals("transcript.md", with_title("***").filename)
        self.assertEquals("young-ha-kim-be-an-artist-right-now.md", with_title("Young-ha Kim: Be an artist, right now! | Video on TED.com").filename)


class DownloaderTest(unittest.TestCase):
    def test_hello(self):
        target = gisted.Downloader.make()
        resp = json.load(open(conf.data_path("hello-gist.json")))
        url = target._find_raw_url(resp)
        self.assertEquals("https://gist.github.com/raw/365370/8c4d2d43d178df44f4c03a7f2ac0ff512853564e/ring.erl", url)

    def test_testshow(self):
        target = gisted.Downloader.make()
        post = target.get("testshow")
        self.assertEquals(post.contributor_name, "octocat")


class AuthTest(unittest.TestCase):
    def test_redirect_url(self):
        auth = gisted.Auth.make({})
        u = urlparse.urlparse(auth.redirect_url)
        q = urlparse.parse_qs(u.query)
        self.assertTrue("None" != q["client_id"][0])
        self.assertTrue("None" != q["state"][0])

    def test_did_come_back(self):
        class TestAuth(gisted.Auth):
            def open(self, req):
                self._req = req
                return StringIO.StringIO(json.dumps({ "access_token": "mytoken" }))

        auth = TestAuth.make({})
        auth.did_come_back({ "code": "mycode", "state": auth.canary })


class PasterTest(unittest.TestCase):
    def test_hello(self):
        def fake_open(req):
            u = req if isinstance(req, types.StringType) else req.get_full_url()
            if "http://www.ted.com/" in u:
                return fetch(u)
            if "https://api.github.com/gists" in u:
                self.assertIsNotNone(req.get_data())
                return open(conf.data_path("hello-gist.json"))
            return None

        class TestingUploader(gisted.Uploader):
            def open(self, req):
                return fake_open(req)

        class TestingFetcher(gisted.Fetcher):
            def open(self, req):
                return fake_open(req)

        class TestingPaster(gisted.Paster):
            uploader_class = TestingUploader
            fetcher_class = TestingFetcher

        target = TestingPaster.make("testtoken")
        target.paste_from("http://www.ted.com/talks/clay_shirky_how_the_internet_will_one_day_transform_government.html")
        self.assertEquals(target.created_id, "73062b6d882439cfbf14")
