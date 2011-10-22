
from tornado.escape import to_unicode
from tforms import Field, html_params

class Input(object):
    """
    Render a basic ``<input>`` field.

    This is used as the basis for most of the other input fields.

    By default, the `_value()` method will be called upon the associated field
    to provide the ``value=`` HTML attribute.
    """

    input_type = 'text'

    def __init__(self, input_type=None):
        if input_type is not None:
            self.input_type = input_type

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('type', self.input_type)
        if 'value' not in kwargs:
            kwargs['value'] = field._value()
        return '<input %s>' % self.html_params(name=field.name, **kwargs)


class TextField(Field):
    """
    This field is the base for most of the more complicated fields, and
    represents an ``<input type="text">``.
    """

    widget = Input()
