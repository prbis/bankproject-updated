import requests
import json
from datetime import datetime

# Configuration
#API_BASE_URL = 'http://localhost:5000'  # Update if your Flask server is hosted elsewhere
API_BASE_URL = 'http://banking-app-service-1-389718663490.us-central1.run.app:443'  # Update if your Flask server is hosted elsewhere
#API_BASE_URL =banking-app-service-1-389718663490.us-central1.run.app:443

#  //process.env.GRPC_SERVER_ADDRESS || 'localhost:50051',
 # process.env.GRPC_SERVER_ADDRESS || 'grpc-server-99990659129.us-central1.run.app:443',

# Initialize session to persist cookies (if any)
session = requests.Session()

# Store JWT token after login
token = None

def register():
    print("\n=== User Registration ===")
    name = input("Enter your name: ").strip()
    email = input("Enter your email: ").strip()
    password = input("Enter your password (min 8 characters): ").strip()
    
    payload = {
        "name": name,
        "email": email,
        "password": password
    }
    
    try:
        response = session.post(f"{API_BASE_URL}/register", json=payload)
        if response.status_code == 201:
            data = response.json()
            print(f"Success: {data['message']}")
            print(f"Your Account ID: {data['account_id']}")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Registration failed.')}")
    except Exception as e:
        print(f"Exception during registration: {e}")

def login():
    global token
    print("\n=== User Login ===")
    email = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()
    
    payload = {
        "email": email,
        "password": password
    }
    
    try:
        response = session.post(f"{API_BASE_URL}/login", json=payload)
        if response.status_code == 200:
            data = response.json()
            token = data['token']
            print("Login successful!")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Login failed.')}")
    except Exception as e:
        print(f"Exception during login: {e}")

def get_headers():
    if not token:
        print("You need to login first.")
        return None
    return {
        "Authorization": f"Bearer {token}"
    }

def check_balance():
    print("\n=== Check Balance ===")
    headers = get_headers()
    if not headers:
        return
    try:
        response = session.get(f"{API_BASE_URL}/balance", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"Account ID: {data['account_id']}")
            print(f"Current Balance: ${data['balance']:.2f}")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Failed to retrieve balance.')}")
    except Exception as e:
        print(f"Exception during balance check: {e}")

def deposit():
    print("\n=== Deposit Funds ===")
    headers = get_headers()
    if not headers:
        return
    amount = input("Enter amount to deposit: ").strip()
    try:
        amount = float(amount)
        if amount <= 0:
            print("Amount must be positive.")
            return
    except ValueError:
        print("Invalid amount.")
        return
    
    payload = {
        "amount": amount
    }
    
    try:
        response = session.post(f"{API_BASE_URL}/deposit", headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"Deposit successful! New Balance: ${data['balance']:.2f}")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Deposit failed.')}")
    except Exception as e:
        print(f"Exception during deposit: {e}")

def withdraw():
    print("\n=== Withdraw Funds ===")
    headers = get_headers()
    if not headers:
        return
    amount = input("Enter amount to withdraw: ").strip()
    try:
        amount = float(amount)
        if amount <= 0:
            print("Amount must be positive.")
            return
    except ValueError:
        print("Invalid amount.")
        return
    
    payload = {
        "amount": amount
    }
    
    try:
        response = session.post(f"{API_BASE_URL}/withdraw", headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"Withdrawal successful! New Balance: ${data['balance']:.2f}")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Withdrawal failed.')}")
    except Exception as e:
        print(f"Exception during withdrawal: {e}")

def transfer():
    print("\n=== Transfer Money ===")
    headers = get_headers()
    if not headers:
        return
    amount = input("Enter amount to transfer: ").strip()
    to_email = input("Enter recipient's email: ").strip()
    
    try:
        amount = float(amount)
        if amount <= 0:
            print("Amount must be positive.")
            return
    except ValueError:
        print("Invalid amount.")
        return
    
    payload = {
        "amount": amount,
        "to_account_email": to_email
    }
    
    try:
        response = session.post(f"{API_BASE_URL}/transfer", headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"Transfer successful: {data['message']}")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Transfer failed.')}")
    except Exception as e:
        print(f"Exception during transfer: {e}")

def transaction_history():
    print("\n=== Transaction History ===")
    headers = get_headers()
    if not headers:
        return
    try:
        response = session.get(f"{API_BASE_URL}/transaction_history", headers=headers)
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('transaction_history', [])
            if not transactions:
                print("No transactions found.")
                return
            for txn in transactions:
                print("-" * 40)
                print(f"Type: {txn.get('type', 'N/A')}")
                print(f"Amount: ${txn.get('amount', 0):.2f}")
                if 'to_account_id' in txn:
                    print(f"To Account ID: {txn.get('to_account_id')}")
                if 'from_account_id' in txn:
                    print(f"From Account ID: {txn.get('from_account_id')}")
                if txn.get('type') == 'purchase':
                    print(f"Item Name: {txn.get('item_name', 'N/A')}")
                    print(f"Shop Name: {txn.get('shop_name', 'N/A')}")
                    print(f"Quantity: {txn.get('quantity', 1)}")
                print(f"Timestamp: {txn.get('timestamp', 'N/A')}")
            print("-" * 40)
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Failed to retrieve transaction history.')}")
    except Exception as e:
        print(f"Exception during fetching transaction history: {e}")

def shop_items():
    print("\n=== Shop Items ===")
    headers = get_headers()
    if not headers:
        return
    try:
        response = session.get(f"{API_BASE_URL}/shop", headers=headers)
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            if not items:
                print("No items available in the shop.")
                return
            print(f"{'ID':<25} {'Name':<20} {'Shop':<20} {'Category':<15} {'Price ($)':<10}")
            print("-" * 90)
            for item in items:
                print(f"{item.get('_id', 'N/A'):<25} {item.get('name', 'N/A'):<20} {item.get('shop_name', 'N/A'):<20} {item.get('category', 'N/A'):<15} {item.get('price', 0):<10.2f}")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Failed to retrieve shop items.')}")
    except Exception as e:
        print(f"Exception during fetching shop items: {e}")

