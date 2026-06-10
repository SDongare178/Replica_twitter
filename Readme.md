# Replica Twitter

## Overview

Replica Twitter is a social media web application inspired by Twitter (X), allowing users to create profiles, post tweets, upload images, and interact with content in a modern web interface.

The application demonstrates full-stack web development using FastAPI, MongoDB, Firebase Authentication, and Azure Blob Storage.

---

## Features

* User authentication with Firebase
* User profile management
* Create and publish tweets
* Upload tweet images
* Upload profile pictures
* Search users and content
* Responsive user interface
* Cloud image storage using Azure Blob Storage
* MongoDB database integration

---

## Technology Stack

### Backend

* FastAPI
* Python
* Uvicorn

### Frontend

* HTML5
* CSS3
* JavaScript

### Database

* MongoDB Atlas

### Authentication

* Firebase Authentication

### Cloud Storage

* Azure Blob Storage

---

## Project Structure

```text
Replica_twitter/
│
├── main.py
├── requirements.txt
├── .gitignore
├── README.md
│
├── static/
│   ├── styles.css
│   └── firebase-login.js
│
├── templates/
│   ├── main.html
│   ├── profile.html
│   └── search.html
│
└── .env
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/SDongare178/Replica_twitter.git
cd Replica_twitter
```

### Create Virtual Environment

```bash
python -m venv .venv
```

### Activate Virtual Environment

Windows:

```bash
.venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root.

```env
MONGODB_URI=your_mongodb_connection_string
```

Replace the value with your MongoDB Atlas connection string.

---

## Running the Application

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Author

Sudhansh Dongare

GitHub: https://github.com/SDongare178
