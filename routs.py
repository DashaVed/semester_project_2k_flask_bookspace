import re
from datetime import datetime, timedelta
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
app.permanent_session_lifetime = timedelta(days=365)


@app.route("/delete_visits")
def clear_cart():
    session.pop('cart')
    return "ok"


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

    return render_template('shop/catalog.html', categories=categories, products=products,
                           is_authenticated=is_authenticated())


@app.route('/change_quantity/<int:product_id>', methods=['POST'])
def change_quantity(product_id):
    quantity = int(request.form.get('quantity'))
    print(quantity)

    if not session.get('cart'):
        session['cart'] = []

    cart = session["cart"]
    item_exists = False

    for index, value in enumerate(cart):
        if value["product_id"] == product_id:
            if 'check' not in request.form:
                cart[index]["count"] += quantity
            else:
                cart[index]["count"] = quantity
            item_exists = True
            break

    if not item_exists:
        cart.append({'product_id': product_id, 'count': quantity})

    session["cart"] = cart

    return redirect(request.referrer)


@app.route('/delete-item/<int:product_id>', methods=['POST'])
def delete_item(product_id):
    cart = session["cart"]

    for value in cart:
        if value["product_id"] == product_id:
            cart.remove(value)
            break

    session["cart"] = cart
    return redirect(request.referrer)


@app.route('/product/<book_id>')
def get_book(book_id):
    book = db.select('SELECT * FROM product WHERE product_id = %s', (book_id,))
    return render_template('shop/book.html', book=book, is_authenticated=is_authenticated())


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
    return render_template('shop/order.html', is_authenticated=is_authenticated())


def order_line(order_id):
    cart = session['cart']
    for item in cart:
        db.update('UPDATE product SET quantity = quantity - %s WHERE product_id = %s',
                  values=(item['count'], item['product_id'],))
        price = db.select('SELECT price FROM product WHERE product_id = %s', values=(item['product_id'],))
        db.insert('INSERT INTO order_line(order_id, product_id, quantity, price) VALUES(%s, %s, %s, %s)',
                  values=(order_id, item['product_id'], item['count'], price['price']))


@app.route('/personal/order/make', methods=['GET', 'POST'])
def make_order():
    total_amount = 0
    total_count = 0
    if 'cart' in session:
        total_count = len(session['cart'])
        for item in session['cart']:
            product = db.select('SELECT product_id, price FROM product WHERE product_id = %s',
                                values=(item['product_id'],))
            total_amount += product['price'] * item['count']

    user_id = session['id']
    user = db.select('SELECT first_name, last_name, email, phone FROM account WHERE user_id = %s',
                     values=(user_id,))

    if request.method == 'POST':
        address = request.form.get('address')
        current_date = datetime.today().strftime('%Y-%m-%d')
        delivery_date = datetime.now() + timedelta(days=7)
        order_id = db.get_insert(
            'INSERT INTO shop_order(user_id, created_date, delivery_date, delivery_address, status, total_amount)'
            'VALUES (%s, %s, %s, %s, %s, %s)  RETURNING order_id',
            values=(user_id, current_date, delivery_date, address, 'Сформирован', total_amount))
        if order_id:
            flash('Заказ успешно сформирован и оплачен')
            order_line(order_id)
            clear_cart()
    return render_template('shop/order_form.html', total_amount=total_amount, total_count=total_count, user=user,
                           is_authenticated=is_authenticated())


@app.route('/cart', methods=['GET', 'POST'])
def get_cart():
    products = []
    total_amount = 0
    total_count = 0
    if 'cart' in session:
        total_count = len(session['cart'])
        for item in session['cart']:
            product = db.select(
                'SELECT product_id, title, author, price, quantity, image FROM product WHERE product_id = %s',
                values=(item['product_id'],))
            total_amount += product['price'] * item['count']
            product['count'] = item['count']
            products.append(product)
    return render_template('shop/cart.html', products=products, total_count=total_count, total_amount=total_amount,
                           is_authenticated=is_authenticated())


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
    return render_template('shop/delivery.html', is_authenticated=is_authenticated())


@app.route('/about-us')
def about_us():
    return render_template('shop/about_us.html', is_authenticated=is_authenticated())


@app.route('/sales')
def get_sales():
    return render_template('shop/sales.html', is_authenticated=is_authenticated())


@app.route('/new')
def get_new():
    return render_template('shop/new.html', is_authenticated=is_authenticated())


@app.route('/bestsellery')
def get_bestsellery():
    return render_template('shop/bestsellery.html', is_authenticated=is_authenticated())


@app.route('/best-price')
def get_best_price():
    return render_template('shop/best_price.html', is_authenticated=is_authenticated())


if __name__ == '__main__':
    app.run(debug=True)
