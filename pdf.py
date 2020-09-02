# coding=utf-8
import threading
import queue
import requests
import json
import time
import pdfkit
import ahttp
import os
from upload import Upload_oss
import asyncio
import oss2
import re
import gl


class LaGou_article():
    def __init__(self, courseId):
        self.url = 'https://gate.lagou.com/v1/neirong/kaiwu/getCourseLessons?courseId='+courseId
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
            'Cookie':gl.COOKIE,
            'Referer': 'https://kaiwu.lagou.com/course/courseInfo.htm?courseId='+courseId,
            'Origin': 'https://kaiwu.lagou.com',
            'Sec-fetch-dest': 'empty',
            'Sec-fetch-mode': 'cors',
            'Sec-fetch-site': 'same-site',
            'x-l-req-header': '{deviceType:1}'}
        # 发现课程文章html的请求url前面都是一样的最后的id不同而已
        self.textUrl = 'https://gate.lagou.com/v1/neirong/kaiwu/getCourseLessonDetail?lessonId='
        self.queue = queue.Queue()  # 初始化一个队列
        self.error_queue = queue.Queue()
        self.courseId = courseId

    def replace_all_blank(self, value):
        """
        去除value中的所有非字母内容，包括标点符号、空格、换行、下划线等
        :param value: 需要处理的内容
        :return: 返回处理后的内容
        """
        # \W 表示匹配非数字字母下划线
        result = re.sub('\W+', '', value).replace("_", '')
        return result

    def parse_one(self):
        """
        :return:获取文章html的url
        """
        content = requests.get(url=self.url, headers=self.headers).text
        code_cont = json.loads(content)
        message_list = code_cont['content']['courseSectionList']
        # print(message_list)
        for message in message_list:
            for i in message['courseLessons']:
                real_url = self.textUrl+str(i['id'])
                self.queue.put(real_url)  # 文章的请求url
        return self.queue

    def courseInfo(self):
        """
        :return:获取文章的详细内容
        """
        content = requests.get(url=self.url, headers=self.headers).text
        info = json.loads(content)
        return info['content']

    def get_html(self, real_url):
        """
        :return:返回一个Str 类型的html
        """
        html = requests.get(url=real_url, timeout=10,
                            headers=self.headers).text
        dit_message = json.loads(html)
        str_html = str(dit_message['content']['textContent'])
        article_name = dit_message['content']['theme']
        self.htmltopdf(str_html, article_name)

    def htmltopdf(self, str_html, article_name):
        info = self.courseInfo()
        dirkName = info['courseName']
        time.sleep(1)
        dir = os.path.abspath(os.curdir)+'\\resources\\'+dirkName+'\\'
        res = self.mkdir(dir)
        path_wk = r'C:\Users\male\Desktop\wkhtmltox-0.12.6-1.mxe-cross-win64 (1)\wkhtmltox\bin\wkhtmltopdf.exe'
        config = pdfkit.configuration(wkhtmltopdf=path_wk)
        options = {
            'page-size': 'Letter',
            'encoding': 'UTF-8',
            'custom-header': [('Accept-Encoding', 'gzip')]
        }
        article_name = self.replace_all_blank(article_name)
        local_name = dir+article_name+'.pdf'
        file_name = article_name+'.pdf'
        pdfkit.from_string(str_html, local_name,
                           configuration=config, options=options)
        print("\033[0;30;42m\t文章爬取成功，TItle："+str(article_name)+"\033[0m")
        # 写入以后上传阿里云OSS
        # run = Upload_oss()
        # pdfUrl = run.upload(file_name,local_name,'pdf')

    def mkdir(self, path):
        path = path.strip()
        path = path.rstrip("\\")
        isExists = os.path.exists(path)
        if not isExists:
            os.makedirs(path)
            return True
        else:
            return False

    def thread_method(self, method, value):  
        # 创建线程方法
        thread = threading.Thread(target=method, args=value)
        return thread

    def main(self):
        thread_list = []
        real_url= self.parse_one()
        while not  real_url.empty():
            for i in range(1):  # 创建线程并启动
                if not real_url.empty():
                    m3u8 = real_url.get()
                    # print(m3u8)
                    thread = self.thread_method(self.get_html, (m3u8,))
                    thread.start()
                    print(thread.getName() + '启动成功,{}'.format(m3u8))
                    thread_list.append(thread)
                else:
                    break
            while len(thread_list)!=0:
                for k in thread_list:
                    k.join()  # 回收线程
                    print('{}线程回收完毕'.format(k))
                    thread_list.remove(k)


if __name__ == "__main__":
    print("请输入课程编号:")
    courseId = int(input())
    run = LaGou_article(str(courseId))
    run.main()
