from flask import Flask, jsonify
from pathlib import Path
import datetime
import os
import json
import logging
import threading
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


def build_disk_response(disk_name: str) -> dict[str, object]:
    logger.info(f'build_response')
    disk = STATE.disks.get(disk_name, {})
    return jsonify({
        'host': STATE.host,
        'disk': disk_name,
        'path': disk.get('path'),
        'date': disk.get('date'),
        'content': [c.__dict__ for c in disk.get('content', [])]
    })


def build_error(error_msg: str, e: Exception) -> dict[str, object]:
    logger.error(f'build_error - error_msg: "{error_msg}"')
    response = {'error': error_msg}
    if e:
        logger.error(str(e))
        response['exception'] = str(e)

    return jsonify(response)


def is_valid_disk_name(disk_name: str) -> bool:
    return disk_name in STATE.disks.keys()


def get_disk(disk_name: str) -> dict[str, object]:
    return STATE.disks.get(disk_name, {})


def scan_all_disks() -> None:
    logger.info(f'scan_all_disks')
    STATE.running = True
    for disk_name in STATE.disks.keys():
        disk = get_disk(disk_name)
        path = Path(disk.get('path'))
        content = []
        try:
            logger.info(f'scanning: {str(path)}')
            content = scan(path)
        except Exception as e:
            logger.error(f'Scan failed with path: {str(path)}')
            logger.error(str(e))
        finally:
            logger.info(f'content length: {len(content)}')
            disk['content'] = content
            disk['date'] = datetime.datetime.now()
    STATE.running = False
    logger.info(f'scan_all_disks done')


@app.route('/status')
def status() -> dict[str, object]:
    logger.info(f'status')
    status = {
        'host': STATE.host,
        'running': STATE.running,
        'disks': [disk_name for disk_name in STATE.disks.keys()]
        # TODO add disk brief state
    }
    logger.info(f'{status}')
    return jsonify(status)


@app.route('/scan/<disk_name>')
def scan_disk(disk_name: str) -> dict[str, object]:
    logger.info(f'scan_disk - disk_name: {disk_name}')

    if STATE.running:
        return build_error('Scanning currently going on, try later :S')
    if not is_valid_disk_name(disk_name):
        return build_error('Invalid disk :(')

    disk = get_disk(disk_name)
    path = Path(disk.get('path'))
    content = []
    response = None

    try:
        STATE.running = True
        logger.info(f'scanning: {str(path)}')
        content = scan(path)
    except Exception as e:
        response = build_error(f'Scan failed with path: {str(path)}', e)
    finally:
        logger.info(f'content length: {len(content)}')
        disk['content'] = content
        disk['date'] = datetime.datetime.now()
        response = build_disk_response(disk_name)
        STATE.running = False

    return response


@app.route('/disk/<disk_name>')
def get_disk_data(disk_name: str) -> dict[str, object]:
    logger.info(f'disk {disk_name}')
    disk = STATE.disks.get(disk_name, {})
    if not disk.get('content', []) and not STATE.running:
        scan_disk(disk_name)
    return build_disk_response(disk_name)


@app.route('/scan-all')
def scan_all() -> dict[str, object]:
    logger.info(f'scanning all disks')
    if STATE.running:
        return build_error(f'Scanning currently going on, try later')
    else:
        thread = threading.Thread(target=scan_all_disks)
        thread.start()
        return jsonify({'status': 'OK', 'started': datetime.datetime.now()})


if __name__ == '__main__':
    logger.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=5000)
