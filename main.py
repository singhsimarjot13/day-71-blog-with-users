from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash,request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user,login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
import  sqlalchemy.exc
# Import your forms from the forms.py
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm


'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.

'''
login_=LoginManager()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRETKEY')
ckeditor = CKEditor(app)
Bootstrap5(app)
login_.init_app(app)

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
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB')
db = SQLAlchemy(model_class=Base)
db.init_app(app)

@login_.user_loader
def load_user(user_id):
    return db.get_or_404(User,user_id)
# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author = relationship("User", back_populates="posts")
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


# TODO: Create a User table for all your registered users.
class User(UserMixin,db.Model):
    __tablename__='users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email:Mapped[str]=mapped_column(String,unique=True,nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String,nullable=False)
    posts=relationship('BlogPost',back_populates='author')
    comments = relationship("Comment", back_populates="comment_author")

class Comment(db.Model):
    __tablename__='comments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")





with app.app_context():
    db.create_all()

def admin_only(f):
    @wraps(f)
    def wrapper_function(*args,**kwargs):
        if current_user.id==1:
            return f(*args,**kwargs)
        else:
            abort(403)
    return wrapper_function
# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm()
    if request.method=='POST':
        email=request.form.get('email')
        password=request.form.get('password')
        name=request.form.get('name')
        result = db.session.execute(db.select(User).where(User.email == email))
        # Note, email in db is unique so will only have one result.
        user = result.scalar()
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        password=generate_password_hash(password,method='pbkdf2:sha256',salt_length=8)
        result=User(
            email=email,
            password=password,
            name=name
        )
        try:
         db.session.add(result)
         db.session.commit()
        except sqlalchemy.exc.IntegrityError as e:
            # Handle the IntegrityError here
            print("IntegrityError occurred:", e)
        return redirect(url_for('login'))
    return render_template("register.html",form=form, current_user=current_user)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login',methods=['GET','POST'])
def login():
    login_userr=LoginForm()
    if request.method=='POST':
        email=request.form.get('email')
        password=request.form.get('password')
        check=db.session.execute(db.select(User).where(User.email==email)).scalar()
        if check:
            if check_password_hash(check.password,password):
                login_user(check)
                return redirect(url_for('get_all_posts'))
            else:
                flash('wrong password!please try again!')
        else:
            flash('wrong email!please try again.')
    return render_template("login.html",form=login_userr, current_user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>",methods=['GET','POST'])
def show_post(post_id):
    commentform=CommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)
    if commentform.validate_on_submit() and request.method=='POST':
        if current_user.is_authenticated:
            comment=request.form.get('body')
            add_comment=Comment(
                text=comment,
            author_id = current_user.id,
                post_id=requested_post.id
            )
            db.session.add(add_comment)
            db.session.commit()
        else:
            flash("You need to login or register to comment")
            return redirect(url_for('login'))
    return render_template("post.html", post=requested_post, current_user=current_user,form=commentform)


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
@app.route("/edit-post/<int:postid>", methods=["GET", "POST"])
@admin_only
def edit_postss(postid):
    post =db.session.execute(db.select(BlogPost).where(BlogPost.id==postid)).scalar()
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
        return redirect(url_for("show_post",post_id=postid))
    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
