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

class Invalid(Exception):
    def __init__(self, message):
        super(Invalid, self).__init__(message)  

FAKE_TOKEN = "fake_token_" + conf.credential("flask_secret_key")

TRANSCRIPT_TEMPLSTE = u"""

 * From: {url}
 * Through: http://gisted.in/

----

{title}
{title_deco}

{body}
"""

class Post(object):
    def __init__(self, gist_id, title, body, props):
        self.gist_id = gist_id
        self.title = title
        self.body = body
        self._props = props

    @property
    def filename(self):
        stripped = re.sub("\\|.*$", "", self.title)
        alphaonly = re.sub("([^\\w]|\\d)+", "-", stripped).lower()
        base = re.sub("(^\\-+)|(\\-+$)", "", alphaonly)
        if not base:
            base = "transcript"
        return base + ".md"

    @property
    def source_url(self):
        return self._props.get("From")

    @property
    def source_hostname(self):
        return urlparse.urlparse(self.source_url).hostname

    @property
    def way_url(self):
        return self._props.get("Through")

    @property
    def way_hostname(self):
        u = self.way_url
        return urlparse.urlparse(u).hostname

    @property
    def contributor_url(self):
        return self._props.get("By")

    @property
    def contributor_page_url(self):
        return "https://github.com/{user}".format(user=self.contributor_name)

    @contributor_url.setter
    def contributor_url(self, val):
        self._props["By"] = val

    @property
    def contributor_name(self):
        return self.contributor_url.split("/")[-1]

    @property
    def paragraphs(self):
        return re.split("\n\n+", self.body)

    @classmethod
    def parse(cls, gist_id, raw_body):
        sep = "----"
        if sep not in raw_body:
            raise Invalid("No header separator...: gist:{id}".format(id=gist_id))
        head, body = raw_body.split(sep)
        props = {}
        for line in head.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = re.search("\* +(\w+): *(.*)", line)
            if not m:
                raise Invalid("Bad header line...: {line} in gist:{id}".format(line=line, id=gist_id))
            props[m.group(1)] = m.group(2).strip()
        if not props.get("From"):
            raise Invalid("Source URI isn't in the header... : gist:{id}".format(id=gist_id))
        m = re.search("([^=]*)(=+)(.*)", body, re.S)
        if not m:
            raise Invaid("Couldn't see the title...: gist:{id}".format(id=gist_id))
        title = m.group(1).strip()
        remaining = m.group(3).strip()
        return Post(gist_id, title, remaining, props)

    @classmethod
    def make(cls, title, text, source):
        return cls(None, title, text, { "From": source })

    def to_markdown(self):
        return TRANSCRIPT_TEMPLSTE.format(url=self.source_url, title=self.title, title_deco="="*len(self.title), body=self.body)


def emphasize(text):
    return "*" + text + "*"

class Extractor(object):
    page_encoding = 'utf-8'

    def __init__(self, html):
        self._html = html
        self._soup = bs4.BeautifulSoup(self._html, "html5lib")

    @property
    def title(self):
        return self._soup.title.string


class TedExtractor(Extractor):
    @classmethod
    def acceptable(cls, url):
        return url.startswith("http://www.ted.com/")

    @property
    def transcript_paragraphs(self):
        lines = self._soup.find_all("a", class_="transcriptLink")
        if not lines:
            raise Invalid("No transcipt... Try other page.")
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
    def body(self):
        return "\n\n".join(self.transcript_paragraphs)


class InfoqInterviewExtractor(Extractor):
    @classmethod
    def acceptable(cls, url):
        return url.startswith("http://www.infoq.com/interviews")

    def _from_dialogue(self, div):
        ret = []
        question = u"".join(div.find("span").stripped_strings)
        # FIXME: should emphasize question
        ret.append(emphasize(question))

        answer = div.find(class_="answer")
        for c in answer.children:
            if isinstance(c, bs4.element.Tag):
                if c.name == "br":
                    continue
                if c.name == "b":
                    ret.append(emphasize((c.string or "").strip()))
                else:
                    ret.append((c.string or "").strip())
            else:
                ret.append((c.string or "").strip())
        return ret

    @property
    def transcript_paragraphs(self):
        root = self._soup.find("div", id="intTranscript")
        if not root:
            raise Invalid("No transcipt... Try other page.")

        dialogues = root.find_all("div", class_="question") 
        return reduce(lambda a, i: a + i, [ self._from_dialogue(d) for d in dialogues], [])
        
    @property
    def body(self):
        return "\n\n".join(self.transcript_paragraphs)


