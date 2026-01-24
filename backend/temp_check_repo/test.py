import sqlite3
import pickle

def get_user_data(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # ❌ SECURITY: SQL Injection
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)

    data = cursor.fetchall()
    return data


def load_user_profile(blob):
    # ❌ SECURITY: Unsafe deserialization
    profile = pickle.loads(blob)
    return profile


def process_users(users):
    i = 0
    # ❌ LOGIC: Infinite loop (i never increments)
    while i < len(users):
        if users[i]["active"]:
            if users[i]["role"] == "admin":
                if users[i]["permissions"]:
                    print("Admin user")
        # missing i += 1


def deeply_nested(x):
    # ❌ QUALITY: Excessive nesting
    if x > 0:
        if x > 1:
            if x > 2:
                if x > 3:
                    if x > 4:
                        print("Too deep")
