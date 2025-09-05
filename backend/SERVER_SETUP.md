# NACRE Platform - Server Setup Guide

## Overview
The NACRE Platform backend is a FastAPI-based service that provides carbon footprint analysis and NACRE code classification using AI.

## Quick Start

### 1. Start the Server
Run the startup script from the backend directory:
```bash
start_server.bat
```

### 2. Test the Server
Once running, test the server at:
- Health check: http://127.0.0.1:8123/health
- API documentation: http://127.0.0.1:8123/docs
- Root endpoint: http://127.0.0.1:8123/

## Configuration

### Environment Variables
Create a `.env` file in the backend directory (copy from `env.template`):

```env
# Required for AI features
OPENAI_API_KEY=your_openai_api_key_here

# Optional - defaults are provided
OPENAI_MODEL=gpt-4o-mini
STORAGE_DIR=../storage
LOG_LEVEL=INFO
```

### Without OpenAI API Key
The server will start and function with limited capabilities:
- File upload and processing ✓
- NACRE dictionary loading ✓
- Basic carbon calculations ✓
- AI-powered analysis ✗ (requires API key)

## Features

### Core Services
- **File Processing**: Upload CSV/XLSX files
- **NACRE Classification**: Map purchases to NACRE codes
- **Carbon Analysis**: Calculate CO2 footprints
- **Sophie AI**: Orchestrator for AI services
- **Health Monitoring**: System status and diagnostics

### API Endpoints
- `/files` - File upload and management
- `/conversions` - NACRE code classification
- `/co2` - Carbon footprint analysis
- `/sophie` - AI assistant interactions
- `/health` - System health checks

## Data Requirements

### NACRE Dictionary
The system uses `nacre_dictionary_with_emissions.csv` which contains:
- `code_nacre`: NACRE classification codes
- `description`: Activity descriptions
- `emission`: Primary emission factors (kg CO2/€)
- `emission_factor`: Fallback emission factors

### Storage Structure
```
storage/
├── data/           # NACRE indices and embeddings
├── uploads/        # User uploaded files
├── db/            # Conversion results
└── logs/          # Application logs
```

## Troubleshooting

### Common Issues

1. **Server won't start**
   - Check Python installation: `python --version`
   - Verify virtual environment: `venv\Scripts\activate.bat`
   - Install dependencies: `pip install -r requirements.txt`

2. **Import errors**
   - Run test script: `python test_server.py`
   - Check file paths and permissions

3. **AI features not working**
   - Verify OpenAI API key in `.env` file
   - Check API key validity and credits
   - Review logs for specific errors

### Log Files
- Application logs: `../storage/logs/nacre.log`
- Console output shows startup messages and errors

## Development

### Testing
Run the comprehensive test:
```bash
python test_server.py
```

### Hot Reload
The server starts with `--reload` flag for development convenience.

### API Documentation
Interactive API docs available at `/docs` when server is running.

## Performance

### Optimization Features
- Batch processing for large datasets
- Embedding caching for faster lookups
- Async processing for concurrent requests
- Performance metrics and timing

### Scaling Considerations
- Adjust `BATCH_SIZE` for your hardware
- Monitor memory usage with large files
- Consider API rate limits for OpenAI calls

## Support

### Health Check
Use `/health` endpoint to verify:
- API connectivity
- Dictionary loading
- Storage accessibility
- AI service status

### Logs and Debugging
- Set `LOG_LEVEL=DEBUG` for verbose logging
- Check `../storage/logs/nacre.log` for detailed information
- Use `/health` endpoint for system diagnostics
