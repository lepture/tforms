
import re
import itertools
from tornado.escape import to_unicode, utf8, xhtml_escape

__all__ ['BaseForm', 'Form', 'ValidationError', 'StopValidation', 'html_params', 'Field']

class BaseForm(object):
    """
    Base Form Class.  Provides core behaviour like field construction,
    validation, and data and error proxying.
    """

    def __init__(self, fields, prefix=''):
        """
        :param fields:
            A dict or sequence of 2-tuples of partially-constructed fields.
        :param prefix:
            If provided, all fields will have their name prefixed with the
            value.
        """
        if prefix and prefix[-1] not in '-_;:/.':
            prefix += '-'

        self._prefix = prefix
        self._errors = None
        self._fields = {}

        if hasattr(fields, 'iteritems'):
            fields = fields.iteritems()

        locale = self._get_locale()

        for name, unbound_field in fields:
            field = unbound_field.bind(form=self, name=name, prefix=prefix, locale=locale)
            self._fields[name] = field

    def __iter__(self):
        """ Iterate form fields in arbitrary order """
        return self._fields.itervalues()

    def __contains__(self, item):
        """ Returns `True` if the named field is a member of this form. """
        return (item in self._fields)

    def __getitem__(self, name):
        """ Dict-style access to this form's fields."""
        return self._fields[name]

    def __setitem__(self, name, value):
        """ Bind a field to this form. """
        self._fields[name] = value.bind(form=self, name=name, prefix=self._prefix)

    def __delitem__(self, name):
        """ Remove a field from this form. """
        del self._fields[name]

    def _get_locale(self):
        """
        Override in subclasses to provide alternate translations factory.

        Must return an object that provides gettext() and ngettext() methods.
        """
        return None

    def populate_obj(self, obj):
        """
        Populates the attributes of the passed `obj` with data from the form's
        fields.

        :note: This is a destructive operation; Any attribute with the same name
               as a field will be overridden. Use with caution.
        """
        for name, field in self._fields.iteritems():
            field.populate_obj(obj, name)

    def process(self, formdata=None, obj=None, **kwargs):
        """
        Take form, object data, and keyword arg input and have the fields
        process them.

        :param formdata:
            Used to pass data coming from the enduser, usually `request.POST` or
            equivalent.
        :param obj:
            If `formdata` has no data for a field, the form will try to get it
            from the passed object.
        :param `**kwargs`:
            If neither `formdata` or `obj` contains a value for a field, the
            form will assign the value of a matching keyword argument to the
            field, if provided.
        """
        if formdata is not None and not hasattr(formdata, 'getlist'):
            formdata = _TornadoArgumentsWrapper(formdata)

        for name, field, in self._fields.iteritems():
            if obj is not None and hasattr(obj, name):
                field.process(formdata, getattr(obj, name))
            elif name in kwargs:
                field.process(formdata, kwargs[name])
            else:
                field.process(formdata)

    def validate(self, extra_validators=None):
        """
        Validates the form by calling `validate` on each field.

        :param extra_validators:
            If provided, is a dict mapping field names to a sequence of
            callables which will be passed as extra validators to the field's
            `validate` method.

        Returns `True` if no errors occur.
        """
        self._errors = None
        success = True
        for name, field in self._fields.iteritems():
            if extra_validators is not None and name in extra_validators:
                extra = extra_validators[name]
            else:
                extra = tuple()
            if not field.validate(self, extra):
                success = False
        return success

    @property
    def data(self):
        return dict((name, f.data) for name, f in self._fields.iteritems())

    @property
    def errors(self):
        if self._errors is None:
            self._errors = dict((name, f.errors) for name, f in self._fields.iteritems() if f.errors)
        return self._errors

