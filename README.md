# toutiao_images
小爬虫程序，利用正则，BeautifulSoop分析Ajax，爬取今日头条街拍美图



# Requiretments

Running Environment(运行环境)

-  Python 3.5+ 
-  Linux/Windows/MAC OS



# library(库)

*  pip isntall  BeautifulSoup
*  pip install  pymongo (python操作MongoDB数据库包)



# Problem analysis

*  通过Chrome自带调试工具（F12），刷新页面，分析首页请求时使用的是 `Ajax请求方式`，在Headers确定出真实请求地址`Request URL`
*  第一个函数--索引页函数 `get_index`， 确定Ajax请求的参数(Query String Parameters)。使用urlencode的方式将Ajax请求的参数以变量的形式传递给函数，并生成真实的请求地址 `url`; requests.get方法获得索引页详情。
*  定义解析详情页函数`parse_page_index(html)`,解析详情页，获得每个详情页titil对应的 html_url; ;html参数为索引页函数返回的值，分析页面详情，通过json格式返回的数据，确定每个title对应的url, 使用**yeild** 生成器，使函数作为一个生成器，达到循环调用url
*  定义每个title下对应页面的详情函数`get_page_detail`,url参数为`parse_page_index`返回的值（为一个生成器），通过requests.get()请求，获得详情页面；
*  函数 `save_to_mongo`和`download_image`用来将解析的每个titiel所有原始图片url请求储存到本地
*  定义解析每个title详情页面的函数`parse_page_detail`,传递两个参数`html, url` .参数分别为get_page_detail返回的返回的数据，和parse_page_index(html)函数返回的数据url. 
   1. 通过BeautifulSoup,获得title 内容
   2. 正则匹配，获得每个title所有原始图片的详情image_url_list (做好字符串的处理，json化字符串)
   3. 返回将相关信息，以字典的格式存储，用来后续插入数据库中
   4. 调用函数download_image，下载图片到本地
*  定义函数`save_to_mongo`将parse_page_detail函数返回的数据插入到MongoDB中
*  主函数main(offset)，传递参数offset用来定义抓取页面的范围
   1. 使用multiprocessing.Pool()进程池，执行多进程。



# update

>  后期可进行模块化，或者类的方式进行，同一个程序下包含多个函数，显得冗长，如requests.get方式，代码重复使用了三次，函数之间的顺序最好从上到下的设计！