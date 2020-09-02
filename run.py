# coding=UTF-8
import threading
import queue
import re
import requests
import json
from Crypto.Cipher import AES
import time
import os
import pdfkit
import asyncio
import re
import gl
from upload import Upload_oss
from pdf import LaGou_article
class LaGou_video():
    def __init__(self,courseId):
        self.courseId = courseId
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
            'Cookie':gl.COOKIE,
            'Referer': 'https://kaiwu.lagou.com/course/courseInfo.htm?courseId='+courseId,
            'Origin': 'https://kaiwu.lagou.com',
            'Sec-fetch-dest': 'empty',
            'Sec-fetch-mode': 'cors',
            'Sec-fetch-site': 'same-site',
            'x-l-req-header': '{deviceType:1}'}
        self.url='https://gate.lagou.com/v1/neirong/kaiwu/getCourseLessons?courseId='+courseId
        self.queue = queue.Queue()  # 初始化一个队列
        self.error_queue = queue.Queue()
    
    def get_id(self):
        real_url_list=[]
        html = requests.get(url=self.url, headers=self.headers).text
        dit_message = json.loads(html)
        message_list = dit_message['content']['courseSectionList']
        for message in message_list:
            id1=message["courseLessons"]
            for t_id in id1:
                real_url="https://gate.lagou.com/v1/neirong/kaiwu/getCourseLessonDetail?lessonId={}".format(t_id["id"])
                real_url_list.append(real_url)
        return real_url_list
    
    def mkdir(self,path):
        path=path.strip()
        path=path.rstrip("\\")
        isExists=os.path.exists(path)
        if not isExists:
            os.makedirs(path) 
            return True
        else:
            return False
    
    def get_name(self):
        html = requests.get(url=self.url, headers=self.headers).text
        dit_message = json.loads(html)
        dirk_name = dit_message['content']['courseName']
        return dirk_name
    
    def parse_one(self,real_url_list):
        """
        :return:获得所有的课程url和课程名 返回一个队列（请求一次）
        """
        for real_url in real_url_list:
            # print(real_url)
            html = requests.get(url=real_url, headers=self.headers).text
            # print(html)
            dit_message = json.loads(html)
            message_list = dit_message['content']
            # print(message_list["videoMedia"])
            if message_list["videoMedia"] == None:
                continue
            else:
                name=message_list["theme"]
                m3u8=message_list["videoMedia"]["fileUrl"]
                # audio = message_list["audioMedia"]["fileUrl"]   mp3
                # print(m3u8)
                m3u8_dict = {m3u8:name}  # key为视频的url，val为视频的name
                # m3u8_audio = {audio:name}  # key为视频的url，val为视频的name
                #os.path.exists("{}.mp4".format(name)) or 
                if os.path.exists("{}.mp4".format(name)):
                    print("{}已经存在".format(name))
                    pass
                else:
                    # print(m3u8_dict)
                    self.queue.put(m3u8_dict)  # 将每个本地不存在的视频url（m3u8）和name加入到队列中
        return self.queue
    
    def get_key(self, **kwargs):
        # global key
        m3u8_dict = kwargs
        # print(m3u8_dict)
        # 获取课程的url
        for ks in m3u8_dict:  
            name = ''
            # print(k)
            true_url = ks.split('/')[0:-1]
            t_url = '/'.join(true_url)  # 拼接ts的url前面部分
            # 请求返回包含ts以及key数据
            html = requests.get(url=ks, headers=self.headers).text  
            # print(html)
            message = html.split('\n')  # 获取key以及ts的url
            key_parse = re.compile('URI="(.*?)"')
            key_list = key_parse.findall(html)
            # print("密匙链接"+key_list)
            # print(key_list[0])
            key = requests.get(url=key_list[0],headers=self.headers).content  
            # 一个m3u8文件中的所有ts对应的key是同一个 发一次请求获得m3u8文件的key
            # print(key)
            name1 = m3u8_dict[ks]  # 视频的名字
            # print("视频名："+name1)
            if "|" or '?' or '/' in name1:
                name = name1.replace("|" , "-")
                for i in message:
                    if '.ts' in i:
                        ts_url = t_url + '/' + i
                        # print("ts_url"+ts_url)
                        self.write(key, ts_url, name, m3u8_dict)
            else:
                name = name1
                for i in message:
                    # print(i)
                    if '.ts' in i:
                        ts_url = t_url + '/' + i
                        # print(ts_url)
                        self.write(key, ts_url, name, m3u8_dict)
    
    def write(self, key, ts_url, name01, m3u8_dict):
        dirkName = self.get_name()
        name01 = re.sub('\W+', '', name01).replace("_", '')
        dir=os.path.abspath(os.curdir)+'\\resources\\'+dirkName+'\\'
        res = self.mkdir(dir)
        print("\033[1;33;44m\t解析加密KEY："+str(key)+"\033[0m")
        cryptor = AES.new(key, AES.MODE_CBC, iv=key)
        with open('{}\\{}.mp4'.format(dir,name01), 'ab')as f:
            try:
                html = requests.get(url=ts_url, headers=self.headers).content
                f.write(cryptor.decrypt(html))
                # 写入成功上传OSS
                # run = Upload_oss()
                # local_file = dir+name01+'.mp4'
                # mp3_url = run.upload(name01+'.mp4',local_file,'mp4')
                # 视频转码可用于OSS存储
                # os.system("ffmpeg -i "name01+".mp4 -strict -2 -vf scale=-1:1080 test1.mp4")
                print("\033[0;32;43m\t视频写入成功："+str(name01)+"\033[0m")
            except Exception as e:
                print('{}爬取出错'.format(name01))
                while True:
                    if f.close():  # 检查问题文件是否关闭  闭关则删除重新爬，否则等待10s，直到该文件被删除并重新爬取为止
                        os.remove('{}.mp4'.format(name01))
                        print("\033[0;37;41m\删除成功："+str(name01)+"\033[0m")
                        thread = self.thread_method(self.get_key, m3u8_dict)
                        print("开启线程{}，{}重新爬取".format(thread.getName(), name01))
                        thread.start()
                        thread.join()
                        break
                    else:
                        time.sleep(10)
    def write_mp3(self, key, ts_url, name01, m3u8_dict):
        dirkName = self.get_name()
        name01 = re.sub('\W+', '', name01).replace("_", '')
        dir='G:\\video\\'+dirkName+'\\mp3\\'
        self.mkdir(dir)
        cryptor = AES.new(key, AES.MODE_CBC, iv=key)
        with open('{}\\{}.mp3'.format(dir,name01), 'ab')as f:
            try:
                html = requests.get(url=ts_url, headers=self.headers).content
                f.write(cryptor.decrypt(html))
                run = Upload_oss() # 上传阿里云OSS并写入数据库
                local_file = dir+name01+'.mp3'
                mp3_url = run.upload(name01+'.mp3',local_file,'mp3')
                print('{}，写入成功'.format(name01))
            except Exception as e:
                print('{}爬取出错'.format(name01))
                while True:
                    if f.close(): 
                        os.remove('{}.mp3'.format(name01))
                        print('{}删除成功'.format(name01))
                        thread = self.thread_method(self.get_key, m3u8_dict)
                        print("开启线程{}，{}重新爬取".format(thread.getName(), name01))
                        thread.start()
                        thread.join()
                        break
                    else:
                        time.sleep(10)
    
    def thread_method(self, method, value):  # 创建线程方法
        thread = threading.Thread(target=method, kwargs=value)
        return thread

    def main_task(self):
        global m3u8
        # 流数组
        thread_list = []
        # 拿到tsid
        real_url_list=self.get_id()
        m3u8_dict = self.parse_one(real_url_list)
        # print (self.demo())
        while not m3u8_dict.empty():
            for i in range(10):  # 创建线程并启动
                if not m3u8_dict.empty():
                    m3u8 = m3u8_dict.get()
                    # print(type(m3u8))
                    thread1 = self.thread_method(self.get_key, m3u8)
                    # thread2 = self.thread_method(run_art.main())
                    thread1.start()
                    # thread2.start()
                    print(thread1.getName() + '启动成功,{}'.format(m3u8))
                    time.sleep(1)
                    thread_list.append(thread1)
                    # thread_list.append(thread2)
                else:
                    break
            for k in thread_list:
                k.join()  # 回收线程
                thread_list.remove(k)


if __name__ == "__main__":
        print("请输入课程编号:")
        courseId=int(input())
        run = LaGou_video(str(courseId))
        pdf = LaGou_article(str(courseId))
        pdf.main()
        time1 = time.time()
        run.main_task()
        time2 = time.time()
        print(time2 - time1)