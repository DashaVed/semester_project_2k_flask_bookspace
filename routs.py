from flask import Flask, render_template


from db_util import Database

app = Flask(__name__)

db = Database()


@app.route("/")
def main():
    return render_template('main.html')


@app.route('/catalog', defaults={'parent_id': None})
@app.route('/catalog/<parent_id>')
def get_catalog(parent_id):
    if parent_id:
        categories = db.select(f'SELECT * FROM category WHERE category_parent_id={parent_id}')
    else:
        categories = db.select('SELECT * FROM category WHERE category_parent_id is NULL')

    return render_template('catalog.html', categories=categories)


@app.route('/product/<book_id>')
def get_book(book_id):
    return render_template('sales.html')


@app.route('/sales')
def get_sales():
    return render_template('sales.html')


@app.route('/new')
def get_new():
    return render_template('new.html')


@app.route('/bestsellery')
def get_bestsellery():
    return render_template('bestsellery.html')


@app.route('/best-price')
def get_best_price():
    return render_template('best_price.html')


@app.route('/personal/profile')
def profile():
    return render_template('profile.html')


@app.route('/delivery')
def delivery():
    return render_template('delivery.html')


@app.route('/about-us')
def about_us():
    return render_template('about_us.html')
