import requests
import json
import sys

# Base URL of the Flask server
#BASE_URL = "http://localhost:5000"
BASE_URL = "http://127.0.0.1:8080"



# Global variable to store JWT token
TOKEN = None

def register():
    print("\n=== User Registration ===")
    name = input("Enter your name: ").strip()
    email = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()

    payload = {
        "name": name,
        "email": email,
        "password": password
    }

    try:
        response = requests.post(f"{BASE_URL}/register", json=payload)
        data = response.json()
        if response.status_code == 201:
            print(f"Success: {data['message']}")
            print(f"Your Account ID: {data['account_id']}")
        else:
            print(f"Error: {data.get('error', 'Registration failed.')}")
    except Exception as e:
        print(f"An error occurred during registration: {e}")

def login():
    global TOKEN
    print("\n=== User Login ===")
    email = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()

    payload = {
        "email": email,
        "password": password
    }

    try:
        response = requests.post(f"{BASE_URL}/login", json=payload)
        data = response.json()
        if response.status_code == 200:
            TOKEN = data['token']
            print("Login successful!")
        else:
            print(f"Error: {data.get('error', 'Login failed.')}")
    except Exception as e:
        print(f"An error occurred during login: {e}")

def check_balance():
    if not TOKEN:
        print("You need to login first.")
        return

    print("\n=== Check Balance ===")
    headers = {
        "Authorization": TOKEN
    }

    try:
        response = requests.get(f"{BASE_URL}/balance", headers=headers)
        data = response.json()
        if response.status_code == 200:
            print(f"Account ID: {data['account_id']}")
            print(f"Current Balance: ${data['balance']}")
        else:
            print(f"Error: {data.get('error', 'Unable to retrieve balance.')}")
    except Exception as e:
        print(f"An error occurred while checking balance: {e}")

def deposit():
    if not TOKEN:
        print("You need to login first.")
        return

    print("\n=== Deposit Money ===")
    try:
        amount = float(input("Enter amount to deposit: ").strip())
    except ValueError:
        print("Invalid amount. Please enter a numerical value.")
        return

    payload = {
        "amount": amount
    }
    headers = {
        "Authorization": TOKEN
    }

    try:
        response = requests.post(f"{BASE_URL}/deposit", json=payload, headers=headers)
        data = response.json()
        if response.status_code == 200:
            print(f"Deposit successful! New Balance: ${data['balance']}")
        else:
            print(f"Error: {data.get('error', 'Deposit failed.')}")
    except Exception as e:
        print(f"An error occurred during deposit: {e}")

def withdraw():
    if not TOKEN:
        print("You need to login first.")
        return

    print("\n=== Withdraw Money ===")
    try:
        amount = float(input("Enter amount to withdraw: ").strip())
    except ValueError:
        print("Invalid amount. Please enter a numerical value.")
        return

    payload = {
        "amount": amount
    }
    headers = {
        "Authorization": TOKEN
    }

    try:
        response = requests.post(f"{BASE_URL}/withdraw", json=payload, headers=headers)
        data = response.json()
        if response.status_code == 200:
            print(f"Withdrawal successful! New Balance: ${data['balance']}")
        else:
            print(f"Error: {data.get('error', 'Withdrawal failed.')}")
    except Exception as e:
        print(f"An error occurred during withdrawal: {e}")

def transfer():
    if not TOKEN:
        print("You need to login first.")
        return

    print("\n=== Transfer Money ===")
    to_email = input("Enter recipient's email: ").strip()
    try:
        amount = float(input("Enter amount to transfer: ").strip())
    except ValueError:
        print("Invalid amount. Please enter a numerical value.")
        return

    payload = {
        "to_account_email": to_email,
        "amount": amount
    }
    headers = {
        "Authorization": TOKEN
    }

    try:
        response = requests.post(f"{BASE_URL}/transfer", json=payload, headers=headers)
        data = response.json()
        if response.status_code == 200:
            print(f"Transfer successful! {data['message']}")
        else:
            print(f"Error: {data.get('error', 'Transfer failed.')}")
    except Exception as e:
        print(f"An error occurred during transfer: {e}")

def view_transaction_history():
    if not TOKEN:
        print("You need to login first.")
        return

    print("\n=== Transaction History ===")
    headers = {
        "Authorization": TOKEN
    }

    try:
        response = requests.get(f"{BASE_URL}/transaction_history", headers=headers)
        data = response.json()
        if response.status_code == 200:
            transactions = data.get('transaction_history', [])
            if not transactions:
                print("No transactions found.")
                return
            print("Recent Transactions:")
            for txn in transactions[:10]:  # Show last 10 transactions
                txn_type = txn.get('type', 'N/A').replace('_', ' ').title()
                amount = txn.get('amount', 0)
                timestamp = txn.get('timestamp', 'N/A')
                if txn_type in ['Transfer Out', 'Transfer In']:
                    direction = 'to' if txn_type == 'Transfer Out' else 'from'
                    related_email = txn.get('to_account_id') if txn_type == 'Transfer Out' else txn.get('from_account_id')
                    print(f"{txn_type} of ${amount} {direction} {related_email} on {timestamp}")
                else:
                    print(f"{txn_type} of ${amount} on {timestamp}")
        else:
            print(f"Error: {data.get('error', 'Unable to retrieve transaction history.')}")
    except Exception as e:
        print(f"An error occurred while retrieving transaction history: {e}")

def chatbot_interaction():
    if not TOKEN:
        print("You need to login first.")
        return

    print("\n=== Chatbot Interaction ===")
    print("Type 'exit' to return to the main menu.")

    headers = {
        "Authorization": TOKEN
    }

    while True:
        message = input("You: ").strip()
        if message.lower() == 'exit':
            break
        if not message:
            print("Please enter a message.")
            continue

        payload = {
            "message": message
        }

        try:
            response = requests.post(f"{BASE_URL}/chatbot", json=payload, headers=headers)
            data = response.json()
            if response.status_code == 200:
                print(f"Bot: {data.get('response', '')}")
            else:
                print(f"Error: {data.get('error', 'Chatbot failed.')}")
        except Exception as e:
            print(f"An error occurred during chatbot interaction: {e}")

def main_menu():
    while True:
        print("\n=== Banking Client Application ===")
        print("1. Register")
        print("2. Login")
        print("3. Check Balance")
        print("4. Deposit Money")
        print("5. Withdraw Money")
        print("6. Transfer Money")
        print("7. View Transaction History")
        print("8. Chatbot Interaction")
        print("9. Exit")

        choice = input("Select an option (1-9): ").strip()

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
            view_transaction_history()
        elif choice == '8':
            chatbot_interaction()
        elif choice == '9':
            print("Exiting the application. Goodbye!")
            sys.exit()
        else:
            print("Invalid option. Please select a number between 1 and 9.")

if __name__ == "__main__":
    main_menu()
