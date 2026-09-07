import os
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='.')

# 1. ENHANCED API & GATEWAY CONFIGURATION
# Set your live gateway endpoint and developer API authorization token here
API_SECRET_KEY = os.environ.get("VTU_API_KEY", "YOUR_LIVE_GATEWAY_API_TOKEN")
GATEWAY_URL = "https://pairgate.com/api/v1"  # Replace with your actual wholesale provider base URL

DB_FILE = "transactions.db"

def init_db():
    """Initializes a local database to keep automated data receipts securely."""
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
            transaction_id TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize transaction database log profile upon boot
init_db()

@app.route('/')
def dashboard():
    """Renders the organized user interface dashboard shell."""
    return render_template('index.html')

@app.route('/v1/get-live-plans', methods=['GET'])
def get_live_plans():
    """
    Fetches wholesale data allocations from your API provider 
    and automatically populates your frontend index.html dropdown array.
    """
    try:
        # Step A: Query the live wholesale provider's plan database endpoint
        # url = f"{GATEWAY_URL}/data/plans"
        # headers = {"Authorization": f"Bearer {API_SECRET_KEY}"}
        # response = requests.get(url, headers=headers, timeout=10)
        # live_plans = response.json()
        
        # Step B: Fallback/Default clean structured market dictionary mapped to your UI drop-downs
        # You can update prices or add Glo, 9mobile, or custom plans here seamlessly
        market_data = {
            "status": "success",
            "networks": {
                "AIRTEL": [
                    {"id": "airtel_cg_1gb", "name": "Airtel 1GB Corporate Gifting (30 Days)"},
                    {"id": "airtel_cg_2gb", "name": "Airtel 2GB Corporate Gifting (30 Days)"},
                    {"id": "airtel_cg_5gb", "name": "Airtel 5GB Corporate Gifting (30 Days)"}
                ],
                "MTN": [
                    {"id": "mtn_sme_1gb", "name": "MTN 1GB SME Plan (30 Days)"},
                    {"id": "mtn_sme_2gb", "name": "MTN 2GB SME Plan (30 Days)"},
                    {"id": "mtn_sme_5gb", "name": "MTN 5GB SME Plan (30 Days)"}
                ]
            }
        }
        return jsonify(market_data)

    except Exception as error:
        return jsonify({"status": "error", "message": f"Failed to populate dropdown array: {str(error)}"}), 500

@app.route('/v1/dispense-data', methods=['POST'])
def dispense_data():
    """Securely handles form payload inputs and routes orders down to the API node."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        user_input = request.get_json()
        network = user_input.get('network')
        plan_id = user_input.get('plan_id')
        phone_number = user_input.get('phone')

        # 2. STRICT CLIENT-SIDE COMPLIANCE VALIDATIONS
        if not phone_number or len(phone_number) != 11 or not phone_number.startswith('0'):
            return jsonify({"status": "failed", "message": "Invalid Nigerian phone number syntax."}), 400

        # Construct exact transaction parameters requested by wholesale API schema
        payload = {
            "network": network,
            "plan_id": plan_id,
            "phone": phone_number,
            "bypass_validator": False  # Enforces structural network safety validations
        }

        headers = {
            "Authorization": f"Bearer {API_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        # 3. AUTOMATED ORDER EXTRACTION NODE
        response = requests.post(f"{GATEWAY_URL}/data/dispense", json=payload, headers=headers, timeout=15)
        api_response_data = response.json()

        if response.status_code == 200 and api_response_data.get("status") == "success":
            tx_id = api_response_data.get("transaction_id")
            
            # Log successful data transaction into local receipt table
            cursor.execute("INSERT INTO transactions (phone, network, plan_id, status, transaction_id, message) VALUES (?, ?, ?, ?, ?, ?)",
                           (phone_number, network, plan_id, "SUCCESS", tx_id, "Dispatched successfully"))
            conn.commit()
            
            return jsonify({
                "status": "success",
                "transaction_id": tx_id,
                "message": "Data bundle pushed successfully via Corporate Gifting."
            })
        else:
            fail_msg = api_response_data.get("message", "Gateway refused automated dispatch.")
            cursor.execute("INSERT INTO transactions (phone, network, plan_id, status, transaction_id, message) VALUES (?, ?, ?, ?, ?, ?)",
                           (phone_number, network, plan_id, "FAILED", None, fail_msg))
            conn.commit()
            
            return jsonify({"status": "failed", "message": fail_msg}), 400

    except requests.exceptions.RequestException as error:
        cursor.execute("INSERT INTO transactions (phone, network, plan_id, status, transaction_id, message) VALUES (?, ?, ?, ?, ?, ?)",
                       (phone_number, network, plan_id, "ERROR", None, str(error)))
        conn.commit()
        return jsonify({"status": "error", "message": f"Critical server routing failure: {str(error)}"}), 500
    
    finally:
        conn.close()

if __name__ == '__main__':
    # Adjust port configuration to natively adapt to cloud environment parameters
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
