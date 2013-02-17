# -*- coding: utf-8 -*-

import os
import json
import re
import random
import codecs
import string
import urllib
import urllib2
import urlparse
import bs4
import gisted.conf as conf

def urlopen(req):
    return urllib.urlopen(req)

def random_string(n=8):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(n))


class NotFound(Exception):
    def __init__(self, message):
        super(NotFound, self).__init__(message)  


TRANSCRIPT_TEMPLSTE = u"""

 * Source: {url}
 * Paster: http://gisted.in/

----

{title}
{title_deco}

{body}
"""

class Post(object):
    def __init__(self, gist_id, source_url, title, body):
        self.gist_id = gist_id
        self.source_url = source_url
        self.title = title
        self.body = body

    @property
    def filename(self):
        stripped = re.sub("\\|.*$", "", self.title)
        alphaonly = re.sub("([^\\w]|\\d)+", "-", stripped).lower()
        base = re.sub("(^\\-+)|(\\-+$)", "", alphaonly)
        if not base:
            base = "transcript"
        return base + ".md"

    @property
    def source_hostname(self):
        return urlparse.urlparse(self.source_url).hostname

    @property
    def paragraphs(self):
        return re.split("\n\n+", self.body)

    @classmethod
    def parse(cls, gist_id, raw_body):
        head, body = raw_body.split("----")
        m = re.search("\* +Source: *(.*)\n", head)
        if not m:
            raise NotFound("Couldn't see the original URL.")
        source = m.group(1).strip()
        m = re.search("([^=]*)(=+)(.*)", body, re.S)
        if not m:
            raise NotFound("Couldn't see the title.")
        title = m.group(1).strip()
        remaining = m.group(3).strip()
        return Post(gist_id, source, title, remaining)

    @classmethod
    def make(cls, source, title, text):
        return cls(None, source, title, text)

    def to_markdown(self):
        return TRANSCRIPT_TEMPLSTE.format(url=self.source_url, title=self.title, title_deco="="*len(self.title), body=self.body)


# FIXME: Should be fetcher
class Fetcher(object):
    def __init__(self, uri):
        self._uri = uri
        self._html = None
        self._soup = None

    def open(self, req):
        return urllib2.urlopen(req)

    @property
    def html(self):
        if not self._html:
            self._html = self.open(self._uri).read()
        return self._html

    @property
    def soup(self):
        if not self._soup:
            self._soup = bs4.BeautifulSoup(self.html, "html5lib")
        return self._soup

    @property
    def title(self):
        return self.soup.title.string

    @property
    def transcript_paragraphs(self):
        lines = self.soup.find_all("a", class_="transcriptLink")
        found_ptags = []
        paragraphs = []
        for line in lines:
            text = line.string
            p = line.parent
            try:
                i = found_ptags.index(p)
                paragraphs[i] = paragraphs[i] + " " + text
            except ValueError:
                found_ptags.append(p)
                paragraphs.append(text)
        return paragraphs

    @property
    def transcript_text(self):
        return "\n\n".join(self.transcript_paragraphs)

    @property
    def post(self):
        return Post.make(self._uri, self.title, self.transcript_text)


class GithubClient(object):
    BASE_URI = "https://api.github.com"

    def __init__(self, client_id, client_secret, token):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = token

    def build_request(self, path, data=None):
        url = urlparse.urljoin(self.BASE_URI, path)
        if self._token:
            return urllib2.Request(url, data=data, headers={ "Authorization": "token {t}".format(t=self._token) })
        if "?" not in url:
            url = url + "?"
        url = url + "client_id={client_id}&client_secret={client_secret}".format(client_id=self._client_id, client_secret=self._client_secret)
        return urllib2.Request(url, data=data)


