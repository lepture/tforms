import tornado.web
import logging
from tornado.options import options
from forms import SignupForm


class BaseHandler(tornado.web.RequestHandler):
    _first_running = True

    def initialize(self):
        if BaseHandler._first_running:
            logging.info('First Running')
            BaseHandler._first_running = False

    def prepare(self):
        options.tforms_locale = self.locale


class SignupHandler(BaseHandler):
    def get(self):
        form = SignupForm()
        self.render('signup.html', form=form)

    def post(self):
        form = SignupForm(self.request.arguments)
        if form.validate():
            self.write('validate')
            return
        self.render('signup.html', form=form)


handlers = [
    ('/', SignupHandler),
]
