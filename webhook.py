import os
from flask import Flask, request, jsonify
from supabase import create_client, Client

app = Flask(__name__)

SUPABASE_URL = os.environ["PROJECT_URL"]
SUPABASE_KEY = os.environ["SERVICE_ROLE_KEY"]
PAYSTACK_SECRET = os.environ["PAYSTACK_SECRET"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/paystack-webhook', methods=['POST'])
def paystack_webhook():
    event = request.json
    print("Received event:", event)
    
    if event['event'] == 'charge.success':
        data = event['data']
        reference = data['reference']
        amount = data['amount'] / 100

        lease_id = reference.replace("lease_", "")

        supabase.table("payments").insert({
            "lease_id": lease_id,
            "amount": amount,
            "reference": reference,
            "status": "paid"
        }).execute()

        supabase.table("leases").update({"status": "active"}).eq("id", lease_id).execute()

        return jsonify({"status": "success"}), 200
    
    return jsonify({"status": "ignored"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)