# Athena Digital Executive Assistant

A intelligent Telegram bot that automates contact management and meeting scheduling through conversational AI. Athena integrates with Google Calendar, stores data in Supabase, and provides a web-based management dashboard.

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🚀 Features

- **Intelligent Conversation**: Natural language processing with OpenAI GPT-4
- **Contact Management**: Automatic collection and storage of contact information
- **Meeting Scheduling**: Smart calendar integration with conflict prevention
- **Context Awareness**: Remembers previous conversations and recognizes returning contacts
- **Manager Dashboard**: Web interface for preferences and oversight
- **Multi-Platform Support**: Telegram bot with web management interface

## 🛠 Technology Stack

- **Backend**: Python 3.11, FastAPI, LangChain, OpenAI
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **Database**: Supabase (PostgreSQL)
- **Integrations**: Telegram Bot API, Google Calendar API
- **Testing**: Pytest, Jest, Coverage reporting
- **Deployment**: Docker, Render

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Supabase account
- Telegram Bot Token (from @BotFather)
- OpenAI API Key
- Google Cloud Console project with Calendar API enabled

## 🏗 Project Structure

```
athena-v2/
├── src/                    # Python backend source code
│   ├── agent/             # AI agent with LangChain
│   ├── api/               # FastAPI endpoints
│   ├── auth/              # Authentication management
│   ├── bot/               # Telegram bot implementation
│   ├── calendar/          # Google Calendar integration
│   ├── config/            # Configuration and settings
│   ├── database/          # Supabase client and operations
│   └── utils/             # Utility functions
├── frontend/              # Next.js frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Next.js pages and API routes
│   │   └── utils/         # Frontend utilities
│   └── public/            # Static assets
├── tests/                 # Test suites
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docker-compose.yml     # Development environment
├── pytest.ini           # Test configuration
└── README.md             # This file
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd athena-v2

# Copy environment variables
cp .env.example .env
# Edit .env with your actual API keys and credentials
```

### 2. Environment Variables

Configure your `.env` file with the following variables:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# OpenAI
OPENAI_API_KEY=sk-your_openai_api_key

# Google Calendar
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Application
ENVIRONMENT=development
PORT=8000
FRONTEND_PORT=3000
```

### 3. Database Setup

Create the following tables in your Supabase database:

```sql
-- Contacts table
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT,
    telegram_id TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(id),
    sender TEXT NOT NULL,
    channel TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'received',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User details table
CREATE TABLE user_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    working_hours_start TIME,
    working_hours_end TIME,
    meeting_duration INTEGER DEFAULT 60,
    buffer_time INTEGER DEFAULT 15,
    telegram_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. Development with Docker

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down
```

### 5. Local Development (Without Docker)

#### Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.api.main:app --reload --port 8000
```

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Generate coverage report
pytest --cov --cov-report=html
open htmlcov/index.html
```

### Frontend Tests
```bash
cd frontend

# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Generate coverage
npm run test:coverage
```

## 📡 API Documentation

### Backend Endpoints

#### Webhook Endpoints
- `POST /webhook/telegram` - Telegram bot webhook
- `POST /webhook/calendar` - Google Calendar notifications

#### Contact Management
- `GET /api/contacts` - List all contacts
- `POST /api/contacts` - Create new contact
- `GET /api/contacts/{id}` - Get contact by ID
- `PUT /api/contacts/{id}` - Update contact
- `DELETE /api/contacts/{id}` - Delete contact

#### Message Management
- `GET /api/messages` - List messages with pagination
- `POST /api/messages` - Create new message
- `GET /api/contacts/{contact_id}/messages` - Get messages for contact

#### Calendar Integration
- `GET /api/calendar/availability` - Check calendar availability
- `POST /api/calendar/meetings` - Schedule new meeting
- `GET /api/calendar/meetings` - List scheduled meetings

#### Authentication
- `POST /api/auth/login` - Login endpoint
- `POST /api/auth/logout` - Logout endpoint
- `GET /api/auth/me` - Get current user info

### Frontend Routes

- `/` - Landing page
- `/login` - Authentication page
- `/dashboard` - Main dashboard
- `/preferences` - Manager preferences
- `/contacts` - Contact management
- `/meetings` - Meeting overview

## 🎯 Usage Examples

### Telegram Bot Interaction

1. **Initial Contact**:
   ```
   User: Hello
   Athena: Hi! I'm Athena, your digital assistant. I help coordinate meetings and manage contacts. May I have your name and email to get started?
   ```

2. **Meeting Scheduling**:
   ```
   User: I'd like to schedule a meeting
   Athena: I'd be happy to help! What would you like to discuss and how long should the meeting be?
   User: Let's discuss the project proposal, about 1 hour
   Athena: Perfect! Here are some available time slots:
   • Tomorrow 2:00 PM - 3:00 PM
   • Thursday 10:00 AM - 11:00 AM  
   • Friday 3:00 PM - 4:00 PM
   Which works best for you?
   ```

3. **Returning User**:
   ```
   User: Hi again
   Athena: Hello John! Nice to hear from you again. How can I help you today?
   ```

## 🚀 Deployment

### Deploy to Render

1. **Backend Deployment**:
   ```bash
   # Create new Web Service on Render
   # Connect your GitHub repository
   # Set build command: pip install -r requirements.txt
   # Set start command: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
   ```

2. **Frontend Deployment**:
   ```bash
   # Create new Static Site on Render
   # Set build command: cd frontend && npm install && npm run build
   # Set publish directory: frontend/out
   ```

3. **Environment Variables**:
   Set all required environment variables in Render dashboard.

### Docker Production Deployment

```bash
# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy to production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 🔧 Configuration

### Manager Dashboard Preferences

Access the dashboard at `http://localhost:3000` to configure:

- **Working Hours**: Set your available meeting times
- **Buffer Time**: Configure time between meetings
- **Working Days**: Select which days you're available
- **Default Meeting Duration**: Set standard meeting length
- **Time Zone**: Configure your time zone

### Bot Behavior Configuration

Modify environment variables to adjust AI behavior:

```env
OPENAI_MODEL=gpt-4                    # AI model to use
OPENAI_TEMPERATURE=0.7                # Response creativity (0.0-1.0)
MAX_CONVERSATION_CONTEXT=5            # Number of previous messages to remember
DEFAULT_MEETING_DURATION_MINUTES=60   # Default meeting length
DEFAULT_BUFFER_TIME_MINUTES=15        # Default buffer time
```

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**:
   - Check Telegram bot token is correct
   - Verify webhook URL is accessible
   - Check backend logs for errors

2. **Calendar integration failing**:
   - Verify Google Calendar API is enabled
   - Check OAuth credentials are correct
   - Ensure proper redirect URI configuration

3. **Database connection issues**:
   - Verify Supabase URL and keys
   - Check database tables exist
   - Review RLS policies in Supabase

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### Health Checks

- Backend health: `GET http://localhost:8000/health`
- Frontend: `http://localhost:3000`
- Database: Check Supabase dashboard

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure tests pass: `pytest && cd frontend && npm test`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- Create an issue for bug reports or feature requests
- Check the troubleshooting section above
- Review the test examples in `/tests` directory

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Architecture Overview](docs/architecture.md)
- [Contributing Guidelines](docs/contributing.md)

---

**Made with ❤️ by the Athena Team** 