class InfoqPresentationExtractor(Extractor):
    @classmethod
    def acceptable(cls, url):
        return url.startswith("http://www.infoq.com/presentations")

    def _from_dialogue(self, div):
        ret = []
        question = u"".join(div.find("span").stripped_strings)
        # FIXME: should emphasize question
        ret.append(emphasize(question))

        answer = div.find(class_="answer")
        for c in answer.children:
            if isinstance(c, bs4.element.Tag):
                if c.name == "br":
                    continue
                if c.name == "b":
                    ret.append(emphasize((c.string or "").strip()))
                else:
                    ret.append((c.string or "").strip())
            else:
                ret.append((c.string or "").strip())
        return ret

    @property
    def transcript_paragraphs(self):
        scripts = self._soup.find_all("script")
        matched = [ s.string for s in scripts if s.string and re.search("var slides", s.string) ]
        if not matched:
            raise Invalid("No slide variables... Try other page.")
        m = re.search("Array\\((.*)\\)", matched[0].string)
        if not m:
            raise Invalid("No slides in script... Try other page.")
        urls = [ re.match("\'(.*)\'", s).group(1) for s in m.group(1).split(",") ]
        return [ u"![slide](http://www.infoq.com{u})".format(u=u) for u in urls ]

    @property
    def body(self):
        return "\n\n".join(self.transcript_paragraphs)


# FIXME: Should be fetcher
class Fetcher(object):
    extractor_classes = [TedExtractor, InfoqInterviewExtractor, InfoqPresentationExtractor]

    def __init__(self, uri):
        self._uri = uri
        self._extactor = None

    def open(self, req):
        return urllib2.urlopen(req)

    
    @property
    def extractor(self):
        if not self._extactor:
            ecls = self._extractor_class_for(self._uri)
            html = self.open(urllib2.Request(self._uri, headers={ "User-Agent": "Gisted http://gisted.in/" })).read().decode(ecls.page_encoding)
            self._extactor = ecls(html)
        return self._extactor

    @property
    def post(self):
        return Post.make(self.extractor.title, self.extractor.body, self._uri)

    @classmethod
    def _extractor_class_for(cls, url):
        found = [ e for e in cls.extractor_classes if e.acceptable(url) ]
        return found[0] if found else None

    @classmethod
    def validate_supported(cls, mayurl):
        u = urlparse.urlparse(mayurl)
        if not (u.scheme and u.hostname):
            raise Invalid("Give me a URL!")
        if not cls._extractor_class_for(mayurl):
            raise Invalid("Sorry, but this site is not supported!: {url}".format(url=mayurl))
        
    @classmethod
    def make(cls, url):
        cls.validate_supported(url)
        return cls(url)


class GithubClient(object):
    BASE_URI = "https://api.github.com"

    def __init__(self, client_id, client_secret, token):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = token

    def build_request(self, path, data=None):
        url = urlparse.urljoin(self.BASE_URI, path)
        if self._token and self._token != FAKE_TOKEN:
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
            "public": False,
            "files": { 
                post.filename: {
                    "content": post.to_markdown()
                }
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
        if (req.get_full_url() == "hello-post.md"):
            return open(conf.data_path("hello-post.md"))
        if ("/gists/testshow" in req.get_full_url()):
            return open(conf.data_path("hello-post.json"))
        return urllib2.urlopen(req)

    def _get_raw_body(self, gist):
        raw_url = self._find_raw_url(gist)
        return self._open(urllib2.Request(raw_url)).read().decode('utf-8')
        
    def _get_contributor_url(self, gist):
        if not gist.get("user"):
            return None
        return gist["user"]["url"]

    def get(self, id):
        try:
            gist = json.load(self._open(self.build_request("/gists/{id}".format(id=id))))
            body = self._get_raw_body(gist)
            cont = self._get_contributor_url(gist)
            post = Post.parse(id, body)
            post.contributor_url = cont
            return post
        except urllib2.HTTPError, e:
            # XXX: Should be logged
            raise Invalid("An error occured on a remote API call...: gist:{id}".format(id=id))



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
        fetcher = self.fetcher_class.make(source_url)
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
        self._session["token"] = FAKE_TOKEN

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