class FormMeta(type):
    """
    The metaclass for `Form` and any subclasses of `Form`.

    `FormMeta`'s responsibility is to create the `_unbound_fields` list, which
    is a list of `UnboundField` instances sorted by their order of
    instantiation.  The list is created at the first instantiation of the form.
    If any fields are added/removed from the form, the list is cleared to be
    re-generated on the next instantiaton.

    Any properties which begin with an underscore or are not `UnboundField`
    instances are ignored by the metaclass.
    """
    def __init__(cls, name, bases, attrs):
        type.__init__(cls, name, bases, attrs)
        cls._unbound_fields = None

    def __call__(cls, *args, **kwargs):
        """
        Construct a new `Form` instance, creating `_unbound_fields` on the
        class if it is empty.
        """
        if cls._unbound_fields is None:
            fields = []
            for name in dir(cls):
                if not name.startswith('_'):
                    unbound_field = getattr(cls, name)
                    if hasattr(unbound_field, '_formfield'):
                        fields.append((name, unbound_field))
            # We keep the name as the second element of the sort
            # to ensure a stable sort.
            fields.sort(key=lambda x: (x[1].creation_counter, x[0]))
            cls._unbound_fields = fields
        return type.__call__(cls, *args, **kwargs)

    def __setattr__(cls, name, value):
        """
        Add an attribute to the class, clearing `_unbound_fields` if needed.
        """
        if not name.startswith('_') and hasattr(value, '_formfield'):
            cls._unbound_fields = None
        type.__setattr__(cls, name, value)

    def __delattr__(cls, name):
        """
        Remove an attribute from the class, clearing `_unbound_fields` if
        needed.
        """
        if not name.startswith('_'):
            cls._unbound_fields = None
        type.__delattr__(cls, name)

class Form(BaseForm):
    """
    Declarative Form base class. Extends BaseForm's core behaviour allowing
    fields to be defined on Form subclasses as class attributes.

    In addition, form and instance input data are taken at construction time
    and passed to `process()`.
    """
    __metaclass__ = FormMeta

    def __init__(self, handler=None, obj=None, prefix='', **kwargs):
        """
        :param handler:
            Used to pass handler, usually `self`.
        :param obj:
            If `handler.request.arguments` has no data for a field, the form
            will try to get it from the passed object.
        :param prefix:
            If provided, all fields will have their name prefixed with the
            value.
        :param `**kwargs`:
            If neither `formdata` or `obj` contains a value for a field, the
            form will assign the value of a matching keyword argument to the
            field, if provided.
        """
        super(Form, self).__init__(self._unbound_fields, prefix=prefix)

        for name, field in self._fields.iteritems():
            # Set all the fields to attributes so that they obscure the class
            # attributes with the same names.
            setattr(self, name, field)

        self.process(handler.request.arguments, obj, **kwargs)
        self.handler = handler
        self.obj = obj

    def __iter__(self):
        """ Iterate form fields in their order of definition on the form. """
        for name, _ in self._unbound_fields:
            if name in self._fields:
                yield self._fields[name]

    def __setitem__(self, name, value):
        raise TypeError('Fields may not be added to Form instances, only classes.')

    def __delitem__(self, name):
        del self._fields[name]
        setattr(self, name, None)

    def __delattr__(self, name):
        try:
            self.__delitem__(name)
        except KeyError:
            super(Form, self).__delattr__(name)

    def _get_locale(self):
        return self.handler.locale

    def validate(self):
        """
        Validates the form by calling `validate` on each field, passing any
        extra `Form.validate_<fieldname>` validators to the field validator.
        """
        extra = {}
        for name in self._fields:
            inline = getattr(self.__class__, 'validate_%s' % name, None)
            if inline is not None:
                extra[name] = [inline]

        return super(Form, self).validate(extra)

class ValidationError(ValueError):
    """
    Raised when a validator fails to validate its input.
    """
    def __init__(self, message=None, *args, **kwargs):
        ValueError.__init__(self, to_unicode(message), *args, **kwargs)

class StopValidation(Exception):
    """
    Causes the validation chain to stop.

    If StopValidation is raised, no more validators in the validation chain are
    called. If raised with a message, the message will be added to the errors
    list.
    """
    def __init__(self, message=None, *args, **kwargs):
        Exception.__init__(self, to_unicode(message), *args, **kwargs)


