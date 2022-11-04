from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import Form, StringField, PasswordField, SubmitField, IntegerField, TextAreaField, FileField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional
)
#
#
# class RegistrationForm(FlaskForm):
#     first_name = StringField(
#         'Имя',
#         validators=[DataRequired()]
#     )
#     last_name = StringField(
#         'Фамилия',
#         validators=[DataRequired()]
#     )
#     phone = StringField(
#         'Телефон',
#         validators=[DataRequired()]
#     )
#     email = StringField(
#         'Email',
#         validators=[
#             Email(message='Enter a valid email.'),
#             DataRequired()
#         ]
#     )
#     password = PasswordField(
#         'Пароль',
#         validators=[
#             DataRequired(),
#             Length(min=6, message='Select a stronger password.')
#         ]
#     )
#
#
# class LoginForm(FlaskForm):
#     email = StringField(
#         'Логин',
#         validators=[
#             DataRequired(),
#             Email(message='Enter a valid email.')
#         ]
#     )
#     password = PasswordField('Пароль', validators=[DataRequired()])


class AddProduct(Form):
    title = StringField('Название', validators=[DataRequired()])
    author = StringField('Автор', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    publishing_office = StringField('Издательство', validators=[DataRequired()])
    series = StringField('Серия', validators=[DataRequired()])
    quantity = IntegerField('Количество на складе', default=1)
    price = IntegerField('Цена', validators=[DataRequired()])
    image = FileField('Обложка', validators=[FileRequired(), FileAllowed(['jpg', 'png', 'gif', 'jpeg'])])
