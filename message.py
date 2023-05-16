import requests
import os

class Message:
    def __init__(self, token = os.getenv('message')):
        self.headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/x-www-form-urlencoded"
        }
      
    def send_message(self, message):
        try:
            requests.post(os.getenv('notify'), headers=self.headers, params={"message": message})
        except Exception as e:
            print("send_message", e)