import os
import sqlite3
import random
import string
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='.')

# Read securely from your Render Environment Variables
API_SECRET_KEY = os.environ.get("VTU_API_KEY", "YOUR_LIVE_GATEWAY_API_TOKEN")

# Pairgate's true data purchase production endpoint
GATEWAY_URL = "https://pairgate.com/api/v1/data/purchase"

DB_FILE = "transactions.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            phone TEXT NOT NULL,
            network TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            status TEXT NOT NULL,
            reference TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def generate_reference():
    """Generates the mandatory unique transaction reference required by Pairgate."""
    chars = string.ascii_letters + string.digits
    return "REF-" + "".join(random.choice(chars) for _ in range(12))

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/v1/get-live-plans', methods=['GET'])
def get_live_plans():
    # These plan lists map to Pairgate's internal structure.
    # Note: Replace these plan IDs with the exact numeric/string IDs found in your Pairgate API documentation tab!
    market_data = {
        "status": "success",
        "networks": {
            "AIRTEL": [
                {"id": "airtel_cg_1gb", "name": "Airtel 1GB Corporate Gifting (30 Days)"},
                {"id": "airtel_cg_2gb", "name": "Airtel 2GB Corporate Gifting (30 Days)"}
            ],
            "MTN": [
                {"id": "mtn_sme_1gb", "name": "MTN 1GB SME Plan (30 Days)"},
                {"id": "mtn_sme_2gb", "name": "MTN 2GB SME Plan (30 Days)"}
            ]
        }
    }
    return jsonify(market_data)

@app.route('/v1/dispense-data', methods=['POST'])
def dispense_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        user_input = request.get_json()
        network = user_input.get('network')    # e.g., "AIRTEL"
        plan_id = user_input.get('plan_id')    # e.g., "airtel_cg_1gb"
        phone_number = user_input.get('phone') # e.g., "07018456784"

        if not phone_number or len(phone_number) != 11:
            return jsonify({"status": "failed", "message": "Invalid phone number length."}), 400

        # Generate the mandatory unique transaction ID for Pairgate
        tx_reference = generate_reference()

        # EXACT PAYLOAD ALIGNED WITH PAIRGATE DEVELOPER RULES
        payload = {
            "provider_id": network,         # Pairgate uses provider_id, not network
            "plan_id": str(plan_id),        # The exact Plan ID from your Pairgate panel
            "recipient": str(phone_number), # Pairgate uses recipient, not phone
            "reference": tx_reference       # Mandatory reference parameter
        }

        headers = {
            "Authorization": f"Bearer {API_SECRET_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Send request directly to Pairgate's live endpoint
        response = requests.post(GATEWAY_URL, json=payload, headers=headers, timeout=20)
        
        # Safely handle potential error string pages before decoding JSON
        if response.status_code == 404:
            return jsonify({"status": "failed", "message": "Pairgate API endpoint path error (404). Check API documentation url."}), 404
        if response.status_code == 401:
            return jsonify({"status": "failed", "message": "Unauthorized (401). Your VTU_API_KEY environment variable is invalid or missing."}), 401

        api_response_data = response.json()

        if response.status_code in [200, 201] and api_response_data.get("status") in ["success", True]:
            cursor.execute("INSERT INTO transactions (phone, network, plan_id, status, reference) VALUES (?, ?, ?, ?, ?)",
                           (phone_number, network, plan_id, "SUCCESS", tx_reference))
            conn.commit()
            return jsonify({
                "status": "success",
                "transaction_id": api_response_data.get("reference", tx_reference),
                "message": "Data bundle pushed successfully!"
            })
        else:
            error_message = api_response_data.get("message", "Pairgate refused this request.")
            return jsonify({"status": "failed", "message": f"Pairgate Error: {error_message}"}), 400

    except Exception as error:
        return jsonify({"status": "error", "message": f"Internal System Error: {str(error)}"}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
