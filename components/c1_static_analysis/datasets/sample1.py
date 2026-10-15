# samples/sample1.py

def validate_user():
    return True

def connect_db():
    print("Connecting to database")

def login(username, password):
    if validate_user():
        connect_db()
        if username == "admin" and password == "1234":
            return True
    return False

def print_numbers():
    for i in range(5):
        print(i)

while False:
    print("test")