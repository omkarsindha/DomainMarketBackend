# Domain Markets Backend

This Python application uses the Namecheap API's XML responses to make a RESTful API.

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

### **4) Configure API Credentials**
This project uses environment variables to store sensitive API keys.
Create a .env file in the project directory and add your Namecheap API credentials:
```sh
API_USER=your_namecheap_user
API_KEY=your_namecheap_api_key
USERNAME=your_namecheap_username
CLIENT_IP=your_ip_address
```
Contact sindhao@sheridancollege.ca for API information or you can use your own.

### **5) Configure API Credentials**
This project uses locally installed Postgres for development.  
Edit the DATABASE_URL  in connection.py according to you test database, username and password.


### **6) Run the Application**
Fast API has no built-in server so run it using the uvicorn server. 
The following command looks for 'app' instance in 'main.py' file and runs it on server:
```sh
uvicorn main:app --reload
```


