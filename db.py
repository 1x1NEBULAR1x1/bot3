import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

async def create_tables():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    name TEXT)
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_text TEXT,
    photo_id TEXT,
    type TEXT DEFAULT 'photo',
    pin INTEGER DEFAULT 0)
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sends (
    chat_id INTEGER,
    message_id INTEGER,
    interval INTEGER DEFAULT 0, 
    active BOOLEAN DEFAULT False, 
    run_time TEXT DEFAULT '',
    end_time TEXT DEFAULT '')
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sends_buttons (
    button_id INTEGER PRIMARY KEY AUTOINCREMENT,
    send_id INTEGER,
    button_text TEXT,
    button_url TEXT)
    ''')
    conn.commit()
async def set_start_time(chat_id, message_id, start_time):
    cursor.execute('UPDATE sends SET run_time = ? WHERE chat_id = ? AND message_id = ?', (start_time, chat_id, message_id))
    conn.commit()
async def set_end_time(chat_id, message_id, end_time):
    cursor.execute('UPDATE sends SET end_time = ? WHERE chat_id = ? AND message_id = ?', (end_time, chat_id, message_id))
    conn.commit()


async def edit_pin(send_id, value):
    cursor.execute('UPDATE messages SET pin = ? WHERE message_id = ?', (value, send_id))
    conn.commit()
async def update_message_text(message_id: int, message_text: str):
    cursor.execute('UPDATE messages SET message_text = ? WHERE message_id = ?',
                   (message_text, message_id))
    conn.commit()
async def update_message_photo(message_id: int, photo_id: str, type: str = 'photo'):
    cursor.execute('UPDATE messages SET photo_id = ?, type = ? WHERE message_id = ?',
                   (photo_id, message_id, type))
    conn.commit()

async def add_button(send_id: int, button_text: str, button_url: str):
    cursor.execute('INSERT INTO sends_buttons(send_id, button_text, button_url) VALUES (?, ?, ?)',
                   (send_id, button_text, button_url))
    conn.commit()
async def get_buttons(send_id: int):
    cursor.execute('SELECT * FROM sends_buttons WHERE send_id = ?', (send_id,))
    return cursor.fetchall()
async def delete_button(button_id: int):
    cursor.execute('DELETE FROM sends_buttons WHERE button_id = ?', (button_id,))
    conn.commit()
async def get_button(button_id: int):
    cursor.execute('SELECT * FROM sends_buttons WHERE button_id = ?', (button_id,))
    return cursor.fetchone()
async def update_button_text(button_id: int, button_text: str):
    cursor.execute('UPDATE sends_buttons SET button_text = ? WHERE button_id = ?', (button_text, button_id))
    conn.commit()
async def update_button_url(button_id: int, button_url: str):
    cursor.execute('UPDATE sends_buttons SET button_url = ? WHERE button_id = ?', (button_url, button_id))
    conn.commit()
async def add_chat(chat_id: int, name: str):
    cursor.execute('SELECT * FROM chats WHERE chat_id = ?', (chat_id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO chats(chat_id, name) VALUES (?, ?)',
                       (chat_id, name,))
        conn.commit()
async def get_chats():
    cursor.execute('SELECT * FROM chats')
    return cursor.fetchall()
async def add_message(message_text: str | None, photo_id: str | None,
                      type: str | None = 'photo'):
    cursor.execute('INSERT INTO messages(message_text, photo_id, type, pin) VALUES (?, ?, ?, ?)',
                   (message_text, photo_id, type, 0, ))
    conn.commit()
async def get_messages():
    cursor.execute('SELECT * FROM messages')
    return cursor.fetchall()
async def get_message(message_id: int):
    cursor.execute('SELECT * FROM messages WHERE message_id = ?', (message_id,))
    return cursor.fetchone()
async def get_chat(chat_id: int):
    cursor.execute('SELECT * FROM chats WHERE chat_id = ?', (chat_id, ))
    return cursor.fetchone()
async def add_send(chat_id: int, message_id: int, interval: int):
    cursor.execute('SELECT * FROM sends WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
    if cursor.fetchone():
        return
    cursor.execute('INSERT INTO sends(chat_id, message_id, interval, active) VALUES (?, ?, ?, ?)',
                   (chat_id, message_id, interval, False))
    conn.commit()
async def deactivate():
    cursor.execute('UPDATE sends SET active = 0')
    conn.commit()
async def get_sends():
    cursor.execute('SELECT * FROM sends')
    return cursor.fetchall()
async def get_message_id(message_text, message_photo_id):
    cursor.execute('SELECT message_id FROM messages WHERE message_text = ? OR photo_id = ?', (message_text, message_photo_id))
    return cursor.fetchone()[0]
async def delete_chat(chat_id: int):
    cursor.execute('DELETE FROM chats WHERE chat_id = ?', (chat_id,))
    conn.commit()
async def delete_message(message_id: int):
    cursor.execute('DELETE FROM messages WHERE message_id = ?', (message_id,))
    conn.commit()
async def get_sends_active():
    cursor.execute('SELECT * FROM sends WHERE active = 1')
    return cursor.fetchall()
async def delete_send(chat_id: int, message_id: int):
    cursor.execute('DELETE FROM sends WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
    conn.commit()
async def set_send_active(chat_id: int, message_id: int, interval: int):
    cursor.execute('UPDATE sends SET active = 1 WHERE chat_id = ? AND message_id = ?',
                   (chat_id, message_id, ))
    cursor.execute('UPDATE sends SET interval = ? WHERE chat_id = ? AND message_id = ?',
                   (interval, chat_id, message_id, ))
    conn.commit()
async def set_send_unactive(chat_id: int, message_id: int):
    cursor.execute('UPDATE sends SET active = 0 WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
    conn.commit()
async def get_send(chat_id: int, message_id: int):
    cursor.execute('SELECT * FROM sends WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
    return cursor.fetchone()
async def find_send(message_text, message_photo_id):
    cursor.execute('SELECT * FROM messages WHERE message_text = ? OR photo_id = ?', (message_text, message_photo_id))
    return cursor.fetchone()