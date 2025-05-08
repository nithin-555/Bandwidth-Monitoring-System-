This project was developed as part of the Software Engineering Course (CS3201) at Mahindra University. 
We would like to thank our professors Dr. Vijay Rao Duddu and Dr. Avinash, our project guide Swapna mam and the TA's for guiding throughout the project. 

**Bandwidth Monitoring System**

A lightweight, real-time bandwidth monitoring and alert system built using Python (Flask) and SQLite, with an interactive dashboard and RESTful APIs. It tracks usage by device, application, and interface—ideal for small networks, labs, or home environments.

**Features**
Real-time bandwidth monitoring (sent/received).
Per-device usage tracking (IP, MAC, top app).
Application usage breakdown (Zoom, Netflix, etc.).
Custom bandwidth threshold alerts.
Historical usage reports via dashboard.
 
**Project Strucutre**
bandwidth-monitor1/
├── app.py                # Main Flask app with logic and API routes
├── models.py             # Database schema and setup
├── bandwidth.db          # SQLite database (auto-created if missing)
├── requirements.txt      # Python dependencies
└── templates/
    └── index.html        # Frontend dashboard UI

Tech Stack

| Component          | Technology Used |
|--------------------|-----------------|
| Backend Framework  | Flask           |
| Data Collection    | psutil          |
| Visualization      | Chart.js        |
| Database           | SQLite          |
| Monitoring         | Threading       |
| Reporting          | Matplotlib      |

# Install dependencies
pip install -r requirements.txt

# Initialize database
python models.py

Running the Application
# Development mode
python app.py
