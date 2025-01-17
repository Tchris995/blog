from datetime import date

import flask
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm
from functools import wraps
from flask import abort
# from __future__ import annotations
from typing import List
from sqlalchemy import ForeignKey
from forms import CommentField
import os


'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('API_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)


# TODO: Configure Flask-Login
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URI', 'sqlite:///posts.db')
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="post")

    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # comment: Mapped['Comment'] = relationship(back_populates='text')
    post_comment: Mapped[List['Comment']] = relationship(back_populates='posted_comment')

    # author_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


# TODO: Create a User table for all your registered users.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post: Mapped[List["BlogPost"]] = relationship(back_populates="author")

    comment: Mapped[List['Comment']] = relationship(back_populates='c_author')
    name: Mapped[str] = mapped_column(String(1000))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(1000))


class Comment(db.Model):
    __tablename__ = 'comments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(10000), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    c_author: Mapped['User'] = relationship(back_populates='comment')
    post_id: Mapped['int'] = mapped_column(ForeignKey('blog_posts.id'))
    posted_comment: Mapped['BlogPost'] = relationship(back_populates='post_comment')


with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data

        result = User.query.filter_by(email=email).first()
        if not result:
            password = generate_password_hash(form.password.data, method='pbkdf2', salt_length=8)
            new_user = User()
            new_user.name = name
            new_user.email = email
            new_user.password = password

            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
        else:
            flask.flash('you\'ve already registered login please', 'error')
            return redirect(url_for('login', current_user=current_user))
    return render_template('register.html', form=form, current_user=current_user)

    # return render_template("register.html")


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        # user = User()
        # user.email = email
        # user.password=password
        result = User.query.filter_by(email=email).first()
        # print(result)
        # print(result.email)
        # user = result.scalar()
        # print(user)

        # if result and check:
        #     # flask.flash('login successful')
        #     login_user(result)
        #     return redirect(url_for('get_all_posts'))
        if not result:
            flash('invalid email address please try again', 'error')
            return redirect(url_for('login', current_user=current_user))
        else:
            check = check = check_password_hash(result.password, password)
        if not check:
            flash('invalid password please try again', 'error')
            return redirect(url_for('login', current_user=current_user))
        else:
            flask.flash('login successful')
            login_user(result)
            # me = current_user.id
            # print(me)

            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=['POST', 'GET'])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    comments = CommentField()
    if comments.validate_on_submit():
        if current_user.is_authenticated:

            new_comment = Comment()
            new_comment.text = comments.comment.data
            new_comment.posted_comment = requested_post
            new_comment.c_author = current_user
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash('login please', 'message')
            return redirect(url_for('login'))

    return render_template("post.html", post=requested_post, form=comments, current_user=current_user)


def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return func(*args, **kwargs)
        else:
            return abort(403, description='Access denied')

    return wrapper


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route('/comment')
def commented():
    pass


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html", )


if __name__ == "__main__":
    app.run(debug=False)
