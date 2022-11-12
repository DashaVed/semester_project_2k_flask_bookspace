import psycopg2


class Database:
    def __init__(self):
        self.con = psycopg2.connect(
            dbname="bookspace",
            user="postgres",
            password="prostotak4589",
            host="localhost",
            port=5432
        )
        self.cur = self.con.cursor()

    def select(self, query, values=()):
        self.cur.execute(query, values)
        data = self.prepare_data(self.cur.fetchall())
        if len(data) == 1:
            data = data[0]

        return data

    def insert(self, query, values):
        self.cur.execute(query, values)
        self.con.commit()

    def get_insert(self, query, values):
        self.cur.execute(query, values)
        data = self.cur.fetchone()[0]
        self.con.commit()
        return data

    def update(self, query, values):
        self.cur.execute(query, values)
        self.con.commit()

    def prepare_data(self, data):
        prepare_data = []
        if len(data):
            column_names = [desc[0] for desc in self.cur.description]
            for row in data:
                prepare_data += [{c_name: row[key] for key, c_name in enumerate(column_names)}]
        return prepare_data
