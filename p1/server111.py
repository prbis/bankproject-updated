import os
from datetime import datetime, timedelta
import joblib
from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

import bcrypt
import jwt


# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')  # Fallback for development

# MongoDB Configuration
MONGO_URI = os.getenv(
    'MONGO_URI',
    "mongodb+srv://ashrafuddinrafat:zspkkdmFMioU3vEa@cluster0.pq8jro5.mongodb.net/banking_system?retryWrites=true&w=majority"
)

client = MongoClient(MONGO_URI)
db = client['banking_system']
tickets_collection = db['tickets']
accounts_collection = db['accounts']
transactions_collection = db['transactions']
shop_collection = db['shop']


# Define possible intents
INTENTS = [
    "transfer_money",
    "check_balance",
    "view_transaction_history",
    "create_ticket",
    "view_tickets",
    "monthly_expenses_summary",
    "future_expenses_prediction",
    "greeting",
    "goodbye",
    "unknown"
]

# JWT decorator to protect routes
def token_required(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing!'}), 403
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
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

# User Registration Endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password", "").encode('utf-8')
    
    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required!'}), 400

    if accounts_collection.find_one({"email": email}):
        return jsonify({'error': 'Email already exists!'}), 400

    # Password policy: minimum 8 characters
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long!'}), 400

    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

    new_account = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "balance": 0.0,
        "created_at": datetime.utcnow()
    }
    result = accounts_collection.insert_one(new_account)
    account_id = str(result.inserted_id)


    return jsonify({'account_id': account_id, 'message': 'Account registered successfully!'}), 201

# User Login Endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password", "").encode('utf-8')

    if not email or not password:
        return jsonify({'error': 'Email and password are required!'}), 400

    user = accounts_collection.find_one({"email": email})
    if not user or not bcrypt.checkpw(password, user['password']):
        return jsonify({'error': 'Invalid credentials!'}), 401

    token = jwt.encode({
        'account_id': str(user['_id']),
        'exp': datetime.utcnow() + timedelta(hours=1)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token}), 200

# Check Balance Endpoint
@app.route('/balance', methods=['GET'])
@token_required
def check_balance(current_user):
    account_id = str(current_user['_id'])
    balance = current_user.get('balance', 0.0)
    return jsonify({'account_id': account_id, 'balance': balance}), 200

# Deposit Endpoint
@app.route('/deposit', methods=['POST'])
@token_required
def deposit(current_user):
    account_id = str(current_user['_id'])
    amount = request.json.get('amount')

    if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({'error': 'Deposit amount must be a positive number'}), 400

    try:
        accounts_collection.update_one(
            {"_id": ObjectId(account_id)},
            {"$inc": {"balance": amount}}
        )

        transaction = {
            "account_id": ObjectId(account_id),
            "type": "deposit",
            "amount": amount,
            "timestamp": datetime.utcnow()
        }
        transactions_collection.insert_one(transaction)

        updated_account = get_account(account_id)

        return jsonify({'account_id': account_id, 'balance': updated_account['balance']}), 200
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred during deposit.'}), 500

# Withdraw Endpoint
@app.route('/withdraw', methods=['POST'])
@token_required
def withdraw(current_user):
    account_id = str(current_user['_id'])
    amount = request.json.get('amount')

    if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({'error': 'Withdrawal amount must be a positive number'}), 400

    account = get_account(account_id)
    if account['balance'] < amount:
        return jsonify({'error': 'Insufficient funds'}), 400

    try:
        accounts_collection.update_one(
            {"_id": ObjectId(account_id)},
            {"$inc": {"balance": -amount}}
        )

        transaction = {
            "account_id": ObjectId(account_id),
            "type": "withdrawal",
            "amount": amount,
            "timestamp": datetime.utcnow()
        }
        transactions_collection.insert_one(transaction)

        updated_account = get_account(account_id)

        return jsonify({'account_id': account_id, 'balance': updated_account['balance']}), 200
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred during withdrawal.'}), 500

# Transfer Endpoint
@app.route('/transfer', methods=['POST'])
@token_required
def transfer(current_user):
    from_account_id = str(current_user['_id'])
    amount = request.json.get('amount')
    to_account_email = request.json.get('to_account_email')

    if not to_account_email:
        return jsonify({'error': 'Recipient email is required.'}), 400

    if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({'error': 'Transfer amount must be a positive number'}), 400

    to_account = get_account(to_account_email)
    if not to_account:
        return jsonify({'error': 'Recipient account not found'}), 404

    if str(to_account['_id']) == from_account_id:
        return jsonify({'error': 'Cannot transfer to the same account.'}), 400

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

