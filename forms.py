from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from flask_wtf.file import FileAllowed

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    steam_id = StringField('Steam ID или ссылка на профиль')
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль',
                                    validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class ProfileForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    steam_id = StringField('Steam ID или ссылка на профиль')
    avatar = FileField('Аватар',
                      validators=[FileAllowed(['jpg', 'png', 'gif'], 'Только изображения!')])
    submit = SubmitField('Обновить профиль')