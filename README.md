This project have been developed as part of Software Engineering Course(CS3201) at Mahindra University, Hyderabad. 

We would like to thank our professors Dr. Vijay Rao and Dr. Avinash, our project guide Mrs. Swapna mam, and TA's of the course for constant guidance. 

# Bandwidth Monitoring System
A lightweight, real-time bandwidth monitoring and alert system built using Python (Flask) and SQLite, with an interactive dashboard and RESTful APIs. It tracks usage by device, application, and interface—ideal for small networks, labs, or home environments.

# Key Features

- **Real-time Monitoring**: Track bandwidth usage with 5-second precision
- **Device Tracking**: Identify top bandwidth consumers by IP/MAC address
- **Application Detection**: Classify traffic by application (Zoom, Netflix, etc.)
- **Alert System**: Threshold-based notifications for abnormal usage
- **Historical Analysis**: View 1-hour, 24-hour, and 7-day trends
- **Lightweight**: SQLite backend with automatic data purging (30-day retention)

# Tech Stack

| Component          | Technology Used |
|--------------------|-----------------|
| Backend Framework  | Flask           |
| Data Collection    | psutil          |
| Visualization      | Chart.js        |
| Database           | SQLite          |
| Monitoring         | Threading       |
| Reporting          | Matplotlib      |

# Install dependencies
```bash pip install -r requirements.txt```

# Initialize database
```bash python models.py```

# Development mode (Running the Application)
```bash python app.py```

# Project Structure
```bash
bandwidth-monitor/
├── app.py                # Main application
├── models.py             # Database schema
├── requirements.txt      # Dependencies
├── templates/            # HTML templates
│   └── dashboard.html    # Main dashboard
└── bandwidth.db          # Database file (auto-generated)
```

# Team 21 
 - **V. Nithin Reddy** – SE22UCSE278  
- **M. Panvi Tej** – SE22UCSE194  
- **N. Kushwanth Reddy** – SE22UCSE177  
- **C. Aryan** – SE22UCSE035  
- **E. Anvith Tej** – SE22UCSE089  
- **B. Jathin Reddy** – SE22UCSE118  
- **A. Hemanth** – SE22UCSE109


