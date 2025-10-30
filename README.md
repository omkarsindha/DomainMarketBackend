# Domain Markets Backend

This project is a backend for a domain marketplace, built with Python, FastAPI, and SQLAlchemy. It provides a RESTful API for users to buy, sell, and manage domain names. The platform includes features for domain searching, registration, user authentication, fixed-price listings, and real-time auctions. It integrates with the Namecheap API for domain registration and management and Stripe for payment processing.

The application also uses Celery with Redis to run scheduled background tasks for managing auction expirations and domain lifecycle events.

---

## Key Features

*   **User Authentication**: Secure user registration and login using JWT tokens.
*   **Domain Search**: Check domain availability and get suggestions for similar domains.
*   **Domain Registration**: Purchase and register domains through the Namecheap API.
*   **Payment Integration**: Securely process payments using Stripe, including saving payment methods for future use.
*   **Auction System**: Users can create auctions for their domains, place bids, and win domains. Auctions are automatically closed by a background worker.
*   **Fixed-Price Listings**: Users can list their domains for sale at a fixed price.
*   **Domain Management**: Owners can manage their domain's DNS records, set up URL forwarding, and view domain information.
*   **Background Tasks**: Celery workers handle time-based tasks like closing expired auctions and managing expired domains.
*   **Transactional History**: Users can view a complete history of their purchases, sales, and other transactions.

---

## Setup Instructions

### **1) Clone the Repository**
First, clone this repository to your local machine:
```sh
git clone https://github.com/omkarsindha/DomainMarketBackend.git
cd DomainMarketBackend
```

### **2) Create a Virtual Environment**
Set up a virtual environment to manage dependencies:
```sh
python -m venv .venv
```
Activate the virtual environment:
```sh
.venv\Scripts\activate
```

### **3) Install Dependencies**
Install the required Python packages:
```sh
pip install -r requirements.txt
```

### **4) Install and Run Redis**
This project uses Redis as a message broker for Celery. For Windows, you can download and install it from the official Microsoft archive release page:
*   [https://github.com/MicrosoftArchive/redis/releases](https://github.com/MicrosoftArchive/redis/releases)

Once installed, ensure the Redis server is running before starting the Celery workers.

### **5) Configure PostgreSQL Database**
This project uses a locally installed PostgreSQL for development.
*   Make sure you have PostgreSQL installed and running.
*   Create a new database for the project.
*   Edit the `DATABASE_URL` in `database/connection.py` with your database credentials (username, password, and database name).

### **6) Configure Environment Variables**
This project uses environment variables to store sensitive API keys. Create a `.env` file in the project's root directory and add your credentials.

**Namecheap Credentials:**
```
API_USER=your_namecheap_user
API_KEY=your_namecheap_api_key
USERNAME=your_namecheap_username
CLIENT_IP=your_public_ip_address
```
*You can contact sindhao@sheridancollege.ca for API information or use your own Namecheap Sandbox account.*

**Stripe Credentials:**
```
STRIPE_SECRET_KEY=your_stripe_secret_key
```

**JWT Secret Key:**
Generate a secret key using the following command:```sh
python -c "import secrets; print(secrets.token_hex(32))"
```
Add the generated key to your `.env` file:
```sh
SECRET_KEY=your_generated_secret_key
```

### **7) Run the Application**

To run the application, you need to start three separate processes in different terminals: the FastAPI server, the Celery worker, and the Celery beat scheduler.

**a) Start the FastAPI Server:**
```sh
python main.py
```
The API will be available at `http://localhost:8000`.

**b) Start the Celery Beat Scheduler:**
*This service schedules the periodic tasks.*
```sh
celery -A celery_worker.celery_app beat --loglevel=info
```

**c) Start the Celery Worker:**
*This service executes the tasks scheduled by beat.*
```sh
celery -A celery_worker.celery_app worker --loglevel=info --pool=solo
```
