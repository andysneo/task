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
        #os.environ['TZ'] = 'Asia/Taipei'
        #time.tzset()
        logger.info('Task starting...')
        self.loopDuration = 60
        self.loadWaitTime = 5
        self.ExpiredTime = 259200
        self.rebootTime = 3600
        self.liveTimeOut = 120
      
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
        self.threads = []

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
        self.running = False
        self.taskCount = 0
      
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
            count = self.keyCount - len(self.taskLists)
            if count > 0:
              for i in range(count):
                self.taskLists.append({})
            self.RemoveExpired()
        else:
            for i in range(self.keyCount):
                self.taskLists.append({})
            logger.info(f"檔案 '{self.file_path}' 不存在。")

    def SaveFile(self):
        temps=[]
        for tlist in self.taskLists:
            newTask = {}
            for k, value in tlist.items():
                newTask[k] = str(value)              
            temps.append(newTask)
              
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(temps, f, ensure_ascii=False)

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

    def URL(self, key):
        self.browser.get(self.url + key)

    def SubTask(self, task, taskList, key):
        try:
            task_name = task.find_element(By.CLASS_NAME, value='case_card_caseTit__2NM7e').text
            task_price = task.find_element(By.CLASS_NAME, value='case_card_casePrice__2tWVB').text

            if self.NeedIgnore(TaskData(task_name, task_price)):
              return
              
            task_date = task.find_element(By.CSS_SELECTOR, "li[class='case_card_cardRowLast__jQRDx public_flexBtCenter__3nYPR']").find_element(By.TAG_NAME, 'span').text
            if len(task_date.split('/')) > 1:
                return
    
            if task_name not in taskList:
                self.taskCount += 1 
                taskList[task_name] = datetime.now()                
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

    def Scrapy(self, taskList, key):
        try:
            WebDriverWait(self.browser, self.loadWaitTime).until(EC.visibility_of_element_located((By.CLASS_NAME, 'case_card_caseTit__2NM7e')))                
        except Exception as e:                    
            logger.error("WebDriverWait timeout")
        allTask = self.browser.find_elements(By.CLASS_NAME, 'case_card_caseCard__7-5Z7')
        #print(len(allTask))
        #print(key)
        for task in allTask:     
            sub_thread = threading.Thread(target = self.SubTask, args = (task, taskList, key))
            self.threads.append(sub_thread)
            sub_thread.start()
      
    def OnDone(self):
        return

    def Reset(self):        
        self.threads.clear()
        self.taskCount = 0
      
    def Wait(self):
        sleepTimes = self.subDuration
        for i in range(sleepTimes):                    
            print("wait " + str(sleepTimes - i) + "...              ", end='\r', flush=True)
            sleep(1)
        print("                                                            ", end='\r', flush=True)

    def DoTask(self):
        #print("Thread Scrapy")
        if self.running == True:
          print("still running...")
          return
        self.running = True
        try:
            for index in range(self.keyCount):
                #try:
                key = self.keywordList[index]
                taskList = self.taskLists[index]
                self.Reset()
                self.URL(key)
                self.Scrapy(taskList, key)
    
                for t in self.threads:
                    t.join()
                
                self.OnDone()
                #print(taskList)
                self.taskLists[index] = taskList
                self.RemoveExpired()
                self.SaveFile()    

                print(key + " " + str(self.taskCount) + " saved " + str(datetime.now()))

                self.Wait()
                #except Exception as e:
                #    print("Browser: ", e)
                 #   browser.quit()
                 #   break
            #self.browser.quit()        
            #print("Thread Done")
        except Exception as e:
            logger.exception("Thread " + str(e))
            self.InitBrowser()   
        self.running = False
          
    def DoTaskBackground(self):
        threading.Thread(target=self.DoTask, args=()).start()
      
    def Update(self, lastTime):      
        #timer = 0
        #while True:
            #sleep(1)
        self.timer = self.timer + 1
        if self.timer > self.rebootTime or (datetime.now() - lastTime).total_seconds() > self.liveTimeOut:
            self.Reboot()
  
    def Reboot(self):
        logger.info('Reboot...')
        print('Reboot...')
        sleep(2)
        #system("busybox reboot")
        system("kill 1")


