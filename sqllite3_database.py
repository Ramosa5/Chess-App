import sqlite3

class FenDatabase:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS fen_strings
                          (id INTEGER PRIMARY KEY, fen_string TEXT)''')
        self.conn.commit()

    def get_last_fen_string(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT fen_string FROM fen_strings ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        if result:
            return result[0]
        return None

    def clear_database(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM fen_strings')  # This will delete all rows in the table
        self.conn.commit()
    def delete_fen_string(self, fen_string):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM fen_strings WHERE fen_string = ?', (fen_string,))
        self.conn.commit()
    def insert_fen_string(self, fen_string):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO fen_strings (fen_string) VALUES (?)', (fen_string,))
        self.conn.commit()

    def close(self):
        self.conn.close()