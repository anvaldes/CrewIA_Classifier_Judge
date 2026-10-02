from flask import Flask, request
from io import StringIO

app = Flask(__name__)

print("✔ Flask app is loading...")

@app.route("/", methods=["GET"])
def pipeline():
    pais = request.args.get("pais", "MX")
    nombre_file = request.args.get("nombre_file", "1")

    return f"Pais: {pais}, Nombre archivo: {nombre_file}" , 200