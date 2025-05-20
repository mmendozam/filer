from flask import Flask
from pathlib import Path
import datetime
import os
import json
import logging
from scanner import scan


# To run:
#
# Option 1:
# python app.py
#
# Option 2:
# set PYTHONPATH=E:\local\GitHub\mmendozam\mmendoza13\python\file-sync
# flask --app controller run

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)

class State:
    running = False
    host = None
    disks = None

    def __init__(self) -> None:
        logger.info('init State')
        self.running = False
        logger.info('host')
        self.host = os.getenv('HOST_NAME', 'unknown-host')
        logger.info('disks')
        self.disks = self._load_disks()

    def _load_disks(self):
        disks_json = os.getenv('DISKS_JSON', '{}')
        logger.info(f'disks_json: "{disks_json}"')
        try:
            return json.loads(disks_json)
        except json.JSONDecodeError:
            return {}

logger.info('Starting state')
STATE = State()

app = Flask(__name__)


def build_response(disk_name: str) -> dict[str, object]:
    disk = STATE.disks.get(disk_name, {})
    return {
        'host': STATE.host,
        'disk': disk_name,
        'path': disk.get('path'),
        'date': disk.get('date'),
        'content': [c.__dict__ for c in disk.get('content', [])]
    }


@app.route('/status')
def status() -> dict[str, object]:
    return {
        'host': STATE.host,
        'running': STATE.running,
        'disks': [disk_name for disk_name in STATE.disks.keys()]
    }


@app.route('/scan/<disk_name>')
def scan_disk(disk_name: str) -> dict[str, object]:
    if disk_name not in STATE.disks.keys():
        return {'error': 'Invalid name'}

    disk = STATE.disks.get(disk_name, {})

    if STATE.running:
        return {'error': 'Scanning currently going on, try later'}
    else:
        STATE.running = True
        path = Path(disk.get('path'))
        disk['content'] = scan(path)
        disk['date'] = datetime.datetime.now()
        STATE.running = False

    return build_response(disk_name)


@app.route('/disk/<disk_name>')
def get_disk(disk_name: str) -> dict[str, object]:
    disk = STATE.disks.get(disk_name, {})
    if not disk.get('content', []) and not STATE.running:
        scan_disk(disk_name)
    return build_response(disk_name)


@app.route('/scan-all')
async def scan_all() -> dict[str, object]:
    if STATE.running:
        return {'error': 'Scanning currently going on, try later'}
    else:
        for disk_name in STATE.disks.keys():
            scan_disk(disk_name)
        return {'status': 'OK'}

if __name__ == '__main__':
    logger.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=5000)
