import os
import uvicorn
from fastapi import FastAPI

from config import get_settings

app = FastAPI()
settings = get_settings()


@app.get('/health')
def health():
    return {'status': 'ok', 'service': settings.SERVICE_NAME}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', settings.PORT))
    uvicorn.run(app, host='0.0.0.0', port=port, log_level='info')
