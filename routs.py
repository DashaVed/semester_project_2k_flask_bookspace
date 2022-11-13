import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_uploads import IMAGES, UploadSet, configure_uploads, patch_request_class
from flask_session import Session
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
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './my_sessions'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
app.permanent_session_lifetime = timedelta(days=365)

sess = Session()
sess.init_app(app)


@app.route("/delete_session")
def clear_cart():
    if 'cart' in session:
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

    if is_authenticated():
        db_cart = db.select('SELECT cart_id FROM cart WHERE user_id = %s', values=(session['id'],))[0]
        if 'check' not in request.form:
            db.update('UPDATE cart_item SET qty = qty + %s WHERE cart_id = %s AND product_id = %s',
                      values=(quantity, db_cart['cart_id'], product_id))
        else:
            db.update('UPDATE cart_item SET qty = %s WHERE cart_id = %s AND product_id = %s',
                      values=(quantity, db_cart['cart_id'], product_id))

    else:
        cart = session["cart"]
        for index, value in enumerate(cart):
            if value["product_id"] == product_id:
                if 'check' not in request.form:
                    cart[index]["qty"] += quantity
                else:
                    cart[index]["qty"] = quantity
                break
        session["cart"] = cart

    return redirect(request.referrer)


@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity'))

    if is_authenticated():
        db_cart = db.select('SELECT cart_id FROM cart WHERE user_id = %s', values=(session['id'],))[0]
        cart = db.select('SELECT product_id, qty FROM cart_item WHERE cart_id = %s AND product_id= %s',
                         (db_cart['cart_id'], product_id))
        if cart:
            db.update('UPDATE cart_item SET qty = qty + 1 WHERE product_id = %s', values=(product_id,))
        else:
            db.insert('INSERT INTO cart_item (cart_id, product_id, qty) VALUES (%s, %s, %s)',
                      values=(db_cart['cart_id'], product_id, quantity))
    else:
        if 'cart' not in session:
            session['cart'] = []

        cart = session["cart"]
        item_exists = False

        for index, value in enumerate(cart):
            if value["product_id"] == product_id:
                cart[index]["qty"] = quantity
                item_exists = True
                break

        if not item_exists:
            cart.append({'product_id': product_id, 'qty': quantity})
        session["cart"] = cart

    return redirect(request.referrer)


@app.route('/delete-item/<int:cart_id>/<int:product_id>', methods=['POST'])
def delete_item(product_id, cart_id=None):
    if is_authenticated():
        db.delete('DELETE FROM cart_item WHERE cart_id = %s AND product_id= %s', values=(cart_id, product_id,))
    else:
        cart = session["cart"]
        for value in cart:
            if value["product_id"] == product_id:
                cart.remove(value)
                break
        session["cart"] = cart

    return redirect(request.referrer)


@app.route('/product/<book_id>')
def get_book(book_id):
    book = db.select('SELECT * FROM product WHERE product_id = %s', (book_id,))[0]
    return render_template('shop/book.html', book=book, is_authenticated=is_authenticated())


@app.route('/personal/profile', methods=['GET', 'POST'])
def profile():
    is_auth = is_authenticated()
    if is_auth:
        user = db.select('SELECT * FROM account WHERE user_id = %s', values=(session['id'],))[0]
        form = RegistrationForm()
        if request.method == 'POST':
            pass
        return render_template('shop/personal/profile.html', is_authenticated=is_auth, user=user, form=form)


@app.route('/personal/order')
def order():
    is_auth = is_authenticated()
    if is_auth:
        user = db.select('SELECT * FROM account WHERE user_id = %s', values=(session['id'],))[0]
        orders = db.select('SELECT * FROM shop_order WHERE user_id = %s', values=(session['id'],))
        return render_template('shop/personal/order.html', is_authenticated=is_auth, user=user, orders=orders)


def order_line(order_id):
    db_cart = db.select('SELECT cart_id FROM cart WHERE user_id = %s', values=(session['id'],))[0]
    cart = db.select('SELECT product_id, qty FROM cart_item WHERE cart_id = %s', (db_cart['cart_id'],))
    for item in cart:
        db.update('UPDATE product SET quantity = quantity - %s WHERE product_id = %s',
                  values=(item['qty'], item['product_id'],))
        price = db.select('SELECT price FROM product WHERE product_id = %s', values=(item['product_id'],))[0]
        db.insert('INSERT INTO order_line(order_id, product_id, quantity, price) VALUES(%s, %s, %s, %s)',
                  values=(order_id, item['product_id'], item['qty'], price['price']))


@app.route('/personal/order/make', methods=['GET', 'POST'])
def make_order():
    is_auth = is_authenticated()
    total_amount = 0
    db_cart = db.select('SELECT cart_id FROM cart WHERE user_id = %s', values=(session['id'],))[0]
    cart_item = db.select('SELECT product_id, qty FROM cart_item WHERE cart_id = %s', (db_cart['cart_id'],))
    total_count = len(cart_item)
    for item in cart_item:
        product = db.select('SELECT product_id, price FROM product WHERE product_id = %s',
                            values=(item['product_id'],))[0]
        total_amount += product['price'] * item['qty']

    user_id = session['id']
    user = db.select('SELECT first_name, last_name, email, phone FROM account WHERE user_id = %s',
                     values=(user_id,))[0]

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
            if is_auth:
                db.delete('DELETE FROM cart_item WHERE cart_id = %s', values=(db_cart, ))
            else:
                clear_cart()
    return render_template('shop/personal/order_form.html', total_amount=total_amount, total_count=total_count,
                           user=user, is_authenticated=is_auth)


