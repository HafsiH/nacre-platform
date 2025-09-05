# NACRE Platform

A comprehensive carbon footprint analysis platform using NACRE classification codes and AI-powered insights.

## 🌟 Overview

The NACRE Platform is a full-stack application that helps organizations analyze their carbon footprint by:
- Classifying purchases using NACRE codes (1,576 codes included)
- Calculating CO2 emissions based on purchase data
- Providing AI-powered recommendations for carbon reduction
- Offering detailed analytics and reporting capabilities

## 🚀 Features

### Core Functionality
- **File Processing**: Upload and process CSV/XLSX files
- **NACRE Classification**: Automatic classification of purchases to NACRE codes
- **Carbon Analysis**: Calculate CO2 footprints with detailed emission factors
- **Data Export**: Export results in multiple formats
- **Real-time Processing**: Live progress tracking and updates

### AI-Powered Features
- **Sophie AI Assistant**: Natural language interaction for carbon analysis
- **Smart Classification**: AI-enhanced code suggestions
- **Advanced Analytics**: Detailed carbon reports with recommendations
- **Pattern Recognition**: Learning from classification patterns

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI with Python 3.8+
- **AI Integration**: OpenAI GPT-4o-mini for intelligent analysis
- **Database**: JSON-based storage with efficient indexing
- **Processing**: Async and parallel processing capabilities

### Frontend (React + Vite)
- **Framework**: React 18.3.1 with modern hooks
- **Build Tool**: Vite 5.4.1 for fast development
- **UI**: Responsive design with real-time updates
- **API Integration**: Seamless backend communication

## 📋 Prerequisites

- **Python 3.8+** (with virtual environment)
- **Node.js 16+** (with npm)
- **OpenAI API Key** (optional, for AI features)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd nacre-platform
```

### 2. Start All Services
```bash
start_all.bat
```

This will automatically:
- Start the backend server on http://127.0.0.1:8123
- Start the frontend on http://localhost:5173
- Open both in separate command windows

### 3. Access the Application
- **Main App**: http://localhost:5173
- **API Docs**: http://127.0.0.1:8123/docs
- **Health Check**: http://127.0.0.1:8123/health

## 🔧 Manual Setup

### Backend Setup
```bash
# Navigate to backend
cd backend

# Activate virtual environment (Windows)
..\venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Start server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8123 --reload
```

### Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the `backend/` directory:

```env
# OpenAI Configuration (optional)
OPENAI_API_KEY=your_openai_api_key_here

# Model Settings
OPENAI_MODEL=gpt-4o-mini
SOPHIE_MODEL=gpt-4o-mini
EMBEDDINGS_MODEL=text-embedding-3-large

# Application Settings
STORAGE_DIR=../storage
MAX_CANDIDATES=25
BATCH_SIZE=10
LOG_LEVEL=INFO
```

### Without OpenAI API Key
The platform works with limited AI features:
- ✅ File processing and NACRE classification
- ✅ Carbon footprint calculations
- ✅ Data export and basic analytics
- ❌ AI-powered analysis and recommendations

## 📊 Data

### NACRE Dictionary
The platform includes a comprehensive NACRE dictionary with:
- **1,576 classification codes**
- **Emission factors** (kg CO2/€)
- **Detailed descriptions** for each code
- **Sector-specific data**

### Supported File Formats
- **CSV**: Comma-separated values
- **XLSX**: Excel spreadsheets
- **Encoding**: Auto-detection (UTF-8, ISO-8859-1, etc.)

## 🔍 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Root endpoint |
| `GET /health` | System health check |
| `POST /files` | File upload |
| `POST /conversions` | Start classification |
| `GET /conversions/{id}` | Get conversion status |
| `POST /co2` | Carbon analysis |
| `POST /sophie` | AI assistant chat |

## 📁 Project Structure

```
nacre-platform/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # Application entry point
│   │   ├── config.py       # Configuration settings
│   │   ├── models.py       # Data models
│   │   ├── routes/         # API endpoints
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utility functions
│   ├── requirements.txt    # Python dependencies
│   └── start_server.bat   # Backend startup script
├── frontend/               # React frontend
│   ├── src/
│   │   ├── App.jsx        # Main application component
│   │   ├── main.jsx       # Entry point
│   │   └── styles.css     # Styling
│   ├── package.json       # Node dependencies
│   └── start_frontend.bat # Frontend startup script
├── storage/               # Data storage
│   ├── data/             # NACRE indices
│   ├── uploads/          # User files
│   └── logs/             # Application logs
├── venv/                 # Python virtual environment
└── start_all.bat        # Start both services
```

## 🧪 Testing

### Backend Testing
```bash
cd backend
python test_server.py
```

### Health Check
```bash
curl http://127.0.0.1:8123/health
```

## 🚀 Deployment

### Production Build
```bash
# Build frontend
cd frontend
npm run build

# Backend is production-ready as-is
# Configure environment variables for production
```

### Docker Support
Docker configurations can be added for containerized deployment.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

### Troubleshooting
- Check the [STARTUP_GUIDE.md](STARTUP_GUIDE.md) for detailed setup instructions
- Review logs in `storage/logs/nacre.log`
- Use the health endpoint for diagnostics

### Common Issues
1. **Port conflicts**: Change ports in configuration
2. **Python path issues**: Ensure virtual environment is activated
3. **Node.js errors**: Clear `node_modules` and reinstall
4. **API errors**: Verify backend is running first

## 🎯 Roadmap

- [ ] Docker containerization
- [ ] Advanced reporting dashboard
- [ ] Multi-language support
- [ ] Enhanced AI capabilities
- [ ] Mobile responsiveness improvements
- [ ] Batch processing optimization

---

**Built with ❤️ for sustainable business practices**