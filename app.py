from flask import Flask
from pathlib import Path
import datetime
from scanner import scan


# To run:
#
# Option 1:
# python app.py
#
# Option 2:
# set PYTHONPATH=E:\local\GitHub\mmendozam\mmendoza13\python\file-sync
# flask --app controller run

class State:
    def __init__(self) -> None:
        self.running = False
        self.host = None
        self.disks = dict[str, object]


app = Flask(__name__)

STATE = State()

STATE.host = 'envy-m4'

STATE.disks = {
    'HD1': {
        'capacity': '175 GB',
        'usage': '30%',
        'path': 'C:/NNLK_HOME',
        'date': None,
        'content': []
    },
    'HD2': {
        'capacity': '750 GB',
        'usage': '5%',
        'path': 'E:/NNLK_HOME',
        'date': None,
        'content': []
    },
}


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
    # app.run(debug=True)
    app.run()
