from flask import Flask, render_template, url_for, redirect, flash, abort, request
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap
from wtforms import StringField, EmailField, PasswordField, SubmitField
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import os
import time

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ['SECRET']
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///task.db'
db = SQLAlchemy(app)
Bootstrap(app)

# LOGIN CONFIG
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.scalars(db.select(User).where(User.id == user_id)).first()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)

    user = relationship('List', back_populates='user')
    user_who_create = relationship('Task', back_populates='user')


class List(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_of_list = db.Column(db.String(255), nullable=True)

    # RELATIONSHIP WITH USER
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User', back_populates='user')

    # RELATIONSHIP WITH TASK
    list = relationship('Task', back_populates='list')


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Integer, nullable=False)
    star = db.Column(db.Integer, nullable=False)

    # RELATIONSHIP WITH USER
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User', back_populates='user_who_create')

    # RELATIONSHIP WITH LIST
    list_id = db.Column(db.Integer, db.ForeignKey('list.id'))
    list = relationship('List', back_populates='list')


class Sign_up_form(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit", validators=[DataRequired()])


class Login_form(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit", validators=[DataRequired()])


class TaskForm(FlaskForm):
    task = StringField('', validators=[DataRequired()])


@app.route('/', methods=["GET", "POST"])
def home():
    db.create_all()
    task_form = TaskForm()
    all_tasks = None
    tasks_with_star = None
    user_list = None
    if current_user.is_authenticated:
        with app.app_context():
            user_list = db.session.scalars(db.select(List).where(current_user.id == List.id)).first()
        if request.method == "POST":
            with app.app_context():
                new_task = Task(
                    description=task_form.task.data,
                    is_done=0,
                    star=0,
                    user_id=current_user.id,
                    list_id=user_list.id
                )
                task_form.task.data = ''
                db.session.add(new_task)
                db.session.commit()
        tasks_with_star = db.session.scalars(db.select(Task).where(Task.user_id == current_user.id, Task.star == 1).order_by(Task.id.asc())).all()
        result = db.session.scalars(db.select(Task).where(Task.user_id == current_user.id, Task.star == 0).order_by(Task.id.desc())).all()
        all_tasks = tasks_with_star + result
    return render_template('index.html', task_form=task_form, tasks=all_tasks, user=current_user,
                           logged_in=current_user.is_authenticated, user_list=user_list)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = Login_form()
    if form.validate_on_submit():
        user_to_login = db.session.scalars(db.select(User).where(User.email == form.email.data)).first()
        if not user_to_login:
            return render_template('login.html', form=form)
        if check_password_hash(user_to_login.password, form.password.data):
            login_user(user_to_login)
            return redirect(url_for('home'))
    return render_template('login.html', form=form)


@app.route('/sign-up', methods=["GET", "POST"])
def sign_up():
    form = Sign_up_form()
    if form.validate_on_submit():
        with app.app_context():
            new_user = User(
                email=form.email.data,
                name=form.name.data,
                password=generate_password_hash(form.password.data, "pbkdf2", 8)
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            new_list = List(
                name_of_list=time.strftime('%Y-%m-%d'),
                user_id=current_user.id,
            )
            db.session.add(new_list)
            db.session.commit()
            return redirect(url_for('home'))
    return render_template('sign-up.html', form=form)

@login_required
@app.route('/add-list/<int:user_id>')
def create_new_list(user_id):
    with app.app_context():
        previous_list = db.session.scalars(db.select(List).where(List.user_id == user_id)).first()
        tasks_of_previous_list = db.session.scalars(db.select(Task).where(Task.list_id == previous_list.id)).all()

        for tasks in tasks_of_previous_list:
            db.session.delete(tasks)
        db.session.delete(previous_list)
        db.session.commit()

        new_list = List(
            name_of_list=time.strftime('%Y-%m-%d'),
            user_id=user_id,
        )
        db.session.add(new_list)
        db.session.commit()
    return redirect(url_for('home'))

@login_required
@app.route('/done-task/<int:task_id>/<int:is_done>')
def done_task(task_id, is_done):
    task = db.session.scalars(db.select(Task).where(Task.id == task_id)).first()
    if is_done == 0:
        task.is_done = 1
    else:
        task.is_done = 0
    db.session.commit()
    return redirect(url_for('home'))

@login_required
@app.route('/star/<int:task_id>/<int:is_star>')
def star(task_id, is_star):
    task = db.session.scalars(db.select(Task).where(Task.id == task_id)).first()
    if is_star == 0:
        task.star = 1
    else:
        task.star = 0
    db.session.commit()
    return redirect(url_for('home'))



@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/delete/<int:task_id>")
def delete(task_id):
    with app.app_context():
        task_to_delete = db.session.scalars(db.select(Task).where(Task.id == task_id)).first()
        db.session.delete(task_to_delete)
        db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
