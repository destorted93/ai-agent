# Service Template

Boilerplate for creating new FastAPI microservices.

## What it includes

- FastAPI app structure
- Configuration management
- Health endpoint
- Port configuration
- Error handling

## Usage

1. Copy this folder to create a new service
2. Rename folder to your service name
3. Update `config.py` with service-specific settings
4. Add your endpoints in `app.py`
5. Create `requirements.txt` with dependencies

## Structure

```
service-name/
├── app.py              # Main FastAPI application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
└── README.md          # Service documentation
```

## Running

```bash
python your-service/app.py
```

Service will run on configured port with auto-reload.

## Configuration

Edit `config.py`:
```python
SERVICE_NAME = "your-service"
PORT = 6001
```

## Integration

Add service to launcher scripts to start with other services