class Uploader(GithubClient):
    @classmethod
    def make(cls, token=None):
        return cls(conf.credential("github_client_id"), conf.credential("github_client_secret"), token)

    def __init__(self, client_id, client_secret, token=None):
        super(Uploader, self).__init__(client_id, client_secret, token)


    def _make_body(self, post):
        # See http://developer.github.com/v3/gists/ for the API detail
        body_dict = {
            "description": "Gisted: " + post.title,
            "public": True,
            "files": { 
                post.filename: post.to_markdown()
            }
        }

        return json.dumps(body_dict)

    def open(self, req):
        return urllib2.urlopen(req)

    def upload(self, post):
        resp = self.open(self.build_request("/gists", data=self._make_body(post)))
        self.response = json.load(resp)
        return self.response
    
    @property
    def created_id(self):
        m = re.search("https://api\\.github\\.com/gists/(.*)", self.response["url"])
        return m.group(1)

    @property
    def created_page_url(self):
        return "https://gist.github.com/{id}".format(id=self.created_id)

        
class Downloader(GithubClient):
    @classmethod
    def make(cls, token=None):
        return cls(conf.credential("github_client_id"), conf.credential("github_client_secret"), token)

    def __init__(self, client_id, client_secret, token=None):
        super(Downloader, self).__init__(client_id, client_secret, token)

    def _find_raw_url(self, resp):
        files = resp["files"]
        if not len(files):
            raise NotFound("No files are included")
        return files.values()[0]["raw_url"]

    def _open(self, req):
        return urllib2.urlopen(req)

    def _get_raw_body(self, id):
        resp = json.load(self._open(self.build_request("/gists/{id}".format(id=id))))
        raw_url = self._find_raw_url(resp)
        return self._open(raw_url).read().decode('utf-8')
        
    def get(self, id):
        body = self._get_raw_body(id) if id != "testshow" else codecs.open(conf.data_path("hello-post.md"), encoding="utf-8").read()
        return Post.parse(id, body)


class Paster(object):
    
    fetcher_class = Fetcher
    uploader_class = Uploader

    @classmethod
    def make(cls, token=None):
        return cls(token)

    def __init__(self, token):
        self.up = self.uploader_class.make(token)

    def open(self, req):
        return urllib2.urlopen(req)

    def paste_from(self, source_url):
        fetcher = self.fetcher_class(source_url)
        return self.up.upload(fetcher.post)
        
    @property
    def created_id(self):
        return self.up.created_id

    @property
    def created_page_url(self):
        return self.up.created_page_url


class Auth(object):
    BACK_URI = "http://gisted.in/logback"

    @classmethod
    def make(cls, session):
        return cls(conf.credential("github_client_id"), conf.credential("github_client_secret"), session)

    def __init__(self, client_id, client_secret, session):
        self.client_id = client_id
        self.client_secret = client_secret
        self._session = session
        self.allows_anonymous = False

    def open(self, req):
        return urllib2.urlopen(req)

    def did_come_back(self, args):
        code = args["code"]
        state = args["state"]
        if self.canary != state:
            return False

        post_url = "https://github.com/login/oauth/access_token"
        post_data = "client_id={client_id}&client_secret={client_secret}&code={code}&state={state}".format(
            client_id = conf.credential("github_client_id"),
            client_secret = conf.credential("github_client_secret"),
            code = code,
            state = state)
        req = urllib2.Request(post_url, post_data, headers={"Accept": "application/json"})
        resp = json.load(self.open(req))
        self._session["token"] = resp["access_token"]

    def fake_login(self):
        self._session["token"] = "fake_token"

    @property
    def token(self):
        return self._session.get("token")

    @property
    def authenticated(self):
        return None != self.token

    @property
    def allows_pasting(self):
        return self.authenticated or self.allows_anonymous

    @property
    def canary(self):
        if not self._session.get("canary"):
            self._session["canary"] = random_string()
        return self._session["canary"]

    @property
    def redirect_url(self):
        params = { "c": self.client_id, 
                   "s": self.canary }
        return "https://github.com/login/oauth/authorize?scope=gist&client_id={c}&state={s}".format(**params)
