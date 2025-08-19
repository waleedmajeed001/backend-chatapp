# Backend Structure

This backend follows a clean architecture pattern with separation of concerns.

## Folder Structure

```
backend/
├── database/
│   ├── __init__.py
│   └── connection.py          # Database connection and initialization
├── models/
│   ├── __init__.py
│   └── user.py               # Pydantic models for data validation
├── services/
│   ├── __init__.py
│   └── auth_service.py       # Business logic for authentication
├── controllers/
│   ├── __init__.py
│   └── auth_controller.py    # HTTP request handling
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py        # Authentication API endpoints
│   └── main_routes.py        # Basic API endpoints
├── app.py                    # Main FastAPI application
├── requirements.txt          # Python dependencies
├── start.bat                # Windows startup script
└── README.md                # This file
```

## Architecture Overview

### **Models** (`models/`)
- **`user.py`**: Contains Pydantic models for user data validation
- Defines the structure of request/response data

### **Services** (`services/`)
- **`auth_service.py`**: Contains business logic for authentication
- Handles password hashing, JWT token creation/validation
- Manages database operations for user management

### **Controllers** (`controllers/`)
- **`auth_controller.py`**: Handles HTTP request processing
- Acts as a bridge between routes and services
- Manages authentication dependencies

### **Routes** (`routes/`)
- **`auth_routes.py`**: Defines authentication API endpoints
- **`main_routes.py`**: Defines basic API endpoints
- Uses FastAPI routers for clean endpoint organization

### **Database** (`database/`)
- **`connection.py`**: Manages database connections
- Handles database initialization and connection pooling

### **Main App** (`app.py`)
- Creates and configures the FastAPI application
- Includes all routers and middleware
- Handles startup events

## Benefits of This Structure

1. **Separation of Concerns**: Each layer has a specific responsibility
2. **Maintainability**: Easy to modify individual components
3. **Testability**: Services and controllers can be tested independently
4. **Scalability**: Easy to add new features and endpoints
5. **Code Reusability**: Services can be reused across different controllers

## Running the Application

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Set up environment**: Create `.env` file with database credentials
3. **Start the server**: `python app.py` or use `start.bat`

## Adding New Features

To add new functionality:

1. **Create models** in `models/` folder
2. **Add business logic** in `services/` folder
3. **Create controllers** in `controllers/` folder
4. **Define routes** in `routes/` folder
5. **Include new routers** in `app.py`

This structure makes it easy to maintain clean, organized code as your application grows.


