from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import os
from collections import Counter

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Secret key for session management

# ✅ Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "users.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
RESULT_FOLDER = os.path.join(BASE_DIR, "results")  # Folder for storing results

# ✅ Ensure necessary folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

# ✅ Initialize Database
def init_db():
    print("[INFO] Initializing Database...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT UNIQUE, 
                password TEXT, 
                firstname TEXT, 
                lastname TEXT, 
                email TEXT UNIQUE, 
                address TEXT)''')
    conn.commit()
    conn.close()
    print("[INFO] Database Initialized Successfully!")

init_db()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        address = request.form['address']

        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password, firstname, lastname, email, address) VALUES (?, ?, ?, ?, ?, ?)",
                          (username, password, firstname, lastname, email, address))
                conn.commit()

            session['user'] = username
            return redirect(url_for('profile', username=username))

        except sqlite3.IntegrityError:
            return "Username or Email already exists. Try again."

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = c.fetchone()

        if user:
            session['user'] = username
            return redirect(url_for('profile', username=username))
        else:
            error = "Invalid username or password. Try again."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/profile/<username>')
def profile(username):
    if 'user' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()

    if not user:
        return "User profile not found."

    return render_template('profile.html', user=user)

### 🔹 File Upload Handler
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    if file and file.filename.endswith('.txt'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        letter_counts = Counter(content)

        # 🔹 Convert Counter to dictionary before storing in session
        session['letter_counts'] = dict(letter_counts)
        session['result_filename'] = f"letter_count_{file.filename}"  # Store filename for download

        # 🔹 Save the results to a file
        result_file_path = os.path.join(app.config['RESULT_FOLDER'], session['result_filename'])
        with open(result_file_path, 'w', encoding='utf-8') as f:
            for letter, count in letter_counts.most_common():
                f.write(f'"{letter}": {count}\n')

        return redirect(url_for('count_me'))

    return "Invalid file type. Please upload a .txt file.", 400

### 🔹 Display & Download Letter Counts
@app.route('/countme')
def count_me():
    letter_counts_dict = session.get('letter_counts', {})
    result_filename = session.get('result_filename', '')

    if not letter_counts_dict:
        return "No file uploaded yet.", 400

    letter_counts = Counter(letter_counts_dict)
    response = ['"{}": {}'.format(letter, count) for letter, count in letter_counts.most_common()]

    return render_template('count.html', response=response, result_filename=result_filename)

### 🔹 Download Letter Count File
@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['RESULT_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found.", 404

if __name__ == '__main__':
    app.run(debug=True)
