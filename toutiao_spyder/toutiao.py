#coding:utf-8
#author by Failymao
'''
- 通过分析Ajax爬取今日头条 ‘街拍图片’
- 流程
    1. 利用requests 请求目标站点，得到索引网页HTML代码，返回结果。 AJAX请求
    2.抓取详情页，解析返回结果，得到详情页的链接，并进一步抓取详情页的信息
    3.下载图片并保存到数据（图片下载到本地，并把页面信息寄图片URL保存至MongoDB）
    4.开启循环及多线程，对多页内容遍历，开启多线程提高速度
'''
from bs4 import BeautifulSoup
from config import *                                                     #导入配置文件
from hashlib import md5
import json
from json.decoder import JSONDecodeError
from multiprocessing import  Pool                                        #引入多进程中的进程池
import os 
import pymongo
from requests.exceptions import RequestException
import requests
import re
from urllib.parse import urlencode


client = pymongo.MongoClient(MONGO_URL, connect=False)                   #实例化一个monogodbd的对象,开启多进程没执行一个多进程会实例化一个client对象
db = client[MONGO_DB]

def get_index(offset,keyword):  
    '''   
           定义索引页函数
         - data  :Ajax请求参数，从headers中获取！
    '''
    data = {
        'offset':offset,
        'format':'json',
        'keyword':keyword,
        'autoload':'true',
        'count':'20',
        'cur_tab':'3',
        'from':'gallery'
        } 
    url  = 'https://www.toutiao.com/search_content/?' + urlencode(data)    #Ajax获取真实请求地址 
    try:
        response = requests.get(url)                                       #get请求服务器
        if response.status_code == 200:                                    #如果返回的状态码为200，说明此请求地址成功！
            return response.text                                           #提取返回的文本信息
        return None                                                        #如果返回的状态码不为200，说明此请求不成功，不返回信息！
#             contents =  json.loads(response.text)
#             if 'data' in contents.keys():
#                 for item in  contents.get('data'):
#                     print (item.get('article_url'))
    except RequestException:                                                #如果发生索引请求异常
        print ('请求索引页出错')                                             #提示
        return None


def parse_page_index(html):
    '''定义解析页面函数，html参数为解析页面URL，yield生成器函数''' 
    try:
        data = json.loads(html)                                             #对返回的文本信息进行格式化成字典格式
        if data and 'data' in data.keys():                                  #如果返回的数据不为空，且字典键中包含'data'键
            for item in data.get('data'):                                   #获取data键对应的值--为一个列表
                yield item.get('article_url')                               #取出每个字典中键(article_url)对应的值，即每个图片主url
    except JSONDecodeError:
        pass
 

def get_page_detail(url):
    '''获得每张图片页面的详情页，参数url为主url,从parse_page_index函数中获得'''
    try:
        response = requests.get(url)                                        #get方式请求url
        if response.status_code == 200:                                     #判断返回状态码是否为200
            return response.text                                            #返回页面详情信息
        return None                                                         #如果返回的状态码非200，不返回任何信息
    except RequestException:
        #print ('请求索引页出错')
        return None


def parse_page_detail(html,url):
    '''  
         解析详情页函数，参数为html,url
         - 正则找出每个title包含的图片详情连接的url,生成列表
         - 返回一个字典格式的数据类型，用来插入到mongodb中
    '''
    soup = BeautifulSoup(html,'lxml')
    title = soup.select('title')[0].text 
    print (title)
    image_pattern = re.compile('gallery: JSON.parse.{1}"(.*?)".{1},\n',re.S) #配包含有具体图片的正则表达式
    #image_url  = re.compile('[A-Za-z-0-9]{20}')
    matche = re.search(image_pattern, html)                                  #使用re.search,查找目标字符串
  
    if matche:
        res = matche.group(1)                                                #取出匹配到的字符串
        a  = res.replace('\\','')                                            #对字符串进行处理，替换掉字符串中转义字符为 空
        data = json.loads(a)                                                 #对字符串进行json处理，变为python格式的字典类型
        if data and 'sub_images' in data.keys():                             #根据返回的字典数据，可以得知sub_images键对应的值为图片详情连接列表
            sub_images = data.get('sub_images')                              #获取详情图片连接的列表
            images_url_list = [item.get('url') for item in sub_images ]      #将每个图片详情连接生成一个列表
            for image_url in images_url_list:download_image(image_url)       #调用下载图片函数，将图片保存在本地
            
            return {
                'title':title,                                               #返回数据 图片title
                'url':url,                                                   #图片连接
                'images':images_url_list                                     #图片详情列表
                }


def save_to_mongo(result):
    '''定义操作数据库函数'''
    if db[MONGO_DB].insert(result):                                         #insertsql语句，插入返回的result，如果成功
        print ('插入MonogoDB数据成功')  
        return True                                                         #返回True
    return False                                                            #否则为False

           
def download_image(url):
    '''定义下载图片的函数'''
    print ("正在下载", url)
    try:
        response = requests.get(url)                                        #get方式请求url
        if response.status_code == 200:                                     #判断返回状态码是否为200
            save_image(response.content)                                    #response.content返回网页饿的是二进制文件，作为参数，调用保存图片的函数
        return None                                                         #如果返回的状态码非200，不返回任何信息
    except RequestException:
        print ('请求图片出错')
        return None

   
def save_image(content):
    ''' 
        定义保存的图片函数，路径，文件名
      - 定义下载保存图片的路径,md5()方法随机生成文件名，传入content内容为图片详情，
    '''
    file_path_name = '{0}/images/{1}.{2}'.format(os.getcwd(),\
                      md5(content).hexdigest(), 'jpg')                       #定义文件名，路径
    if not os.path.exists(file_path_name):                                   #如果文件名不存在路径中，则保存打开的文件内容
        with open(file_path_name, 'wb') as f :
            f.write(content)
            f.close()
            
def main(offset):
    '''主函数'''
    html = get_index(offset, KEYWORD)                                       #传递两个参数给ge_index函数，获取所得到的 页面信息  
    for url in parse_page_index(html):                                      #调用此函数(生成器)，获得url连接！
        html = get_page_detail(url)
        #print (url)
        if html:
            result = parse_page_detail(html,url)                            #调用详情页面解析函数
            if result:save_to_mongo(result)                                 #调用数据操作函数，将返回的数据插入到mongodb
   
  
if __name__ == "__main__":
    groups = [ x*20 for x in range(GROUP_START,GROUP_END+1)]                 #设置offset的取值列表
    pool = Pool()                                                            #开启一个进程池
    pool.map(main, groups)                                                   #map函数配合进程池，实现多进程处理--groups每一个元素作为参数传递个main函数
    


