from flask import Flask, render_template, request, redirect
import mysql.connector
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = 'mon_secret'  # Nécessaire pour gérer les sessions

# 🛠️ MySQL config
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',       # 🔁 replace with your MySQL username
    'password': '',   # 🔁 replace with your MySQL password
    'database': 'todo_db'
}

def get_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect('/')
        else:
            error = "Identifiants invalides"

    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_pw))
            conn.commit()
            conn.close()
            return redirect('/login')
        except mysql.connector.errors.IntegrityError:
            conn.close()
            error = "Nom d'utilisateur déjà pris"
    
    return render_template('register.html', error=error)



@app.route('/', methods=['GET'])
def index():
    if 'user_id' not in session:
        return redirect('/login')

    category_filter = request.args.get('category')
    priority_filter = request.args.get('priority')
    status_filter = request.args.get('status')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Charger catégories et priorités pour le formulaire
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    cursor.execute("SELECT * FROM priorities")
    priorities = cursor.fetchall()

    # Construction dynamique de la requête
    query = """
        SELECT todos.*, categories.name AS category_name, priorities.level AS priority_level
        FROM todos  
        LEFT JOIN categories ON todos.category_id = categories.id
        LEFT JOIN priorities ON todos.priority_id = priorities.id
        WHERE todos.user_id = %s
    """
    params = [session['user_id']]

    if category_filter and category_filter != "all":
        query += " AND todos.category_id = %s"
        params.append(category_filter)

    if priority_filter and priority_filter != "all":
        query += " AND todos.priority_id = %s"
        params.append(priority_filter)

    if status_filter and status_filter != "all":
        query += " AND todos.status = %s"
        params.append(status_filter)

    query += " ORDER BY todos.id DESC"  # ou `created_at` si tu ajoutes cette colonne

    cursor.execute(query, params)
    todos = cursor.fetchall()

    conn.close()
    return render_template('index.html', todos=todos, categories=categories, priorities=priorities)




@app.route('/add', methods=['POST'])
def add():
    task = request.form['task']
    status = request.form['status']
    category_id = request.form['category']
    priority_id = request.form['priority']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO todos (task, status, user_id, category_id, priority_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (task, status, session['user_id'], category_id, priority_id))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    status = request.form['status']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE todos SET status = %s WHERE id = %s", (status, id))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/add_category', methods=['POST'])
def add_category():
    data = request.get_json()
    name = data.get('name')
    if name:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
        conn.commit()
        conn.close()
        return '', 200
    return '', 400


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True) 
