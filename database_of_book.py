import sqlite3
import pandas as pd

conn = sqlite3.connect('book_database.db')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS books(
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    genre TEXT
)
''')

c.execute('''CREATE TABLE IF NOT EXISTS user_books(
    all_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    book_id INTEGER,
    read_flag INTEGER,
    read_date TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(book_id) REFERENCES books(book_id)
)
''')

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print(tables)

df = pd.read_csv('higashino_keigo_base.csv')
sub_df = df[['title','genre','flag','finish_date']]
for n,row in sub_df.iterrows():
    title = row['title']
    genre = row['genre']
    c.execute("INSERT INTO books (title,genre) VALUES(?,?)", (title,genre))

c.execute("SELECT * FROM books LIMIT 5")
print(c.fetchall())

conn.commit()
conn.close()
