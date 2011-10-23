
from tornado.escape import to_unicode
from tforms import Field, StopValidation, html_params

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
        return '<input %s>' % html_params(name=field.name, **kwargs)


class TextField(Field):
    """
    This field is the base for most of the more complicated fields, and
    represents an ``<input type="text">``.
    """

    widget = Input()

    def __init__(self, required=False, maxlength=None, **kwargs):
        super(TextField, self).__init__(**kwargs)
        self.maxlength = maxlength
        self.required = required

    def __call__(self, **kwargs):
        if self.maxlength:
            kwargs['maxlength'] = str(self.maxlength)
        return self.widget(self, **kwargs)

    def pre_validate(self, form):
        if self.maxlength and len(self.data) > self.maxlength:
            raise StopValidation(self.translate("Field cannot be longer than %d characters",self.maxlength))
        if self.required and not self.data:
            raise StopValidation(self.translate("This field is required"))

    def _value(self):
        if self.data:
            return to_unicode(self.data)
        return to_unicode('')
