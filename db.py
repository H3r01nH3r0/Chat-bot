from pymongo import MongoClient, errors
from pymongo.cursor import Cursor
from typing import Optional, Union, Dict
import sqlite3
import random



class DataBase:
    def __init__(self, db_url: str, db_name: str, db_file: str) -> None:
        try:
            self.client = MongoClient(
                db_url, connect=False,
                serverSelectionTimeoutMS=2000
            )

        except errors.ConnectionFailure:
            exit("Can`t connect to server!")

        self.db = self.client[db_name]
        self._users = self.db.users
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.connection.cursor()


    def add_user(self, user_id: int) -> str:
        return self._users.insert_one({"user_id": user_id, "lang": None}).inserted_id

    def get_user(self, user_id: Optional[int]=None) -> Union[Cursor, Dict]:
        if user_id:
            return self._users.find_one({"user_id": user_id})

        return self._users.find({})

    def get_users_count(self) -> int:
        return self._users.count_documents({})

    def edit_user(self, user_id: int, data: dict) -> int:
        return self._users.update_one({"user_id": user_id}, {"$set": data}).modified_count

    def delete_user(self, user_id: Optional[int]=None) -> int:
        if user_id:
            result = self._users.delete_many({})
        else:
            result = self._users.delete_one({"user_id": user_id})

        return result.deleted_count

    def check_queue(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM queue WHERE user_id = ?", (user_id,)).fetchall()
            return bool(len(result))

    def add_queue(self, user_id):
        with self.connection:
            return self.cursor.execute("INSERT INTO queue (user_id) VALUES (?)", (user_id,))


    def del_queue(self, user_id):
        with self.connection:
            return self.cursor.execute("DELETE FROM queue WHERE user_id = ?", (user_id,))

    def get_chat(self):
        with self.connection:
            chat = self.cursor.execute("SELECT * FROM queue").fetchall()
            if bool(len(chat)):
                random_index = random.randint(0, len(chat) - 1)
                return chat[random_index][1]
            else:
                return False

    def check_chat(self, user_id):
        with self.connection:
            result1 = self.cursor.execute("SELECT * FROM chats WHERE user_one = ?", (user_id,)).fetchall()
            result2 = self.cursor.execute("SELECT * FROM chats WHERE user_two = ?", (user_id,)).fetchall()
            if len(result1) == 0 and len(result2) == 0:
                return True
            else:
                return False


    def create_chat(self, chat_one, chat_two):
        with self.connection:
            if chat_two != 0:
                self.cursor.execute("DELETE FROM queue WHERE user_id = ?", (chat_two,))
                self.cursor.execute("INSERT INTO chats (user_one, user_two) VALUES (?, ?)", (chat_one, chat_two,))
                return True
            else:
                return False

    def get_activ_chat(self, user_id):
        with self.connection:
            chat1 = self.cursor.execute("SELECT * FROM chats WHERE user_one = ?", (user_id,)).fetchall()
            chat2 = self.cursor.execute("SELECT * FROM chats WHERE user_two = ?", (user_id,)).fetchall()
            if len(chat1) == 0 and len(chat2) == 0:
                return False
            else:
                if len(chat1) > len(chat2):
                    chat_info = chat1[0][0], chat1[0][2]
                    return chat_info
                elif len(chat1) < len(chat2):
                    chat_info = chat2[0][0], chat2[0][1]
                    return chat_info

    def del_chat(self, chat_id):
        with self.connection:
            return self.cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))

    def check_valent(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM valentin WHERE user_id = ?", (user_id,)).fetchall()
            return bool(len(result))

    def add_valentin(self, user_id, valentin_id):
        with self.connection:
            return self.cursor.execute("INSERT INTO valentin (user_id, valent_id) VALUES (?, ?)", (user_id, valentin_id,))

    def change_valent(self, user_id, valent_id):
        with self.connection:
            return self.cursor.execute("UPDATE valentin SET valent_id = ? WHERE user_id = ?", (valent_id, user_id))

    def get_valent(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT valent_id FROM valentin WHERE user_id = ?", (user_id,)).fetchall()
            return result[0][0]

    def waitin_message(self, user_id, text, valent_id):
        with self.connection:
            return self.cursor.execute("INSERT INTO messages (user_id, message, valent_id) VALUES (?, ?, ?)", (user_id, text, valent_id,))

    def check_message(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM messages WHERE valent_id = ?", (user_id,)).fetchall()
            return bool(len(result))

    def get_message(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM messages WHERE valent_id = ?", (user_id,)).fetchall()
            return result

    def del_message(self, user_id):
        with self.connection:
            return self.cursor.execute("DELETE FROM messages WHERE valent_id = ?", (user_id,))

    def check_countv(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM countv WHERE user_id = ?", (user_id,)).fetchall()
            return bool(len(result))

    def add_countv(self, user_id):
        with self.connection:
            return self.cursor.execute("INSERT INTO countv (user_id) VALUES (?)", (user_id,))

    def get_countv(self):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM countv").fetchall()
            return len(result)

    def check_countvn(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM countvn WHERE user_id = ?", (user_id,)).fetchall()
            return bool(len(result))

    def add_countvn(self, user_id):
        with self.connection:
            return self.cursor.execute("INSERT INTO countvn (user_id) VALUES (?)", (user_id,))

    def get_countvn(self):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM countvn").fetchall()
            return len(result)

    def close(self) -> None:
        self.client.close()
