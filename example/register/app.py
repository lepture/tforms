#!/usr/bin/env python

import os

rootdir = os.path.abspath(os.path.dirname(__file__))
import site
projdir = os.path.split(rootdir)[0]
site.addsitedir(projdir)

import tornado.options
import tornado.locale
from tornado.options import define, options
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado import web
os.environ['TZ'] = 'UTC'

define('port', default=8000, type=int)


class Application(web.Application):
    def __init__(self):
        from handlers import handlers
        settings = dict(
            debug=True,
            autoescape=None,
            template_path=os.path.join(rootdir, "templates"),
            static_path=os.path.join(projdir, "static"),
        )
        super(Application, self).__init__(handlers, **settings)
        tornado.locale.load_translations(os.path.join(rootdir, "locale"))
        #tornado.locale.set_default_locale('zh_CN')


def run_server():
    tornado.options.parse_command_line()
    server = HTTPServer(Application(), xheaders=True)
    server.bind(int(options.port))
    server.start(1)
    IOLoop.instance().start()


if __name__ == "__main__":
    run_server()
