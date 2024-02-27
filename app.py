from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time
from logger import logger, log_output, settings
from update_stock import update_stock
from update_catalog import update_catalog
from update_price import update_price

script_running = False
thread = None

app = Flask(__name__)
socketio = SocketIO(app)

def background_thread():
    global message_to_emit
    """Emit server generated events to clients."""
    while True:
        time.sleep(1)
        new_logs = log_output.getvalue()
        if new_logs:
            socketio.emit('message', {'data': new_logs})
            log_output.truncate(0)
            log_output.seek(0)

def run_script_catalog():
    global script_running
    if not script_running:
        script_running = True
        try:
            time.sleep(1)
            logger.info("#### START ####\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})
            update_catalog()
        finally:
            script_running = False

def run_script_stock():
    global script_running
    if not script_running:
        script_running = True
        try:
            time.sleep(1)
            logger.info("#### START ####\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})
            update_stock()  # Add your logic to update stock here
        finally:
            script_running = False

def run_script_price():
    global script_running
    if not script_running:
        script_running = True
        try:
            time.sleep(1)
            logger.info("#### START ####\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})
            update_price()  # Add your logic to update stock here
        finally:
            script_running = False

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    logger.info("Connect", extra={'to_console': True})
    global thread
    if thread is None:
        thread = threading.Thread(target=background_thread)
        thread.daemon = True
        thread.start()

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("\nDisconnect", extra={'to_console': True})

@socketio.on('trigger_update_catalog')
def handle_update_stock():
    # Call the function that updates the stock
    run_script_catalog()

@socketio.on('trigger_update_stock')
def handle_update_stock():
    # Call the function that updates the stock
    run_script_stock()

@socketio.on('trigger_update_price')
def handle_update_price():
    # Call the function that updates the stock
    run_script_price()

@app.route('/update_stock')
def trigger_update_stock():
    # Call the function that updates the stock
    settings["CONSOLE"] = True
    run_script_stock()
    settings["CONSOLE"] = False
    return "Stock update completed!"