def html_params(**kwargs):
    """
    Generate HTML parameters from inputted keyword arguments.

    The output value is sorted by the passed keys, to provide consistent output
    each time this function is called with the same parameters.  Because of the
    frequent use of the normally reserved keywords `class` and `for`, suffixing
    these with an underscore will allow them to be used.

    >>> html_params(name='text1', id='f', class_='text')
    'class="text" id="f" name="text1"'
    """
    params = []
    for k,v in sorted(kwargs.iteritems()):
        if k in ('class_', 'for_'):
            k = k[:-1]
        if v is True:
            params.append(k)
        else:
            params.append('%s="%s"' % (to_unicode(k), xhtml_escape(to_unicode(v))))
    return ' '.join(params)

_unset_value = object()
class Field(object):
    """
    Field base class
    """
    widget = None
    errors = tuple()
    process_errors = tuple()
    _formfield = True
    _locale = _DummyLocale()

    def __new__(cls, *args, **kwargs):
        if '_form' in kwargs and '_name' in kwargs:
            return super(Field, cls).__new__(cls)
        else:
            return UnboundField(cls, *args, **kwargs)

    def __init__(self, label=None, validators=None, filters=tuple(),
                 description='', id=None, default=None, widget=None,
                 _form=None, _name=None, _prefix='fm-', _locale=None):
        """
        Construct a new field.

        :param label:
            The label of the field. 
        :param validators:
            A sequence of validators to call when `validate` is called.
        :param filters:
            A sequence of filters which are run on input data by `process`.
        :param description:
            A description for the field, typically used for help text.
        :param id:
            An id to use for the field. A reasonable default is set by the form,
            and you shouldn't need to set this manually.
        :param default:
            The default value to assign to the field, if no form or object
            input is provided. May be a callable.
        :param widget:
            If provided, overrides the widget used to render the field.
        :param _form:
            The form holding this field. It is passed by the form itself during
            construction. You should never pass this value yourself.
        :param _name:
            The name of this field, passed by the enclosing form during its
            construction. You should never pass this value yourself.
        :param _prefix:
            The prefix to prepend to the form name of this field, passed by
            the enclosing form during construction.

        If `_form` and `_name` isn't provided, an :class:`UnboundField` will be
        returned instead. Call its :func:`bind` method with a form instance and
        a name to construct the field.
        """
        self.short_name = _name
        self.name = _prefix + _name
        if _locale is not None:
            self._locale = _locale
        self.id = id or self.name
        if label is None:
            label = _name.replace('_', ' ').title()
        self.label = Label(self.id, label) 
        if validators is None:
            validators = []
        self.validators = validators
        self.filters = filters
        self.description = to_unicode(description)
        self.type = type(self).__name__
        self.default = default
        self.raw_data = None
        if widget:
            self.widget = widget

    def __unicode__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the `__call__` method.
        """
        return self()

    def __str__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the `__call__` method.
        """
        return utf8(self())

    def __call__(self, **kwargs):
        """
        Render this field as HTML, using keyword args as additional attributes.

        Any HTML attribute passed to the method will be added to the tag
        and entity-escaped properly.
        """
        return self.widget(self, **kwargs)

    def translate(self, message, plural_message=None, count=None):
        return self._locale.translate(message, plural_message, count)

    def validate(self, form, extra_validators=tuple()):
        """
        Validates the field and returns True or False. `self.errors` will
        contain any errors raised during validation. This is usually only
        called by `Form.validate`.

        Subfields shouldn't override this, but rather override either
        `pre_validate`, `post_validate` or both, depending on needs.

        :param form: The form the field belongs to.
        :param extra_validators: A list of extra validators to run.
        """
        self.errors = list(self.process_errors)
        stop_validation = False

        # Call pre_validate
        try:
            self.pre_validate(form)
        except StopValidation as e:
            if e.args and e.args[0]:
                self.errors.append(self.translate(e.args[0]))
            stop_validation = True
        except ValueError as e:
            self.errors.append(self.translate(e.args[0]))

        # Run validators
        if not stop_validation:
            for validator in itertools.chain(self.validators, extra_validators):
                try:
                    validator(form, self)
                except StopValidation as e:
                    if e.args and e.args[0]:
                        self.errors.append(self.translate(e.args[0]))
                    stop_validation = True
                    break
                except ValueError as e:
                    self.errors.append(self.translate(e.args[0]))

        # Call post_validate
        try:
            self.post_validate(form, stop_validation)
        except ValueError as e:
            self.errors.append(self.translate(e.args[0]))

        return len(self.errors) == 0

    def pre_validate(self, form):
        """
        Override if you need field-level validation. Runs before any other
        validators.

        :param form: The form the field belongs to.
        """
        pass

    def post_validate(self, form, validation_stopped):
        """
        Override if you need to run any field-level validation tasks after
        normal validation. This shouldn't be needed in most cases.

        :param form: The form the field belongs to.
        :param validation_stopped:
            `True` if any validator raised StopValidation.
        """
        pass

    def process(self, formdata, data=_unset_value):
        """
        Process incoming data, calling process_data, process_formdata as needed,
        and run filters.

        If `data` is not provided, process_data will be called on the field's
        default.

        Field subclasses usually won't override this, instead overriding the
        process_formdata and process_data methods. Only override this for
        special advanced processing, such as when a field encapsulates many
        inputs.
        """
        self.process_errors = []
        if data is _unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default
        try:
            self.process_data(data)
        except ValueError as e:
            self.process_errors.append(self.translate(e.args[0]))

        if formdata:
            try:
                if self.name in formdata:
                    self.raw_data = formdata.getlist(self.name)
                else:
                    self.raw_data = []
                self.process_formdata(self.raw_data)
            except ValueError as e:
                self.process_errors.append(self.translate(e.args[0]))

        for _filter in self.filters:
            try:
                self.data = _filter(self.data)
            except ValueError as e:
                self.process_errors.append(self.translate(e.args[0]))

    def process_data(self, value):
        """
        Process the Python data applied to this field and store the result.

        This will be called during form construction by the form's `kwargs` or
        `obj` argument.

        :param value: The python object containing the value to process.
        """
        self.data = value

    def process_formdata(self, valuelist):
        """
        Process data received over the wire from a form.

        This will be called during form construction with data supplied
        through the `formdata` argument.

        :param valuelist: A list of strings to process.
        """
        if valuelist:
            self.data = to_unicode(valuelist[0])
        else:
            self.data = to_unicode(None)

    def populate_obj(self, obj, name):
        """
        Populates `obj.<name>` with the field's data.

        :note: This is a destructive operation. If `obj.<name>` already exists,
               it will be overridden. Use with caution.
        """
        setattr(obj, name, self.data)

    def _value(self):
        return to_unicode(self.data)


