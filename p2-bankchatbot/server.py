from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
import bcrypt
import jwt
from datetime import datetime, timedelta
import re
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key

# MongoDB connection
client = MongoClient("mongodb+srv://ashrafuddinrafat:zspkkdmFMioU3vEa@cluster0.pq8jro5.mongodb.net/banking_system?retryWrites=true&w=majority")
db = client['banking_system']
tickets_collection = db['tickets']          # New collection for tickets
accounts_collection = db['accounts']
transactions_collection = db['transactions']

# Initialize DialoGPT model and tokenizer
print("Loading DialoGPT-small model...")
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")
print("DialoGPT-small model loaded successfully.")

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Conversation history: {user_id: [conversation_ids]}
conversation_history = {}

# Define possible intents
INTENTS = [
    "transfer_money",
    "check_balance",
    "view_transaction_history",
    "create_ticket",          # Existing intent
    "view_tickets",           # New intent
    "greeting",
    "goodbye",
    "unknown"
]

# Helper function to retrieve account by ID or email
def get_account(identifier):
    if isinstance(identifier, ObjectId):
        return accounts_collection.find_one({"_id": identifier})
    elif isinstance(identifier, str):
        try:
            obj_id = ObjectId(identifier)
            account = accounts_collection.find_one({"_id": obj_id})
            if account:
                return account
        except InvalidId:
            pass
        return accounts_collection.find_one({"email": identifier})
    else:
        return None

# JWT decorator to protect routes
def token_required(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing!'}), 403
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = get_account(data['account_id'])
            if not current_user:
                return jsonify({'error': 'User not found!'}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 403
        return f(current_user, *args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Register endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password").encode('utf-8')
    
    if accounts_collection.find_one({"email": email}):
        return jsonify({'error': 'Email already exists!'}), 400

    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

    new_account = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "balance": 0,
        "created_at": datetime.utcnow()
    }
    result = accounts_collection.insert_one(new_account)
    account_id = str(result.inserted_id)

    return jsonify({'account_id': account_id, 'message': 'Account registered successfully!'}), 201

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password").encode('utf-8')
    
    user = accounts_collection.find_one({"email": email})
    if not user or not bcrypt.checkpw(password, user['password']):
        return jsonify({'error': 'Invalid credentials!'}), 401

    token = jwt.encode({
        'account_id': str(user['_id']),
        'exp': datetime.utcnow() + timedelta(hours=1)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token}), 200

# Check balance endpoint
@app.route('/balance', methods=['GET'])
@token_required
def check_balance(current_user):
    account_id = str(current_user['_id'])
    account = get_account(account_id)
    return jsonify({'account_id': account_id, 'balance': account['balance']}), 200

# Transfer endpoint
@app.route('/transfer', methods=['POST'])
@token_required
def transfer(current_user):
    from_account_id = str(current_user['_id'])
    amount = request.json.get('amount')
    to_account_email = request.json.get('to_account_email')

    if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({'error': 'Transfer amount must be a positive number'}), 400

    to_account = get_account(to_account_email)
    if not to_account:
        return jsonify({'error': 'Recipient account not found'}), 404

    if current_user['balance'] < amount:
        return jsonify({'error': 'Insufficient funds'}), 400

    try:
        with client.start_session() as session:
            with session.start_transaction():
                accounts_collection.update_one({"_id": ObjectId(from_account_id)}, {"$inc": {"balance": -amount}}, session=session)
                accounts_collection.update_one({"_id": ObjectId(to_account['_id'])}, {"$inc": {"balance": amount}}, session=session)

                transaction_out = {
                    "account_id": ObjectId(from_account_id),
                    "type": "transfer_out",
                    "amount": amount,
                    "to_account_id": ObjectId(to_account['_id']),
                    "timestamp": datetime.utcnow()
                }
                transaction_in = {
                    "account_id": ObjectId(to_account['_id']),
                    "type": "transfer_in",
                    "amount": amount,
                    "from_account_id": ObjectId(from_account_id),
                    "timestamp": datetime.utcnow()
                }
                transactions_collection.insert_many([transaction_out, transaction_in], session=session)
        return jsonify({'message': 'Transfer successful'}), 200
    except Exception as e:
        print(f"Transfer error: {e}")
        return jsonify({'error': 'An error occurred during the transfer.'}), 500

# Transaction History Endpoint
@app.route('/transaction_history', methods=['GET'])
@token_required
def transaction_history(current_user):
    try:
        account_id = current_user['_id']

        # Retrieve transactions from the database
        transactions = list(
            transactions_collection.find({"account_id": ObjectId(account_id)}).sort("timestamp", -1)
        )

        # Serialize transactions and handle purchase-specific logic
        serialized_transactions = []
        for txn in transactions:
            serialized_transaction = {
                '_id': str(txn['_id']),
                'account_id': str(txn['account_id']),
                'type': txn.get('type', 'N/A').replace('_', ' ').title(),
                'amount': txn.get('amount', 0),  # Default for non-purchase transactions
                'timestamp': txn['timestamp'].isoformat() if 'timestamp' in txn else None
            }

            # Handle additional fields for purchase transactions
            if txn.get('type') == 'purchase':
                serialized_transaction['amount'] = txn.get('total_price', 0)  # Use total_price for purchases
                serialized_transaction['item_name'] = txn.get('item_name', 'Unknown Item')
                serialized_transaction['shop_name'] = txn.get('shop_name', 'Unknown Shop')
                serialized_transaction['quantity'] = txn.get('quantity', 1)

            # Add related account information for transfers
            if "to_account_id" in txn:
                serialized_transaction['to_account_id'] = str(txn['to_account_id'])
            if "from_account_id" in txn:
                serialized_transaction['from_account_id'] = str(txn['from_account_id'])

            serialized_transactions.append(serialized_transaction)

        return jsonify({'transaction_history': serialized_transactions or []}), 200

    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred while retrieving transaction history.'}), 500


# Chatbot endpoint
@app.route('/chatbot', methods=['POST'])
@token_required
def chatbot(current_user):
    data = request.json
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'response': 'Please provide a message.'}), 400

    # Detect intent
    intent = detect_intent(message)

    # Handle intents
    if intent == "transfer_money":
        response = handle_transfer_money(current_user, message)
    elif intent == "check_balance":
        response = handle_check_balance(current_user)
    elif intent == "view_transaction_history":
        response = handle_view_transaction_history(current_user)
    elif intent == "create_ticket":
        response = handle_create_ticket(current_user, message)
    elif intent == "view_tickets":    # New intent handling
        response = handle_view_tickets(current_user)
    else:
        # If intent is unknown, generate response using DialoGPT
        response = generate_response(current_user['_id'], message)

    return jsonify({'response': response}), 200

