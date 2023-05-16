from task import TaskerApp

from time import sleep
from datetime import datetime
from flask import Flask
from flask_cors import CORS
from logger import logger

import threading


task = TaskerApp()
app = Flask(__name__)
CORS(app)
lastTime = datetime.now()

def run_app():
    try:
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        logger.exception("Thread " + str(e))

@app.route("/", methods=['GET'])
def home():
    return "alive"

@app.route("/run", methods=['GET'])
def run():
    global lastTime
    lastTime = datetime.now()

    task.DoTaskBackground()
  
    print("alive!")
    return str(lastTime)

if __name__ == '__main__':
    threading.Thread(target=run_app).start()
    
    while True:
        sleep(1)
        task.Update(lastTime);

logger.info("Done.")