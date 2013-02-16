# -*- coding: utf-8 -*-

import os
import flask
import gisted.tools as tools
import gisted.conf as conf
import flask as f
import logging

template_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")

app = flask.Flask(__name__, template_folder = template_dir, static_folder = static_dir)
app.secret_key = conf.credential("flask_secret_key")

@app.route('/', methods=["GET", "POST"])
def index():
    auth = tools.Auth.make(f.session)
    #auth.allows_anonymous = True
    if f.request.method == "GET":
        return f.render_template("index.html", auth=auth)
    elif f.request.method == "POST":
        if auth.canary != f.request.values["canary"]:
            return f.abort(403)
        if not auth.allows_pasting:
            return f.abort(403)
        source = f.request.values["u"]
        paster = tools.Paster.make(auth.token)
        paster.paste_from(source)
        return f.redirect(f.url_for("show", id=paster.created_id))
    else:
        return f.abort(403)

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file("favicon.ico")

@app.route('/<id>')
def show(id):
    loader = tools.Downloader.make(tools.Auth.make(f.session).token)
    post = loader.get(id)
    return f.render_template("show.html", post=post)


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

@app.route('/debug_login')
def debug_login():
    tools.Auth.make(f.session).fake_login()
    return f.redirect("/")
