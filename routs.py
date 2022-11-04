import re
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
# from flask_uploads import IMAGES, UploadSet
import os

from db_util import Database
from forms import AddProduct


base_directory = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config =

db = Database()

app.secret_key = 'bookspace-semester-project'
# app.permanent_session_lifetime = datetime.timedelta(days=365)


@app.route("/")
def main():
    is_authenticated = False
    if 'loggedin' in session:
        is_authenticated = True
    return render_template('shop/main.html', is_authenticated=is_authenticated)


@app.route('/catalog', defaults={'parent_id': None})
@app.route('/catalog/<parent_id>')
def get_catalog(parent_id):
    if parent_id:
        categories = db.select(f'SELECT * FROM category WHERE category_parent_id= %s', (parent_id,))
    else:
        categories = db.select('SELECT * FROM category WHERE category_parent_id is NULL')

    return render_template('shop/catalog.html', categories=categories)


@app.route('/product/<book_id>')
def get_book(book_id):
    return render_template('shop/sales.html')


@app.route('/sales')
def get_sales():
    return render_template('shop/sales.html')


@app.route('/new')
def get_new():
    return render_template('shop/new.html')


@app.route('/bestsellery')
def get_bestsellery():
    return render_template('shop/bestsellery.html')


@app.route('/best-price')
def get_best_price():
    return render_template('shop/best_price.html')


@app.route('/personal/profile')
def profile():
    return render_template('shop/profile.html')


@app.route('/delivery')
def delivery():
    return render_template('shop/delivery.html')


@app.route('/about-us')
def about_us():
    return render_template('shop/about_us.html')


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')

        _hashed_password = generate_password_hash(password)

        user = db.select('SELECT * FROM account WHERE email= %s', values=(email, ))
        phones = db.select('SELECT phone FROM account WHERE phone= %s', values=(phone, ))
        if user:
            flash('Аккаунт с таким email уже существует')
        elif phones:
            flash('Аккаунт с таким номером телефона уже существует')
        elif not re.match(r'^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$', phone):
            flash('Введите корректный номер телефона')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Введите корректный email')
        elif not first_name or not last_name or not password or not email:
            flash('Заполните все поля')
        else:
            db.insert_user(values=(first_name, last_name, phone, email, _hashed_password))
            user = db.select('SELECT * FROM account WHERE email= %s', values=(email, ))
            session['loggedin'] = True
            session['id'] = user['user_id']
            session['email'] = user['email']
            return redirect(url_for('main'))

    return render_template('shop/registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = db.select("SELECT * FROM account WHERE email= %s", values=(email, ))
        if user:
            password_rs = user['password']
            if check_password_hash(password_rs, password):
                session['loggedin'] = True
                session['id'] = user['user_id']
                session['email'] = user['email']
                return redirect(url_for('main'))

        flash('Incorrect username/password')
    return render_template('shop/authorization.html')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('email', None)
    return redirect(url_for('main'))


@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    form = AddProduct(request.form)

    return render_template('shop/product_form.html', form=form)


if __name__ == '__main__':
    print(base_directory)