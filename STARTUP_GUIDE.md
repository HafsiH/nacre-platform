# NACRE Platform - Complete Startup Guide

## 🚀 Quick Start (Both Backend + Frontend)

### **Step 1: Start Backend Server**
```bash
cd backend
start_server.bat
```
- Backend runs on: **http://127.0.0.1:8123**
- API docs: **http://127.0.0.1:8123/docs**

### **Step 2: Start Frontend**
```bash
cd frontend  
start_frontend.bat
```
- Frontend runs on: **http://localhost:5173**
- Automatically proxies API calls to backend

## 📋 System Requirements

- **Python 3.8+** (with virtual environment activated)
- **Node.js 16+** (for frontend)
- **npm** (comes with Node.js)

## 🔧 Manual Startup

### Backend (FastAPI)
```bash
cd backend
# Activate virtual environment
..\venv\Scripts\activate.bat
# Start server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8123 --reload
```

### Frontend (React + Vite)
```bash
cd frontend
# Install dependencies (if needed)
npm install
# Start development server
npm run dev
```

## 🌐 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | Main web application |
| **Backend API** | http://127.0.0.1:8123 | REST API server |
| **API Docs** | http://127.0.0.1:8123/docs | Interactive API documentation |
| **Health Check** | http://127.0.0.1:8123/health | System status |

## ⚙️ Configuration

### Backend Configuration
- Create `.env` file in `backend/` directory (optional)
- Copy from `backend/env.template` for full AI features
- Requires OpenAI API key for AI-powered analysis

### Frontend Configuration
- Vite config in `frontend/vite.config.ts`
- API proxy automatically routes calls to backend
- No additional configuration needed

## 🎯 Features Available

### Core Functionality
- ✅ **File Upload** - CSV/XLSX file processing
- ✅ **NACRE Classification** - Automatic code assignment
- ✅ **Carbon Footprint Analysis** - CO2 calculation
- ✅ **Data Export** - Results download
- ✅ **Real-time Processing** - Live progress tracking

### AI Features (requires OpenAI API key)
- 🤖 **Sophie AI Assistant** - Natural language interaction
- 🧠 **Smart Classification** - AI-powered code suggestions
- 📊 **Advanced Analytics** - Detailed carbon reports
- 💡 **Recommendations** - Improvement suggestions

## 🔍 Troubleshooting

### Backend Issues
1. **Import errors**: Run `python backend/test_server.py`
2. **Port conflicts**: Change port in startup command
3. **Dependencies**: Check `backend/requirements.txt`

### Frontend Issues
1. **Node modules**: Run `npm install` in frontend directory
2. **Port conflicts**: Vite will suggest alternative port
3. **API errors**: Ensure backend is running first

### Connection Issues
- Backend must start **before** frontend
- Check firewall settings for localhost connections
- Verify ports 8123 (backend) and 5173 (frontend) are available

## 📁 Project Structure

```
nacre-platform/
├── backend/                 # FastAPI server
│   ├── app/                # Application code
│   ├── start_server.bat    # Backend startup script
│   └── requirements.txt    # Python dependencies
├── frontend/               # React application
│   ├── src/               # Source code
│   ├── start_frontend.bat # Frontend startup script
│   └── package.json       # Node dependencies
├── venv/                  # Python virtual environment
└── storage/               # Data and uploads
```

## 🎉 Success Indicators

### Backend Ready
- Console shows: "Application startup complete"
- Health check returns: `{"ok": true}`
- No error messages in logs

### Frontend Ready
- Console shows: "Local: http://localhost:5173/"
- Browser opens automatically (or navigate manually)
- Page loads without errors

### Full System Ready
- Frontend displays NACRE interface
- File upload works
- API calls succeed (check browser dev tools)

## 📞 Support

- Check logs in `storage/logs/nacre.log`
- Use health endpoint: http://127.0.0.1:8123/health
- Review browser console for frontend errors
- Test individual components using API docs
