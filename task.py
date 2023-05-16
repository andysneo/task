from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from time import sleep
from os import system
from datetime import datetime

from message import Message
from logger import logger

import threading
import os
import time
import json

class TaskData:
    def __init__(self, task_name, task_price):    
        self.task_name = task_name 
        self.task_price = task_price 

class TaskBase:
    def __init__(self):   
        
        os.environ['TZ'] = 'Asia/Taipei'
        time.tzset()
        logger.info('Task starting...')
        self.loopDuration = 60
        self.loadWaitTime = 5
        self.ExpiredTime = 259200
        self.rebootTime = 1800
      
        self.file_path = 'save.json'
        self.msg = Message()
        self.url = os.getenv('default_url')
        self.browser = None
        self.options = Options()
        #self.options.add_argument("--headless")
        self.options.add_argument('window-size=1920x1080')
        self.options.add_argument("--start-maximized")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])
      
        self.taskLists = []

        self.keywordList = os.getenv('keywords').split(";")
        self.keyCount = len(self.keywordList)        
        self.subDuration = int(self.loopDuration / self.keyCount)
        if self.subDuration > self.loadWaitTime :
            self.subDuration -= self.loadWaitTime
        else:
            self.subDuration = 0

        self.InitBrowser()
        self.InitSaveFile()
        self.timer = 0
      
    def InitBrowser(self):
        try:
            if self.browser is not None:
                  self.browser.quit()
        except Exception as e:
            logger.exception("InitBrowser " + str(e))

        self.browser = webdriver.Chrome(options=self.options)

    def InitSaveFile(self):
        if os.path.exists(self.file_path):
            temps = []
            with open(self.file_path, 'r', encoding='utf-8') as f:
                temps = json.load(f)
        
            for tlist in temps:
                newTask = {}
                for k, value in tlist.items():
                    newTask[k] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
                self.taskLists.append(newTask)
            self.RemoveExpired()
        else:
            for i in range(self.keyCount):
                self.taskLists.append({})
            logger.info(f"檔案 '{self.file_path}' 不存在。")

    def RemoveExpired(self):      
        now = datetime.now()
        for tlist in self.taskLists:              
              to_remove = []
              for k, value in tlist.items():
                  if (now - value).total_seconds() >= self.ExpiredTime:
                      to_remove.append(k)
            
              for k in to_remove:                  
                  logger.info("remove expired: " + k)
                  del tlist[k]

    def NeedIgnore(self, taskData):
      return False

    def SubTask(self, task, taskList, key):
        try:
            task_name = task.find_element(By.CLASS_NAME, value='case_card_caseTit__2NM7e').text
            task_price = task.find_element(By.CLASS_NAME, value='case_card_casePrice__2tWVB').text

            if self.NeedIgnore(TaskData(task_name, task_price)):
              return
              
            task_date = task.find_element(By.CSS_SELECTOR, "li[class='case_card_cardRowLast__jQRDx public_flexBtCenter__3nYPR']").find_element(By.TAG_NAME, 'span').text
            if len(task_date.split('/')) > 1:
                return
    
            time_now = datetime.now()
            if task_name not in taskList:
                taskList[task_name] = time_now                
                logger.info(task_name)
                task_offer = task.find_element(By.CLASS_NAME, 'case_card_iconOffer__1nYP4').text
                task_caption = task.find_element(By.CLASS_NAME, 'case_card_cardCaption__2lsnZ').text
                task_url = task.find_element(By.XPATH, '..').get_attribute('href')
                task_id = task.find_element(By.XPATH, ".//*[@class='public_redBtn__3aFVS public_sizeM__2dTKy chat_start_btn ga_event']").get_attribute('data-id')
                task_url2 = self.url + task_id
    
                message = task_name + ' @ ' + key + "  " + task_date + ' 更新\n' + task_url + '\n' + task_price + '\n' + task_offer + '\n' + task_caption + '\n相關案件：' + task_url2
                #print(message)
                self.msg.send_message(message)
        except Exception as e:
            #print("SubTask",e)
            return

    def DoTask(self):
        #print("Thread Scrapy")
    
        try:
            threads = []
            for index in range(self.keyCount):
                #try:
                key = self.keywordList[index]
                taskList = self.taskLists[index]
                self.browser.get(self.url + key)
                try:
                    WebDriverWait(self.browser, self.loadWaitTime).until(EC.visibility_of_element_located((By.CLASS_NAME, 'case_card_caseTit__2NM7e')))                
                except Exception as e:                    
                    logger.exception("WebDriverWait " + str(e))
                allTask = self.browser.find_elements(By.CLASS_NAME, 'case_card_caseCard__7-5Z7')
                #print(len(allTask))
                threads.clear()
                #print(key)
                for task in allTask:     
                    sub_thread = threading.Thread(target = self.SubTask, args = (task, taskList, key))
                    threads.append(sub_thread)
                    sub_thread.start()
    
                for t in threads:
                    t.join()
                #print(taskList)
                self.taskLists[index] = taskList
                
                self.RemoveExpired()
                    
                temps=[]
                for tlist in self.taskLists:
                  newTask = {}
                  for k, value in tlist.items():
                    newTask[k] = str(value)              
                  temps.append(newTask)
              
                with open(self.file_path, 'w', encoding='utf-8') as f:
                  json.dump(temps, f, ensure_ascii=False)

                print(key + " " + len(allTask) + " saved " + str(datetime.now()))
              
                if index == self.keyCount - 1 :
                  break;
                  
                sleepTimes = self.subDuration #random.randint(50,60)
                for i in range(sleepTimes):
                    sleep(1)
      
                #except Exception as e:
                #    print("Browser: ", e)
                 #   browser.quit()
                 #   break
            #self.browser.quit()        
            #print("Thread Done")
        except Exception as e:
            logger.exception("Thread " + str(e))
            self.InitBrowser()   
          
    def DoTaskBackground(self):
        threading.Thread(target=self.DoTask, args=()).start()
      
    def Update(self, lastTime):      
        #timer = 0
        #while True:
            #sleep(1)
        self.timer = self.timer + 1
        if self.timer > self.rebootTime or (datetime.now() - lastTime).total_seconds() > 120:
            self.Reboot()
  
    def Reboot(self):
        logger.info('Reboot...')
        #system("busybox reboot")
        system("kill 1")


class TaskerApp(TaskBase):
    def __init__(self):    
        super().__init__()
        self.url = os.getenv('ca_url')


class TaskerGame(TaskBase):
    def NeedIgnore(self, taskData):
      if taskData.task_price.startswith('$') and int(taskData.task_price.replace("$", "").replace(",", ""))< 5001 or taskData.task_price.startswith("5千") :
            self.taskList.append(taskData.task_name)
            return True
      return super().NeedIgnore()