# Intent detection function
def detect_intent(message):
    message = message.lower()
    if "transfer" in message and "to" in message:
        return "transfer_money"
    elif "balance" in message:
        return "check_balance"
    elif "transaction history" in message or "transactions" in message:
        return "view_transaction_history"
    elif any(ticket_phrase in message for ticket_phrase in ["help me", "report a problem", "create a ticket", "i need assistance", "support"]):
        return "create_ticket"
    elif any(view_phrase in message for view_phrase in ["view my tickets", "show my tickets", "my support requests", "view my support tickets"]):
        return "view_tickets"     # New intent detection
    else:
        return "unknown"

# Handler functions for intents
def handle_transfer_money(current_user, message):
    # Extract amount and recipient email using regex
    transfer_pattern = r"transfer\s+\$?(\d+(?:\.\d+)?)\s+to\s+([\w\.-]+@[\w\.-]+\.\w+)"
    match = re.search(transfer_pattern, message, re.IGNORECASE)
    
    if not match:
        return "Please specify the amount and recipient's email. For example, 'Transfer $100 to recipient@example.com'."
    
    amount = float(match.group(1))
    to_email = match.group(2)
    
    if amount <= 0:
        return "Transfer amount must be a positive number."
    
    to_account = get_account(to_email)
    if not to_account:
        return "Recipient account not found."
    
    if current_user['balance'] < amount:
        return "Insufficient funds for this transfer."
    
    from_account_id = str(current_user['_id'])
    
    try:
        with client.start_session() as session:
            with session.start_transaction():
                accounts_collection.update_one({"_id": ObjectId(from_account_id)}, {"$inc": {"balance": -amount}}, session=session)
                accounts_collection.update_one({"_id": ObjectId(to_account['_id'])}, {"$inc": {"balance": amount}}, session=session)

                transaction_out = {
                    "account_id": ObjectId(from_account_id),
                    "type": "transfer_out",
                    "amount": amount,
                    "to_account_id": ObjectId(to_account['_id']),
                    "timestamp": datetime.utcnow()
                }
                transaction_in = {
                    "account_id": ObjectId(to_account['_id']),
                    "type": "transfer_in",
                    "amount": amount,
                    "from_account_id": ObjectId(from_account_id),
                    "timestamp": datetime.utcnow()
                }
                transactions_collection.insert_many([transaction_out, transaction_in], session=session)
        return f"Transferred ${amount} to {to_email} successfully."
    except Exception as e:
        print(f"Transfer error: {e}")
        return "An error occurred during the transfer."

def handle_check_balance(current_user):
    account_id = str(current_user['_id'])
    account = get_account(account_id)
    return f"Your current balance is ${account['balance']}."