class UnboundField(object):
    _formfield = True
    creation_counter = 0

    def __init__(self, field_class, *args, **kwargs):
        UnboundField.creation_counter += 1
        self.field_class = field_class
        self.args = args
        self.kwargs = kwargs
        self.creation_counter = UnboundField.creation_counter

    def bind(self, form, name, prefix='', locale=None, **kwargs):
        return self.field_class(_form=form, _prefix=prefix, _name=name, _locale=locale, *self.args, **dict(self.kwargs, **kwargs))

    def __repr__(self):
        return '<UnboundField(%s, %r, %r)>' % (self.field_class.__name__, self.args, self.kwargs)

class Label(object):
    """
    An HTML form label.
    """
    def __init__(self, field_id, text):
        self.field_id = field_id
        self.text = text

    def __str__(self):
        return utf8(self())

    def __unicode__(self):
        return self()

    def __call__(self, text=None, **kwargs):
        kwargs['for'] = self.field_id
        attributes = html_params(**kwargs)
        return '<label %s>%s</label>' % (attributes, to_unicode(text) or to_unicode(self.text))

    def __repr__(self):
        return 'Label(%r, %r)' % (self.field_id, self.text)


class _TornadoArgumentsWrapper(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError

    def getlist(self, key):
        try:
            values = []
            for v in self[key]:
                v = to_unicode(v)
                if isinstance(v, unicode):
                    v = re.sub(r"[\x00-\x08\x0e-\x1f]", " ", v)
                values.append(v)
            return values
        except KeyError:
            raise AttributeError


class _DummyLocale(object):
    def translate(self, message, plural_message=None, count=None):
        if plural_message is not None:
            assert count is not None
            return plural_message
        return message

