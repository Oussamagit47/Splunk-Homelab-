from flask import Flask, request
import logging
from logging.handlers import RotatingFileHandler
import json
import os

app = Flask(__name__)

# ensure directory exists
log_path = "/var/log/app.log"
os.makedirs(os.path.dirname(log_path), exist_ok=True)

# configure rotating file handler
handler = RotatingFileHandler(log_path, maxBytes=1000000, backupCount=1)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)

# attach handler and set logger level
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
# optional: don't propagate to root/console to avoid duplicate output
app.logger.propagate = False

@app.route('/', methods=['GET','POST'])
def index():
    evt = {
        'event_type': 'http_request',
        'method': request.method,
        'path': request.path,
        'ua': request.headers.get('User-Agent'),
        'args': request.args.to_dict(),
        'form': request.form.to_dict(),
        'src_ip': request.remote_addr
    }
    app.logger.info(json.dumps(evt))
    return 'ok\n', 200

@app.route('/upload', methods=['POST'])
def upload():
    evt = {
        'event_type': 'file_upload',
        'path': request.path,
        'data': request.get_data(as_text=True),
        'ua': request.headers.get('User-Agent'),
        'src_ip': request.remote_addr
    }
    app.logger.info(json.dumps(evt))
    return 'uploaded\n', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