def handle_view_transaction_history(current_user):
    account_id = str(current_user['_id'])
    transactions = list(transactions_collection.find({"account_id": ObjectId(account_id)}).sort("timestamp", -1))
    
    if not transactions:
        return "No transactions found."

    # Format transactions
    history = []
    for txn in transactions[:10]:  # Limit to last 10 transactions
        txn_type = txn['type'].replace('_', ' ').title()
        amount = txn['amount']
        timestamp = txn['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if txn_type in ['Transfer Out', 'Transfer In']:
            related_account_id = txn.get('to_account_id') if 'to_account_id' in txn else txn.get('from_account_id')
            related_account = get_account(str(related_account_id))
            related_email = related_account['email'] if related_account else 'Unknown'
            direction = 'to' if 'to_account_id' in txn else 'from'
            history.append(f"{txn_type} of ${amount} {direction} {related_email} on {timestamp}")
        else:
            history.append(f"{txn_type} of ${amount} on {timestamp}")

    response_message = "Here are your recent transactions:\n\n" + "\n".join(history)
    return response_message

def handle_create_ticket(current_user, message):
    # Extract issue description
    # Assuming the user provides the issue after a keyword, e.g., "create a ticket: My account is locked."
    issue_pattern = r"create a ticket[:\-]?\s*(.*)"
    match = re.search(issue_pattern, message, re.IGNORECASE)
    
    if match:
        issue_description = match.group(1).strip()
    else:
        # If issue description is not provided directly, prompt the user to enter it
        return "Sure, I can help you create a support ticket. Please describe your issue."
    
    if not issue_description:
        return "Please provide a detailed description of your issue to create a support ticket."
    
    # Create the ticket document
    ticket = {
        "user_id": ObjectId(current_user['_id']),
        "issue_description": issue_description,
        "status": "open",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    try:
        result = tickets_collection.insert_one(ticket)
        ticket_id = str(result.inserted_id)
        return f"Your support ticket has been created successfully! The next available agent will directly call you to support you or you can contact center. Ticket ID: {ticket_id}"
    except Exception as e:
        print(f"Ticket creation error: {e}")
        return "An error occurred while creating your support ticket. Please try again later."

def handle_view_tickets(current_user):
    account_id = str(current_user['_id'])
    
    # Retrieve tickets belonging to the current user
    tickets = list(tickets_collection.find({"user_id": ObjectId(account_id)}).sort("created_at", -1))
    
    if not tickets:
        return "You have no support tickets."
    
    # Format tickets
    ticket_messages = []
    for ticket in tickets[:10]:  # Limit to last 10 tickets
        ticket_id = str(ticket['_id'])
        issue = ticket.get('issue_description', 'No description provided.')
        status = ticket.get('status', 'N/A').title()
        created_at = ticket.get('created_at').strftime('%Y-%m-%d %H:%M:%S')
        ticket_messages.append(f"**Ticket ID:** {ticket_id}\n**Issue:** {issue}\n**Status:** {status}\n**Created At:** {created_at}\n")
    
    response_message = "Here are your recent support tickets:\n\n" + "\n".join(ticket_messages)
    return response_message

def handle_greetings(intent):
    if intent == "greeting":
        return "Hello! How can I assist you today?"
    elif intent == "goodbye":
        return "Goodbye! Have a great day!"
    else:
        return "Hello!"

# Generate response using DialoGPT
def generate_response(user_id, user_message):
    # Initialize conversation history for the user if not present
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    # Encode the new user input and append to the conversation history
    new_user_input_ids = tokenizer.encode(user_message + tokenizer.eos_token, return_tensors='pt').to(device)
    conversation_history[user_id].append(new_user_input_ids)
    
    # Concatenate conversation history
    bot_input_ids = torch.cat(conversation_history[user_id], dim=-1)
    
    # Generate a response
    chat_history_ids = model.generate(
        bot_input_ids,
        max_length=1000,
        pad_token_id=tokenizer.eos_token_id,
        no_repeat_ngram_size=3,
        do_sample=True,
        top_k=50,
        top_p=0.95,
        temperature=0.75
    )
    
    # Get the bot's response
    response = tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
    
    # Append the bot's response to the conversation history
    conversation_history[user_id].append(chat_history_ids[:, bot_input_ids.shape[-1]:])
    
    # Limit conversation history to last 10 exchanges
    if len(conversation_history[user_id]) > 10:
        conversation_history[user_id] = conversation_history[user_id][-10:]
    
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))  # Default to 8080 if PORT is not set
    app.run(host='0.0.0.0', port=port)

#if __name__ == '__main__':
 #   app.run(debug=True)
