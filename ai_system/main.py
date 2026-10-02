from flask import Flask, jsonify, request

from classifier_judge import classify

app = Flask(__name__)

print("✔ Flask app is loading...")

@app.route("/", methods=["POST"])
def pipeline():
    payload = request.get_json(silent=True)
    review = payload.get("review") if isinstance(payload, dict) else None

    if not isinstance(review, str) or not review.strip():
        return jsonify({"error": 'Expected a JSON body like {"review": "The film was bad"}'}), 400

    return jsonify(classify(review)), 200