# Shop Items Endpoint
@app.route('/shop', methods=['GET'])
@token_required
def shop_items(current_user):
    try:
        items = list(shop_collection.find())
        for item in items:
            item['_id'] = str(item['_id'])
            item['shop_name'] = item.get('Shop Name', 'Unknown Shop')
            item['category'] = item.get('Product Category', 'Uncategorized')
            item['name'] = item.get('Product Name', 'Unnamed Product')
            item['price'] = item.get('Price', 0.0)
        return jsonify({'items': items}), 200
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred while retrieving shop items.'}), 500

# Purchase Endpoint
@app.route('/purchase', methods=['POST'])
@token_required
def purchase(current_user):
    try:
        data = request.json
        item_id = data.get("item_id")
        quantity = data.get("quantity", 1)  # Default quantity to 1 if not specified

        if not item_id or not isinstance(quantity, int) or quantity <= 0:
            return jsonify({'error': 'Invalid item ID or quantity'}), 400

        # Validate and retrieve the item
        try:
            item = shop_collection.find_one({"_id": ObjectId(item_id)})
        except InvalidId:
            return jsonify({'error': 'Invalid item ID format'}), 400

        if not item:
            return jsonify({'error': 'Item not found in shop'}), 404

        # Extract necessary fields with default values
        item_name = item.get('Product Name', 'Unknown Item')
        shop_name = item.get('Shop Name', 'Unknown Shop')
        product_category = item.get('Product Category', 'Uncategorized')
        price_per_item = item.get('Price', 0.0)
        total_price = price_per_item * quantity

        # Check if user has enough balance
        if current_user.get('balance', 0.0) < total_price:
            return jsonify({'error': 'Insufficient funds for this purchase'}), 400

        # Deduct the total price from the user's balance
        update_result = accounts_collection.update_one(
            {"_id": current_user['_id']},
            {"$inc": {"balance": -total_price}}
        )

        if update_result.matched_count == 0 or update_result.modified_count == 0:
            return jsonify({'error': 'Failed to update balance'}), 500

        # Record the purchase as a transaction
        purchase_transaction = {
            "account_id": ObjectId(current_user['_id']),
            "type": "purchase",
            "item_id": ObjectId(item_id),
            "item_name": item_name,
            "shop_name": shop_name,
            "product_category": product_category,
            "quantity": quantity,
            "total_price": total_price,
            "timestamp": datetime.utcnow()
        }
        transactions_collection.insert_one(purchase_transaction)

        # Retrieve updated account information
        updated_account = get_account(current_user['_id'])


        return jsonify({
            'message': f'Successfully purchased {quantity} of {item_name}',
            'remaining_balance': updated_account.get('balance', 0.0)
        }), 200
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred during purchase.'}), 500

# Purchase History Endpoint
@app.route('/purchase_history', methods=['GET'])
@token_required
def purchase_history(current_user):
    try:
        account_id = current_user['_id']
        # Retrieve all purchase transactions for the user, sorted by timestamp descending
        purchases = list(transactions_collection.find({
            "account_id": ObjectId(account_id),
            "type": "purchase"
        }).sort("timestamp", -1))

        # Convert ObjectIds to strings and format timestamps
        for purchase in purchases:
            purchase['_id'] = str(purchase['_id'])
            purchase['account_id'] = str(purchase['account_id'])
            purchase['item_id'] = str(purchase['item_id'])
            purchase['timestamp'] = purchase['timestamp'].isoformat()

        return jsonify({'purchase_history': purchases}), 200
    except Exception as e:

        return jsonify({'error': 'An unexpected error occurred while retrieving purchase history.'}), 500

# Monthly Expense Tracking Endpoint
@app.route('/monthly_expenses', methods=['GET'])
@token_required
def monthly_expenses(current_user):
    try:
        account_id = current_user['_id']
        # Define the date range (e.g., last 6 months)
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        # Retrieve transactions within the last 6 months
        transactions = list(
            transactions_collection.find({
                "account_id": ObjectId(account_id),
                "timestamp": {"$gte": six_months_ago}
            })
        )
        
        if not transactions:
            return jsonify({'message': 'No transactions found for the past 6 months.'}), 200
        
        # Aggregate expenses by month and category
        monthly_summary = {}
        for txn in transactions:
            if txn['type'] not in ['deposit', 'transfer_in']:
                # Consider only expense types
                month = txn['timestamp'].strftime('%Y-%m')
                category = txn.get('product_category', 'Uncategorized')
                amount = txn.get('total_price', txn.get('amount', 0))
                
                if month not in monthly_summary:
                    monthly_summary[month] = {}
                
                if category not in monthly_summary[month]:
                    monthly_summary[month][category] = 0.0
                
                monthly_summary[month][category] += amount
        
        return jsonify({'monthly_expenses': monthly_summary}), 200
    
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred while retrieving monthly expenses.'}), 500


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
