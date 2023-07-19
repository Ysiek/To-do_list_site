from flask import Flask, render_template, url_for, redirect, flash, abort, request
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SubmitField
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import String, ForeignKey
import keyboard
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ['SECRET']
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///task.db'
db = SQLAlchemy(app)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)


class TaskForm(FlaskForm):
    task = StringField('', validators=[DataRequired()])


@app.route('/', methods=["GET", "POST"])
def home():
    db.create_all()
    with app.app_context():
        result = db.session.scalars(db.select(Task).order_by(Task.id.desc())).all()
    task_form = TaskForm()
    if request.method == "POST":
        with app.app_context():
            new_task = Task(
                description=task_form.task.data
            )
            task_form.task.data = ''
            db.session.add(new_task)
            db.session.commit()
            return redirect(url_for('home'))
    return render_template('index.html', task_form=task_form, tasks=result)


if __name__ == '__main__':
    app.run(debug=True)