@app.route('/personal/wishlist', methods=['GET', 'POST'])
def wishlist():
    is_auth = is_authenticated()
    if is_auth:
        user = db.select('SELECT * FROM account WHERE user_id = %s', values=(session['id'],))[0]
        products = []
        user_wishlist = db.select('SELECT wishlist_id FROM wishlist WHERE user_id = %s', values=(session['id'],))[0]
        products_id = db.select('SELECT product_id FROM wishlist_item WHERE wishlist_id = %s',
                                values=(user_wishlist['wishlist_id'],))
        for item in products_id:
            print(item)
            products += \
                db.select('SELECT product_id, title, author, series, price, image FROM product WHERE product_id = %s',
                          values=(item['product_id'],))
        return render_template('shop/personal/wishlist.html', user=user, products=products,
                               wishlist_id=user_wishlist['wishlist_id'])


@app.route('/add-to-wishlist/<int:product_id>', methods=['POST'])
def add_to_wishlist(product_id):
    user_wishlist = db.select('SELECT wishlist_id FROM wishlist WHERE user_id = %s', values=(session['id'],))[0]
    products_id = db.select('SELECT product_id FROM wishlist_item WHERE wishlist_id = %s',
                            values=(user_wishlist['wishlist_id'],))

    item_exist = False
    if products_id:
        for item in products_id:
            if item['product_id'] == product_id:
                item_exist = True
                break

    if not item_exist:
        db.insert('INSERT INTO wishlist_item(wishlist_id, product_id) VALUES (%s, %s)',
                  values=(user_wishlist['wishlist_id'], product_id,))
        return redirect(request.referrer)


@app.route('/delete-wishlist/<int:wishlist_id>/<int:product_id>', methods=['POST'])
def delete_wishlist(wishlist_id, product_id):
    db.delete('DELETE FROM wishlist_item WHERE wishlist_id=%s AND product_id=%s', values=(wishlist_id, product_id, ))
    return redirect(request.referrer)


def get_product(products, cart):
    amount = 0
    for item in cart:
        product = db.select(
            'SELECT product_id, title, author, price, quantity, image FROM product WHERE product_id = %s',
            values=(item['product_id'],))[0]
        repeated_product = list(filter(lambda x: x['product_id'] == product['product_id'], products))
        if repeated_product:
            product['qty'] += item['qty']
        else:
            product['qty'] = item['qty']
            products.append(product)
        amount += product['price'] * product['qty']
    return amount


@app.route('/cart', methods=['GET', 'POST'])
def get_cart():
    products = []
    total_amount = 0
    total_count = 0
    is_auth = is_authenticated()
    if is_auth:
        db_cart = db.select('SELECT cart_id FROM cart WHERE user_id = %s', values=(session['id'],))[0]
        cart_item = db.select('SELECT product_id, qty FROM cart_item WHERE cart_id = %s', (db_cart['cart_id'],))
        if cart_item:
            total_count += len(cart_item)
            total_amount += get_product(products, cart_item)
    if 'cart' in session:
        total_count += len(session['cart'])
        total_amount += get_product(products, session['cart'])
        if is_auth:
            for item in session['cart']:
                db.insert('INSERT INTO cart_item (cart_id, product_id, qty) VALUES (%s, %s, %s)',
                          values=(db_cart['cart_id'], item['product_id'], item['qty']))
            clear_cart()
    return render_template('shop/personal/cart.html', products=products, total_count=total_count,
                           cart_id=db_cart['cart_id'] or None, total_amount=total_amount, is_authenticated=is_auth)


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')

        _hashed_password = generate_password_hash(password)

        user = db.select('SELECT * FROM account WHERE email= %s', values=(email,))[0]
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
            db.insert('INSERT INTO cart(user_id) VALUES (%s)', values=(user['user_id'],))
            db.insert('INSERT INTO wishlist(user_id) VALUES (%s)', values=(user['user_id'],))
            user = db.select('SELECT * FROM account WHERE email= %s', values=(email,))[0]
            session['loggedin'] = True
            session['id'] = user['user_id']
            session['email'] = user['email']
            return redirect(url_for('main'))

    return render_template('shop/auth/registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = db.select("SELECT * FROM account WHERE email= %s", values=(email,))[0]
        if user:
            password_rs = user['password']
            if check_password_hash(password_rs, password):
                session['loggedin'] = True
                session['id'] = user['user_id']
                session['email'] = user['email']
                return redirect(url_for('main'))

        flash('Неправильный логин или пароль. Попробуйте еще раз.')
    return render_template('shop/auth/authorization.html')


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
    return render_template('shop/admin/product_form.html', form=form, categories=categories, labels=labels)


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
