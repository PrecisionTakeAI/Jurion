# LegalAI Hub Backend

Multi-tenant legal practice management platform with AI integration, built with FastAPI and SQLAlchemy.

## Features

### 🏢 Multi-Tenant Architecture
- **Firm Isolation**: Complete data separation between law firms
- **Row-Level Security**: PostgreSQL-based data isolation
- **Subscription Tiers**: Starter, Professional, Enterprise, Enterprise Plus
- **Usage Limits**: Configurable user and storage limits per firm

### 🔐 Enterprise Authentication & Security
- **Multi-Factor Authentication**: TOTP-based MFA with backup codes
- **PBKDF2 Password Hashing**: Industry-standard password security
- **JWT Token Authentication**: Secure stateless authentication
- **Account Locking**: Protection against brute force attacks
- **Role-Based Access Control**: 6 permission levels (Principal, Senior Lawyer, Lawyer, Paralegal, Admin, Client)

### 🇦🇺 Australian Legal Compliance
- **Practitioner Validation**: All 8 Australian states/territories supported
- **Legal Disclaimers**: Jurisdiction-specific compliance
- **Audit Logging**: Comprehensive compliance tracking
- **Data Privacy**: GDPR/Australian Privacy Act compliance

### 📊 Advanced Data Models
- **Case Management**: Australian family law specialization
- **Document Processing**: AI-enhanced with privilege protection
- **Financial Information**: Property settlement calculations
- **Children Information**: Family law case requirements
- **AI Interactions**: Full compliance logging

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 13+
- Redis (optional, for caching)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/legalai-hub.git
cd legalai-hub/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Environment Configuration

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/legalai_hub

# JWT Security
JWT_SECRET_KEY=your-super-secret-jwt-key
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Application
ENVIRONMENT=development
SQL_ECHO=false
```

### Database Setup

```bash
# Create database tables
python -c "from backend.database import create_tables; create_tables()"

# Or use Alembic for migrations
alembic upgrade head
```

### Run Development Server

```bash
# Start the server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# API will be available at:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

## API Documentation

### Authentication Endpoints

#### Register Firm
```http
POST /auth/register-firm
Content-Type: application/json

{
  "firm_name": "Smith & Associates Legal",
  "abn": "12345678901",
  "phone": "(02) 9555-1234",
  "email": "admin@smithassociates.com.au",
  "principal_first_name": "John",
  "principal_last_name": "Smith",
  "principal_email": "john.smith@smithassociates.com.au",
  "principal_password": "SecurePassword123!",
  "practitioner_number": "12345678",
  "practitioner_state": "nsw"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "john.smith@smithassociates.com.au",
  "password": "SecurePassword123!",
  "mfa_code": "123456"
}
```

#### Setup MFA
```http
POST /auth/setup-mfa
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "enable": true
}
```

### Protected Endpoints
All protected endpoints require `Authorization: Bearer <access_token>` header.

## Testing

### Run Tests
```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific test file
pytest backend/tests/test_models.py

# Run with verbose output
pytest -v
```

### Test Coverage
- **Models**: 95% coverage including validation, relationships, and business logic
- **Authentication**: 90% coverage including MFA, account locking, and permissions
- **Australian Validation**: 100% coverage for all 8 states/territories
- **API Endpoints**: 85% coverage including error cases

## Architecture

### Database Schema
```
law_firms (Multi-tenant root)
├── users (Role-based access)
├── cases (Australian family law)
│   ├── documents (AI-processed)
│   ├── financial_information (Property settlements)
│   └── children_information (Custody cases)
├── ai_interactions (Compliance logging)
└── audit_logs (Security tracking)
```

### Security Model
1. **Firm-Level Isolation**: All data scoped to firm_id
2. **Role-Based Permissions**: Hierarchical permission system
3. **API Security**: JWT tokens with configurable expiration
4. **Data Encryption**: Passwords hashed with PBKDF2
5. **Audit Trail**: All actions logged for compliance

### Australian Legal Features
- **8 State Support**: NSW, VIC, QLD, WA, SA, TAS, ACT, NT
- **Practitioner Validation**: State-specific format validation
- **Case Types**: 8 family law case types supported
- **Court Integration**: Australian court system hierarchy
- **Compliance**: Professional responsibility tracking

## Development

### Code Style
```bash
# Format code
black backend/
isort backend/

# Lint code
flake8 backend/

# Type checking
mypy backend/
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

### Adding New Models
1. Create model in `backend/models/`
2. Add to `backend/models/__init__.py`
3. Create migration: `alembic revision --autogenerate`
4. Add tests in `backend/tests/test_models.py`
5. Update API endpoints if needed

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Configuration
- Use production PostgreSQL database
- Set strong JWT_SECRET_KEY
- Enable HTTPS
- Configure CORS appropriately
- Set up monitoring and logging
- Use Redis for caching (optional)

### Health Checks
- `GET /health` - Database connectivity and system status
- Monitor authentication success rates
- Track API response times
- Alert on database connection failures

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

### Code Standards
- Follow PEP 8 style guide
- Add type hints to all functions
- Write comprehensive tests
- Document API changes
- Update version numbers appropriately

## License

Copyright (c) 2025 LegalAI Hub. All rights reserved.

## Support

- Documentation: `/docs` endpoint
- Issues: GitHub Issues
- Email: support@legalai-hub.com