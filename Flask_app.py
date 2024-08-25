# Dołączanie modułu flask 

from flask import Flask
from flask import render_template, request, redirect, url_for, flash, session
from flask import Flask, session
from flask_session import Session
from werkzeug.utils import secure_filename
from tensorflow.python.keras.models import load_model
import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
import datetime
import sqlite3
import cv2
import os


# Tworzenie aplikacji
app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'

UPLOAD_FOLDER2 = os.getcwd() + r'\static\uploads'

PROJECT_PATH = os.getcwd()

MODEL_PATH = os.getcwd() + '\model'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Tworzenie obsługi sesji
sess = Session()

# Ścieżka do pliku bazy danych w sqlite
DATABASE = os.getcwd() + '\DB\database.db'

@app.route('/create_database', methods=['GET', 'POST'])
def create_db():
    # Połączenie sie z bazą danych
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    # Stworzenie tabeli w bazie danych za pomocą sqlite3
    cur.execute('CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT, password TEXT, admin INTEGER)')
    cur.execute('CREATE TABLE stats (stat_id INTEGER PRIMARY KEY, author TEXT, fileName TEXT, animal TEXT, prediction TEXT, date timestamp)')
    cur.execute("INSERT INTO users (username,password,admin) VALUES (?,?,?)",("admin","admin",1))
    conn.commit()
    # Zakończenie połączenia z bazą danych
    conn.close()
    return "Dodano użytkownika do bazy danych <br>"

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' in session:
        return render_template('index.html', username = session['user'].get('login'))
    else:
        return render_template('login.html')

@app.route('/show_image', methods=['POST'])
def show_image():
    if request.method == 'POST': 
        # if 'file' not in request.files:
        #     return render_template('test.html')
         
        uploaded_img = request.files['file']

        if uploaded_img:
            uploaded_img.save(UPLOAD_FOLDER2+"\\"+secure_filename(uploaded_img.filename))
            filename = uploaded_img.filename
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            session['UPLOADED_IMG_PATH'] = img_path
            print(img_path)
            return render_template('show_image.html', img = img_path, username = session['user'].get('login'))
        else:
            return render_template('index.html', username = session['user'].get('login'))
    else:
        return render_template('index.html', username = session['user'].get('login'))

@app.route('/login', methods=['POST'])
def login():
    # Pobranie danych z przesłanego formularza metodą POST i konwersja ich do słownika
    req_form = request.form.to_dict()
    login = request.form['login']
    password = request.form['password']

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (login, password))
    user = cur.fetchall()
    con.close()
    if len(user) == 0:
        return render_template("login.html", AccNotExist = True)
    else:
        session['user'] = req_form
        return index()

@app.route('/logout', methods=['GET'])
def logout():
    # Jeżeli sesja klienta istnieje - usunięcie sesji 
    if 'user' in session:
        session.pop('user')
        return render_template("logout.html")
    else:
        # Przekierowanie klienta do strony początkowej
        return redirect(url_for('login'))

@app.route('/users', methods=['GET','POST'])
def users():
    if isAdmin():
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        con.close()
        return render_template("users.html", users=users, username = session['user'].get('login'))
    else:
        return render_template("notAdmin.html", username = session['user'].get('login'))

def isAdmin():
    login = session['user'].get('login')
    password = session['user'].get('password')

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (login, password))
    user = cur.fetchall()
    con.close()

    return True if user[0][3] == 1 else False


@app.route('/addUser', methods=['POST'])
def addUser():
    login = request.form['login']
    password = request.form['password']
    isAdmin = request.form.get("admin")

    #dodanie uzytkowanika do bazy
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("INSERT INTO users (username,password,admin) VALUES (?,?,?)",(login,password, 0 if isAdmin is None else 1))
    con.commit()
    con.close()
    # return users()
    return redirect(url_for('users'))

@app.route('/stats', methods=['GET'])
def stats():
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("SELECT * FROM stats WHERE author=?", (session['user'].get('login'),))
    stats = cur.fetchall()
    con.close()

    return render_template('stats.html', stats = stats, username = session['user'].get('login'))

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    img_path = session.get('UPLOADED_IMG_PATH')
    img = cv2.imread("{}/{}".format(PROJECT_PATH, img_path))
    img = cv2.resize(img,(128,128))
    img = img / 255.0
    img = np.expand_dims(img, axis=0).astype('float32')
    img = tf.constant(img, dtype=tf.float32)
 
    model = tf.saved_model.load(MODEL_PATH)

    prediction = 'Dog' if model(img, training = True).numpy().argmax().all() == 1 else 'Cat'

    if request.method == 'POST':
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        if request.form.get('YesButton') == 'Yes':
            current_dateTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            filename = os.path.basename(img_path).split('/')[-1]
            
            cur.execute("INSERT INTO stats (author,filename,animal,prediction,date) VALUES (?,?,?,?,?)",
            (session['user'].get('login'),filename,'Dog' if prediction == 'Dog' else 'Cat','Correct', current_dateTime))
            con.commit()
        
            return render_template('index.html')

        elif request.form.get('NoButton') == 'No':
            current_dateTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            filename = os.path.basename(img_path).split('/')[-1]
            cur.execute("INSERT INTO stats (author,filename,animal,prediction,date) VALUES (?,?,?,?,?)",
            (session['user'].get('login'),filename,'Cat' if prediction == 'Cat' else 'Dog','Wrong',current_dateTime))
            con.commit()

            return render_template('index.html', username = session['user'].get('login'))
        
        con.close()

    return render_template('predict.html', predict = prediction, img = img_path, username = session['user'].get('login'))

# Uruchomienie aplikacji w trybie debug
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
sess.init_app(app)
app.config.from_object(__name__)
app.debug = True
app.run()