#class TaskerApp(TaskBase):
#    def __init__(self):    
#        super().__init__()
#        self.url = os.getenv('ca_url')


class TaskerGame(TaskBase):
    def NeedIgnore(self, taskData):
      if taskData.task_price.startswith('$') and int(taskData.task_price.replace("$", "").replace(",", ""))< 5001 or taskData.task_price.startswith("5千") :
            self.taskList.append(taskData.task_name)
            return True
      return super().NeedIgnore(taskData)

class Tasker888(TaskBase):    
    def URL(self, key):
        self.browser.get(self.url)
      
    def Scrapy(self, taskList, key):
        try:
            WebDriverWait(self.browser, self.loadWaitTime).until(EC.visibility_of_element_located((By.CLASS_NAME, 'Hundred_Percent_Style')))                
        except Exception as e:                    
            logger.error("WebDriverWait timeout")
        table = self.browser.find_element(by=By.CLASS_NAME, value='Hundred_Percent_Style')
        allTask = table.find_elements(by=By.TAG_NAME, value='tr')

        count = len(allTask)

        if count > 0:
            taskIndex = 0
            last = count - 2
            for task in allTask:
                if taskIndex > 0 and taskIndex < last:
                    sub_thread = threading.Thread(target = self.SubTask, args = (task, taskList, key))
                    self.threads.append(sub_thread)
                    sub_thread.start()                    
                taskIndex += 1

        return count - 2

    def SubTask(self, task, taskList, key):
        try:            
            tdlist = task.find_elements(by=By.TAG_NAME, value='td')

            taskMain = tdlist[0]
            task_name = taskMain.text

            if key.lower() not in task_name.lower():
                return

            task_price = tdlist[1].text                      

            if self.NeedIgnore(TaskData(task_name, task_price)):
              return
            subBrowser = None
            if task_name not in taskList:                
                task_place = "地點" + tdlist[2].text                     
                task_caption = tdlist[3].text                    
                task_url = taskMain.find_element(by=By.TAG_NAME, value='a').get_attribute('href')  
                subBrowser = webdriver.Chrome(options=self.options)
                subBrowser.get(task_url)
                try:
                  WebDriverWait(subBrowser, self.loadWaitTime).until(EC.visibility_of_element_located((By.CLASS_NAME, 'Member_Table_Style')))
                except Exception as e:                    
                  logger.error("WebDriverWait timeout")
                  subBrowser.quit()
                  subBrowser = None
                  return
                
                self.taskCount += 1 
                taskList[task_name] = datetime.now()     
                table = subBrowser.find_element(by=By.CLASS_NAME, value='Member_Table_Style')
                allData = table.find_elements(by=By.TAG_NAME, value='tr')        
                task_date = allData[3].find_elements(by=By.TAG_NAME, value='td')[1].text
                task_caption2 = allData[2].find_elements(by=By.TAG_NAME, value='td')[1].text
                task_caption3= '[技能要求]\n' + allData[5].find_elements(by=By.TAG_NAME, value='td')[1].text

                logger.info(task_name)
                
                message = task_name + ' @ ' + key + "  " + task_date + ' 更新\n' + task_url + '\n' + task_price + '\n' + task_place + '\n' + task_caption + '\n' + task_caption2 + '\n\n' + task_caption3
                #print(message)
                self.msg.send_message(message)
            if subBrowser is not None:
                subBrowser.quit()
                subBrowser = None
        except Exception as e:
            print("SubTask",e)
            if subBrowser is not None:
                subBrowser.quit()
                subBrowser = None