from tforms import validators
from tforms.fields import TextField, PasswordField
from tforms.forms import TornadoForm as Form
from tforms.validators import ValidationError


class SignupForm(Form):
    username = TextField(
        'Username', [
            validators.Required(),
            validators.Length(min=4, max=16),
            validators.Regexp(
                '[a-zA-Z0-9-]',
                message='Username can only contain characters and digits',
            ),
        ],
        description='Username can only contain English characters and digits'
    )
    email = TextField(
        'Email', [
            validators.Required(),
            validators.Length(min=4, max=30),
            validators.Email(),
        ],
        description='Please active your account after registration'
    )
    password = PasswordField(
        'Password', [
            validators.Required(),
            validators.Length(min=6),
        ],
        description='Password must be longer than 6 characters'
    )
    password2 = PasswordField(
        'Confirm', [
            validators.Required(),
            validators.Length(min=6),
        ]
    )

    def validate_password(form, field):
        if field.data != form.password2.data:
            raise ValidationError("Passwords don't match")
