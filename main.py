import tkinter as tk
from flask import Flask, request, jsonify
import threading
import jwt, datetime, bcrypt, sqlite3, random
from cryptography.fernet import Fernet
from sklearn.ensemble import IsolationForest
import numpy as np
import requests

# ---------------- BACKEND ---------------- #

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'

key = Fernet.generate_key()
cipher = Fernet(key)

model = IsolationForest(contamination=0.1)
training_data = np.array([[1],[2],[3],[4],[5],[6],[7]])
model.fit(training_data)

conn = sqlite3.connect('pse.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS logs (user TEXT, activity TEXT, time TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS alerts (user TEXT, alert TEXT, time TEXT)")
conn.commit()

otp_store = {}

def log(user, activity):
    cursor.execute("INSERT INTO logs VALUES (?, ?, ?)",
                   (user, activity, str(datetime.datetime.now())))
    conn.commit()

def alert(user, msg):
    cursor.execute("INSERT INTO alerts VALUES (?, ?, ?)",
                   (user, msg, str(datetime.datetime.now())))
    conn.commit()

def detect_anomaly(val):
    return model.predict([[val]])[0] == -1

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt())
    cursor.execute("INSERT INTO users VALUES (?, ?)", (data['username'], hashed))
    conn.commit()
    return jsonify({"msg":"Registered"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    cursor.execute("SELECT password FROM users WHERE username=?", (data['username'],))
    res = cursor.fetchone()

    if res and bcrypt.checkpw(data['password'].encode(), res[0]):
        otp = random.randint(100000,999999)
        otp_store[data['username']] = otp
        print(f"[🔥 OTP for {data['username']}] => {otp}")
        return jsonify({"msg":"OTP sent"})
    return jsonify({"msg":"Invalid creds"})

@app.route('/verify-otp', methods=['POST'])
def verify():
    data = request.json
    user = data['username']
    otp = int(data['otp'])

    if otp_store.get(user) == otp:
        hour = datetime.datetime.now().hour
        if detect_anomaly(hour):
            alert(user, "🚨 Anomalous Login Detected")

        token = jwt.encode({
            "user": user,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        log(user, "Login Success")
        return jsonify({"token":token})

    return jsonify({"msg":"Invalid OTP"})

@app.route('/secure', methods=['GET'])
def secure():
    token = request.headers.get('Authorization')

    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user = data['user']

        encrypted = cipher.encrypt(b"Ultra Secure Data")
        decrypted = cipher.decrypt(encrypted)

        log(user, "Access Secure Resource")

        return jsonify({
            "encrypted": encrypted.decode(),
            "decrypted": decrypted.decode()
        })

    except:
        return jsonify({"msg":"Unauthorized"})

@app.route('/logs')
def get_logs():
    cursor.execute("SELECT * FROM logs")
    return jsonify(cursor.fetchall())

@app.route('/alerts')
def get_alerts():
    cursor.execute("SELECT * FROM alerts")
    return jsonify(cursor.fetchall())

def run_server():
    app.run(debug=False)

# ---------------- GUI (HACKER STYLE) ---------------- #

BASE_URL = "http://127.0.0.1:5000"
token = ""

def print_output(text, color="#00FF00"):
    output.insert(tk.END, text + "\n", color)
    output.tag_config(color, foreground=color)
    output.see(tk.END)

def register_gui():
    res = requests.post(f"{BASE_URL}/register", json={
        "username": user.get(),
        "password": pwd.get()
    })
    print_output(f"[+] REGISTER: {res.json()}")

def login_gui():
    res = requests.post(f"{BASE_URL}/login", json={
        "username": user.get(),
        "password": pwd.get()
    })
    print_output("[*] LOGIN INITIATED - CHECK TERMINAL FOR OTP")

def verify_gui():
    global token
    res = requests.post(f"{BASE_URL}/verify-otp", json={
        "username": user.get(),
        "otp": otp.get()
    })
    token = res.json().get("token","")
    print_output(f"[+] AUTH SUCCESS: {res.json()}")

def secure_gui():
    res = requests.get(f"{BASE_URL}/secure", headers={"Authorization": token})
    print_output(f"[DATA ACCESS]: {res.json()}")

def logs_gui():
    res = requests.get(f"{BASE_URL}/logs")
    print_output("[LOGS]", "#00FFFF")
    print_output(str(res.json()))

def alerts_gui():
    res = requests.get(f"{BASE_URL}/alerts")
    print_output("[⚠ ALERTS DETECTED]", "#FF0000")
    print_output(str(res.json()), "#FF0000")

threading.Thread(target=run_server, daemon=True).start()

# GUI WINDOW
root = tk.Tk()
root.title("PSE // Cyber Defense Console")
root.configure(bg="black")

# INPUTS
tk.Label(root, text="USERNAME", fg="#00FF00", bg="black").pack()
user = tk.Entry(root, bg="black", fg="#00FF00", insertbackground="#00FF00")
user.pack()

tk.Label(root, text="PASSWORD", fg="#00FF00", bg="black").pack()
pwd = tk.Entry(root, bg="black", fg="#00FF00", insertbackground="#00FF00")
pwd.pack()

tk.Label(root, text="OTP", fg="#00FF00", bg="black").pack()
otp = tk.Entry(root, bg="black", fg="#00FF00", insertbackground="#00FF00")
otp.pack()

# BUTTONS
buttons = [
    ("REGISTER", register_gui),
    ("LOGIN", login_gui),
    ("VERIFY OTP", verify_gui),
    ("ACCESS DATA", secure_gui),
    ("VIEW LOGS", logs_gui),
    ("VIEW ALERTS", alerts_gui)
]

for text, cmd in buttons:
    tk.Button(root, text=text, command=cmd,
              bg="black", fg="#00FF00",
              activebackground="#003300",
              activeforeground="#00FF00",
              highlightbackground="#00FF00").pack(pady=2)

# OUTPUT TERMINAL
output = tk.Text(root, height=20, width=70, bg="black", fg="#00FF00")
output.pack()

root.mainloop()