# -*- coding: utf-8 -*-

import werkzeug.serving
import gisted.web

app = gisted.web.app

if __name__ == '__main__':
    app.config['DEBUG'] = True
    werkzeug.serving.run_simple('localhost', 8000, app, use_debugger=True,  use_reloader=True, use_evalex=True)
