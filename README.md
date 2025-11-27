# Smart CLM - Setup Guide

## Quick Start

### 1. Project Structure
Create the following directory structure:

```
smrt-clm/
│
├── main.py                 # Main FastAPI application
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── templates/             # HTML templates folder
│   ├── register.html      # Registration page (your HTML)
│   └── login.html         # Login page
│
├── static/                # Static files folder
│   ├── css/              # CSS files
│   ├── js/               # JavaScript files
│   └── assets/           # Images, fonts, etc.
│
└── data/                  # Data storage (optional)
    └── uploads/           # Uploaded documents
```

### 2. Installation Steps

```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create required directories
mkdir templates static static/css static/js static/assets data data/uploads
```

### 3. Add Your Registration HTML

Save your registration HTML file as `templates/register.html`. Then update the `/register` route in `main.py`:

```python
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})
```

### 4. Run the Application

```bash
# Run the FastAPI server
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access the Application

- **Application**: http://localhost:8000
- **Registration**: http://localhost:8000/register
- **Login**: http://localhost:8000/login
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## Available API Endpoints

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `POST /api/forgot-password` - Request password reset

### User Management
- `GET /api/users/me` - Get current user details

### Document Management
- `POST /api/upload-documents` - Upload company documents

### System
- `GET /health` - Health check endpoint

## Testing the Registration Flow

### 1. Using the Web Interface
1. Navigate to http://localhost:8000/register
2. Fill in the registration form
3. Submit the form
4. Check the console for the response

### 2. Using cURL
```bash
# Register a new user
curl -X POST "http://localhost:8000/api/register" \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "John",
    "lastName": "Doe",
    "email": "john@example.com",
    "phone": "+97412345678",
    "password": "SecurePass123!",
    "companyName": "Test Company",
    "jobTitle": "Manager",
    "companyType": "client",
    "terms": true
  }'

# Login
curl -X POST "http://localhost:8000/api/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

### 3. Using Python Requests
```python
import requests

# Register
response = requests.post(
    "http://localhost:8000/api/register",
    json={
        "firstName": "Jane",
        "lastName": "Smith",
        "email": "jane@example.com",
        "phone": "+97412345679",
        "password": "SecurePass456!",
        "companyName": "Another Company",
        "jobTitle": "Director",
        "companyType": "contractor",
        "terms": True
    }
)
print(response.json())
```

## Integrating Your HTML

### Step 1: Save the HTML file
Save your complete registration HTML as `templates/register.html`

### Step 2: Update the CSS/JS paths
In your HTML, update paths to use the static folder:
```html
<!-- From -->
<link rel="stylesheet" href="styles.css">

<!-- To -->
<link rel="stylesheet" href="/static/css/styles.css">
```

### Step 3: Update API endpoint in JavaScript
In your registration form JavaScript:
```javascript
// Update the fetch URL to match the FastAPI endpoint
const response = await fetch('/api/register', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
});
```

## Production Deployment

### 1. Environment Variables
Create a `.env` file:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost/smrtclm
REDIS_URL=redis://localhost:6379
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-password
```

### 2. Database Setup
For production, replace the mock database with a real one:
- PostgreSQL for relational data
- MongoDB for document storage
- Redis for session management

### 3. Security Enhancements
- Use bcrypt for password hashing
- Implement JWT tokens for authentication
- Add rate limiting
- Enable HTTPS
- Set up CORS properly

### 4. Deployment Options
- **Docker**: Create a Dockerfile and docker-compose.yml
- **Cloud**: Deploy to AWS, Google Cloud, or Azure
- **VPS**: Deploy to DigitalOcean, Linode, or Vultr
- **PaaS**: Deploy to Heroku, Railway, or Render

## Docker Setup (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db/smrtclm
    depends_on:
      - db
    volumes:
      - ./data:/app/data

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=smrtclm
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Run with Docker:
```bash
docker-compose up --build
```

## Troubleshooting

### Port Already in Use
```bash
# Kill the process using port 8000
# On Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# On Mac/Linux:
lsof -i :8000
kill -9 <PID>
```

### Module Not Found
```bash
# Make sure virtual environment is activated
# Reinstall dependencies
pip install -r requirements.txt
```

### CORS Issues
Update CORS settings in `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Support

For issues or questions:
1. Check the API documentation at http://localhost:8000/docs
2. Review the console logs for errors
3. Ensure all dependencies are installed
4. Verify the directory structure is correct

## License

© 2024 Smart CLM - Contract Lifecycle Management System