def purchase_item():
    print("\n=== Purchase Item ===")
    headers = get_headers()
    if not headers:
        return
    item_id = input("Enter the Item ID to purchase: ").strip()
    quantity = input("Enter quantity to purchase: ").strip()
    
    try:
        quantity = int(quantity)
        if quantity <= 0:
            print("Quantity must be at least 1.")
            return
    except ValueError:
        print("Invalid quantity.")
        return
    
    payload = {
        "item_id": item_id,
        "quantity": quantity
    }
    
    try:
        response = session.post(f"{API_BASE_URL}/purchase", headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['message']}")
            print(f"Remaining Balance: ${data['remaining_balance']:.2f}")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Purchase failed.')}")
    except Exception as e:
        print(f"Exception during purchase: {e}")

def purchase_history():
    print("\n=== Purchase History ===")
    headers = get_headers()
    if not headers:
        return
    try:
        response = session.get(f"{API_BASE_URL}/purchase_history", headers=headers)
        if response.status_code == 200:
            data = response.json()
            purchases = data.get('purchase_history', [])
            if not purchases:
                print("No purchase history found.")
                return
            for purchase in purchases:
                print("-" * 40)
                print(f"Item Name: {purchase.get('item_name', 'N/A')}")
                print(f"Shop Name: {purchase.get('shop_name', 'N/A')}")
                print(f"Category: {purchase.get('product_category', 'N/A')}")
                print(f"Quantity: {purchase.get('quantity', 1)}")
                print(f"Total Price: ${purchase.get('total_price', 0):.2f}")
                print(f"Timestamp: {purchase.get('timestamp', 'N/A')}")
            print("-" * 40)
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Failed to retrieve purchase history.')}")
    except Exception as e:
        print(f"Exception during fetching purchase history: {e}")

def monthly_expenses():
    print("\n=== Monthly Expenses Summary ===")
    headers = get_headers()
    if not headers:
        return
    try:
        response = session.get(f"{API_BASE_URL}/monthly_expenses", headers=headers)
        if response.status_code == 200:
            data = response.json()
            monthly_expenses = data.get('monthly_expenses', {})
            if not monthly_expenses:
                print("No expenses data available.")
                return
            for month, categories in monthly_expenses.items():
                print(f"\nMonth: {month}")
                for category, amount in categories.items():
                    print(f"  - {category}: ${amount:.2f}")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Failed to retrieve monthly expenses.')}")
    except Exception as e:
        print(f"Exception during fetching monthly expenses: {e}")

def predict_expenses():
    print("\n=== Predict Future Expenses ===")
    headers = get_headers()
    if not headers:
        return
    try:
        response = session.get(f"{API_BASE_URL}/predict_expenses", headers=headers)
        if response.status_code == 200:
            data = response.json()
            prediction = data.get('prediction', [])
            if prediction:
                print("Predicted Expenses for the Next 3 Months:")
                for pred in prediction:
                    print(f"{pred['Month']}: {pred['Predicted Expense']}")
            elif data.get('message'):
                print(data['message'])
            elif data.get('error'):
                print(f"Error: {data['error']}")
            else:
                print("No prediction data available.")
        else:
            data = response.json()
            print(f"Error: {data.get('error', 'Failed to retrieve expense predictions.')}")
    except Exception as e:
        print(f"Exception during fetching expense predictions: {e}")

def chatbot_interaction():
    print("\n=== Chatbot Interaction ===")
    headers = get_headers()
    if not headers:
        return
    print("Type 'exit' to end the chat.")
    while True:
        message = input("You: ").strip()
        if message.lower() == 'exit':
            print("Chatbot: Goodbye!")
            break
        if not message:
            print("Please enter a message.")
            continue
        payload = {
            "message": message
        }
        try:
            response = session.post(f"{API_BASE_URL}/chatbot", headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get('response', "I didn't understand that.")
                print(f"Chatbot: {bot_response}")
            else:
                data = response.json()
                print(f"Error: {data.get('error', 'Chatbot failed to respond.')}")
        except Exception as e:
            print(f"Exception during chatbot interaction: {e}")

def main_menu():
    while True:
        print("\n=== Banking System Client Testing ===")
        print("1. Register")
        print("2. Login")
        print("3. Check Balance")
        print("4. Deposit Funds")
        print("5. Withdraw Funds")
        print("6. Transfer Money")
        print("7. View Transaction History")
        print("8. View Shop Items")
        print("9. Purchase Item")
        print("10. View Purchase History")
        print("11. View Monthly Expenses")
        print("12. Predict Future Expenses")
        print("13. Chatbot Interaction")
        print("14. Exit")
        
        choice = input("Select an option (1-14): ").strip()
        
        if choice == '1':
            register()
        elif choice == '2':
            login()
        elif choice == '3':
            check_balance()
        elif choice == '4':
            deposit()
        elif choice == '5':
            withdraw()
        elif choice == '6':
            transfer()
        elif choice == '7':
            transaction_history()
        elif choice == '8':
            shop_items()
        elif choice == '9':
            purchase_item()
        elif choice == '10':
            purchase_history()
        elif choice == '11':
            monthly_expenses()
        elif choice == '12':
            predict_expenses()
        elif choice == '13':
            chatbot_interaction()
        elif choice == '14':
            print("Exiting the client. Goodbye!")
            break
        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == "__main__":
    main_menu()
