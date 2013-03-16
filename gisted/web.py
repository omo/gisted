# -*- coding: utf-8 -*-

import os
import flask
import re
import gisted.tools as tools
import gisted.conf as conf
import gisted.session as session
import flask as f
import jinja2
import logging
import urlparse

template_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")

app = flask.Flask(__name__, template_folder = template_dir, static_folder = static_dir)
app.secret_key = conf.credential("flask_secret_key")
app.session_interface = session.SessionInterface(app.secret_key[:8])

def redirect_index_with_error(error):
    f.flash(error.message, "error")
    return f.redirect(f.url_for("index"))

def redirect_to_secure(url):
    urlparse.urlparse(url)
    return f.redirect(url)

def to_gist_id_from_url_if_possible(url):
    if not url:
        return None
    m = re.match("https://gist.github.com/[^/]+/([a-zA-Z0-9]+)", url)
    if not m:
        return None
    return m.group(1)

@app.template_filter('markdown')
def markdown_filter(text):
    mk = jinja2.Markup
    m = re.search("^\\*(.*)\\*$", text, re.S)
    if m:
        return mk(u"<em>") + jinja2.escape(m.group(1)) + mk(u"</em>")
    m = re.search("^\\!\\[(.*)\\]\\((.*)\\)$", text, re.S)
    if m:
        title = m.group(1)
        url = m.group(2)
        if urlparse.urlparse(url).scheme not in [ "http", "https" ]:
            return text
        if url.endswith("swf"):
            return mk(u"<embed class='paragraph-image' src='") + jinja2.escape(url) + mk(u"' ><embed>")
        else:
            return mk(u"<img class='paragraph-image' src='") + jinja2.escape(url) + mk(u"' title='") + jinja2.escape(title) + mk(u"' />")
    return text

@app.route('/', methods=["GET", "POST"])
def index():
    auth = tools.Auth.make(f.session)
    if f.request.method == "GET":
        u = (f.request.values.get("u") or "") if auth.authenticated else ""
        return f.render_template("index.html", auth=auth, u=u)
    else:
        if auth.canary != f.request.values["canary"]:
            return f.abort(403)
        if not auth.allows_pasting:
            return f.abort(403)
        try:
            source = f.request.values["u"].strip()
            maybe_id = to_gist_id_from_url_if_possible(source)
            if maybe_id:
                return redirect_to_secure(f.url_for("show", id=maybe_id))
            paster = tools.Paster.make(auth.token)
            paster.paste_from(source)
            return redirect_to_secure(f.url_for("show", id=paster.created_id))
        except tools.Invalid, e:
            return redirect_index_with_error(e)

@app.route('/<id>')
def show(id):
    loader = tools.Downloader.make(tools.Auth.make(f.session).token)
    try:
        post = loader.get(id)
        return f.render_template("show.html", post=post)
    except tools.Invalid, e:
        return redirect_index_with_error(e)

if conf.enable_debug_pages:
    @app.route('/debug_upload', methods=["GET", "POST"])
    def debug_upload():
        if f.request.method == "GET":
            return f.render_template("debug_upload.html")
        else:
            auth = tools.Auth.make(f.session)
            post = tools.Post(gist_id=None, 
                              source_url=f.request.values["source"],
                              title=f.request.values["title"],
                              body=f.request.values["body"])
            u = tools.Uploader.make(auth.token)
            u.upload(post)
            return "<a href='{url}'>{id}</a>".format(url=u.created_page_url, id=u.created_id)

@app.route('/debug_token', methods=["GET", "POST"])
def debug_token():
    auth = tools.Auth.make(f.session)
    if not conf.enable_debug_pages and not auth.is_admin_user:
        return f.abort(403)

    if f.request.method == "GET":
        return f.render_template("debug_token.html", auth=auth)
    else:
        if auth.canary != f.request.values["canary"]:
            return f.abort(403)
        auth.token = f.request.values["token"]
        return f.redirect(f.url_for("index"))


@app.route('/favicon.ico')
def favicon():
    return app.send_static_file("favicon.ico")

#
# Authentication
#
@app.route('/login')
def login():
    return f.redirect(tools.Auth.make(f.session).redirect_url)

@app.route('/logback')
def logback():
    auth = tools.Auth.make(f.session)
    auth.did_come_back(f.request.args)
    return f.redirect("/")

@app.route('/logout')
def logout():
    f.session.clear()
    return f.redirect("/")

if conf.enable_debug_pages:
    @app.route('/debug_login')
    def debug_login():
        tools.Auth.make(f.session).fake_login()
        return f.redirect("/")
