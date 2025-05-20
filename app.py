from flask import Flask
from pathlib import Path
import datetime
import os
import json
import logging
from scanner import scan


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)

class State:
    running = False
    host = None
    disks = None

    def __init__(self) -> None:
        self.running = False
        self.host = os.getenv('HOST_NAME', 'unknown-host')
        self.disks = self._load_disks()

    def _load_disks(self):
        disks_json = os.getenv('DISKS_JSON', '{}')
        logger.info(f'disks_json: "{disks_json}"')
        try:
            return json.loads(disks_json)
        except json.JSONDecodeError:
            logger.info(f'error while parsing json :(')

STATE = State()

app = Flask(__name__)


def build_response(disk_name: str) -> dict[str, object]:
    logger.info(f'build_response')
    disk = STATE.disks.get(disk_name, {})
    return {
        'host': STATE.host,
        'disk': disk_name,
        'path': disk.get('path'),
        'date': disk.get('date'),
        'content': [c.__dict__ for c in disk.get('content', [])]
    }


def build_error(error_msg: str) -> dict[str, object]:
    logger.error(f'build_error - error_msg: "{error_msg}"')
    return {'error': error_msg}

@app.route('/status')
def status() -> dict[str, object]:
    logger.info(f'status')
    return {
        'host': STATE.host,
        'running': STATE.running,
        'disks': [disk_name for disk_name in STATE.disks.keys()]
    }


@app.route('/scan/<disk_name>')
def scan_disk(disk_name: str) -> dict[str, object]:
    logger.info(f'scan_disk')

    if STATE.running:
        return build_error('Scanning currently going on, try later')
    if disk_name not in STATE.disks.keys():
        return build_error('Invalid name')

    STATE.running = True
    now = datetime.datetime.now()
    logger.info(f'disk_name: {disk_name}')
    logger.info(f'now: {str(now)}')
    disk = STATE.disks.get(disk_name, {})
    path = Path(disk.get('path'))
    logger.info(f'path: {str(path)}')
    logger.info(f'scanning...')
    content = scan(path)
    logger.info(f'content length: {len(content)}')
    disk['content'] = content
    disk['date'] = now
    STATE.running = False

    return build_response(disk_name)


@app.route('/disk/<disk_name>')
def get_disk(disk_name: str) -> dict[str, object]:
    logger.info(f'disk {disk_name}')
    disk = STATE.disks.get(disk_name, {})
    if not disk.get('content', []) and not STATE.running:
        scan_disk(disk_name)
    return build_response(disk_name)


@app.route('/scan-all')
async def scan_all() -> dict[str, object]:
    logger.info(f'scanning all disks')
    if STATE.running:
        return {'error': 'Scanning currently going on, try later'}
    else:
        for disk_name in STATE.disks.keys():
            scan_disk(disk_name)
        return {'status': 'OK'}

if __name__ == '__main__':
    logger.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=5000)
