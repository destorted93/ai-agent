import os
from flask import Flask, jsonify

from config import get_settings

app = Flask(__name__)
settings = get_settings()


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': settings.SERVICE_NAME})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', settings.PORT))
    app.run(host='0.0.0.0', port=port, debug=settings.DEBUG, threaded=True)
