# -*- coding: utf-8 -*-

import os
import flask
import gisted.tools as tools
import gisted.conf as conf
import gisted.session as session
import flask as f
import logging

template_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")

app = flask.Flask(__name__, template_folder = template_dir, static_folder = static_dir)
app.secret_key = conf.credential("flask_secret_key")
app.session_interface = session.SessionInterface(app.secret_key[:8])

@app.route('/', methods=["GET", "POST"])
def index():
    auth = tools.Auth.make(f.session)
    if f.request.method == "GET":
        return f.render_template("index.html", auth=auth)
    else:
        if auth.canary != f.request.values["canary"]:
            return f.abort(403)
        if not auth.allows_pasting:
            return f.abort(403)
        paster = tools.Paster.make(auth.token)
        try:
            source = f.request.values["u"].strip()
            paster.paste_from(source)
            return f.redirect(f.url_for("show", id=paster.created_id))
        except tools.Invalid, e:
            f.flash(e.message, "error")
            return f.redirect(f.url_for("index"))

@app.route('/<id>')
def show(id):
    loader = tools.Downloader.make(tools.Auth.make(f.session).token)
    post = loader.get(id)
    return f.render_template("show.html", post=post)

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
