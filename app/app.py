import os
from flask import Flask, request, jsonify
from flask_restx import Api, Resource
import psycopg2

app = Flask(__name__)
api = Api(app, version='1.0', title='cloud lab1 API UPDATED BY ALINA', description='CI/CD pipeline test successful!')
ns = api.namespace('api', description='main operations')

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:mysecretpassword@db:5432/appdb')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, text TEXT);")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"no connection to Data Base: {e}")

init_db()

@ns.route('/data')
class DataResource(Resource):
    @ns.doc('get_data')
    def get(self):
        """Get all data from db"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, text FROM messages;")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [{"id": r[0], "text": r[1]} for r in rows], 200
        except Exception as e:
            return {"error": str(e)}, 500

    @ns.doc('post_data')
    def post(self):
        """Add new line (protected by token for task6)"""
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != "Bearer secret-token-123":
            return {"error": "Unauthorized"}, 401

        data = request.json
        text = data.get('text', '')
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO messages (text) VALUES (%s) RETURNING id;", (text,))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"id": new_id, "text": text}, 201

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)