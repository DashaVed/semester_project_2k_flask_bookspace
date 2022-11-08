import re
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_uploads import IMAGES, UploadSet, configure_uploads, patch_request_class
import os
import secrets

from db_util import Database
from forms import AddProduct, RegistrationForm

base_directory = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(os.path.join(base_directory, 'static'), 'img')
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app)

db = Database()

app.secret_key = 'bookspace-semester-project'
app.permanent_session_lifetime = datetime.timedelta(days=365)

def is_authenticated():
    return True if 'loggedin' in session else False


def is_admin():
    if is_authenticated():
        return True if session['id'] == '4' else False


@app.route("/")
def main():
    return render_template('shop/main.html', is_authenticated=is_authenticated(), is_admin=is_admin())


@app.route('/catalog', defaults={'parent_id': None})
@app.route('/catalog/<parent_id>')
def get_catalog(parent_id):
    if parent_id:
        categories = db.select(f'SELECT * FROM category WHERE category_parent_id= %s', (parent_id,))
    else:
        categories = db.select('SELECT * FROM category WHERE category_parent_id is NULL')
    products = db.select('SELECT * FROM product')

    return render_template('shop/catalog.html', categories=categories, products=products)


@app.route('/product/<book_id>')
def get_book(book_id):
    book = db.select('SELECT * FROM product WHERE product_id = %s', (book_id,))
    return render_template('shop/book.html', book=book)


@app.route('/personal/profile', methods=['GET', 'POST'])
def profile():
    is_auth = is_authenticated()
    if is_auth:
        user = db.select('SELECT * FROM account WHERE user_id = %s', values=(session['id'],))
        form = RegistrationForm()
        if request.method == 'POST':
            pass
        return render_template('shop/profile.html', is_authenticated=is_auth, user=user, form=form)


@app.route('/personal/order')
def order():
    return render_template('shop/order.html')


@app.route('/cart')
def get_cart():
    ...


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')

        _hashed_password = generate_password_hash(password)

        user = db.select('SELECT * FROM account WHERE email= %s', values=(email,))
        phones = db.select('SELECT phone FROM account WHERE phone= %s', values=(phone,))
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
            db.insert('INSERT INTO account (first_name, last_name, phone, email, password)'
                      ' VALUES (%s, %s, %s, %s, %s)',
                      values=(first_name, last_name, phone, email, _hashed_password))
            user = db.select('SELECT * FROM account WHERE email= %s', values=(email,))
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

        user = db.select("SELECT * FROM account WHERE email= %s", values=(email,))
        if user:
            password_rs = user['password']
            if check_password_hash(password_rs, password):
                session['loggedin'] = True
                session['id'] = user['user_id']
                session['email'] = user['email']
                return redirect(url_for('main'))

        flash('Неправильный логин или пароль. Попробуйте еще раз.')
    return render_template('shop/authorization.html')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('email', None)
    return redirect(url_for('main'))


@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    categories = db.select('SELECT id, value FROM category')
    labels = db.select('SELECT id, value FROM shop_label')
    form = AddProduct(request.form)
    if request.method == 'POST':
        title = form.title.data
        author = form.author.data
        description = form.description.data
        publishing_office = form.publishing_office.data
        series = form.series.data
        quantity = form.quantity.data
        price = form.price.data
        image = photos.save(request.files.get('image'), name=secrets.token_hex(10) + '.')
        product_id = db.get_insert(
            'INSERT INTO product (title, author, description, publishing_office, series, quantity, price, image)'
            ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING product_id',
            values=(title, author, description, publishing_office, series, quantity, price, image))
        category_id = request.form.get('category')
        db.insert('INSERT INTO product_category (product_id, category_id) VALUES (%s, %s)',
                  values=(product_id, category_id,))
        label_id = request.form.get('label')
        if label_id != 'none':
            db.insert('INSERT INTO product_label (product_id, label_id) VALUES (%s, %s)',
                      values=(product_id, label_id,))
        flash('Товар успешно добавлен')
    return render_template('shop/product_form.html', form=form, categories=categories, labels=labels)


@app.route('/delivery')
def delivery():
    return render_template('shop/delivery.html')


@app.route('/about-us')
def about_us():
    return render_template('shop/about_us.html')


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


if __name__ == '__main__':
    app.run(debug=True)
