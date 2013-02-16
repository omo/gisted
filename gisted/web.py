# -*- coding: utf-8 -*-

import os
import flask
import gisted.tools as tools
import flask as f

template_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")

app = flask.Flask(__name__, template_folder = template_dir, static_folder = static_dir)
app.gist = tools.Gist.make()

@app.route('/')
def index():
    return "Hello"

@app.route('/<id>')
def show(id):
    post = app.gist.get(id)
    return f.render_template("show.html", post=post)
