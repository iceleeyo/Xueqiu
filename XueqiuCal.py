# -*-coding=utf-8-*-
#抓取雪球的收藏文章
from _ast import Str
from _datetime import date
__author__ = 'liache'
import requests,http.cookiejar,re,json,time
import pandas as pd
import urllib.request
from urllib import parse
from toolkit import Toolkit
from lxml import etree
import http.client
from bs4 import BeautifulSoup
import easytrader
import math

def request(url, cookie=''):
    ret = parse.urlparse(url)    # Parse input URL
    if ret.scheme == 'http':
        conn = http.client.HTTPConnection(ret.netloc)
    elif ret.scheme == 'https':
        conn = http.client.HTTPSConnection(ret.netloc)
    url = ret.path
    if ret.query: url += '?' + ret.query
    if ret.fragment: url += '#' + ret.fragment
    if not url: url = '/'
    conn.request(method='GET', url=url , headers={'Cookie': cookie})
    return conn.getresponse()

def get_xueqiu_hold(cube_symbol,cube_weight):
    cubeholding = {}
    req = urllib.request.Request(cube_hold_url+cube_symbol,headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:33.0) Gecko/20100101 Firefox/33.0',
                'cookie':cookie
               })
    soup = urllib.request.urlopen(req).read().decode('utf-8')
    soup = BeautifulSoup(soup, 'lxml')
    script = soup.find('script', text=re.compile('SNB\.cubeInfo'))
    json_text = re.search(r'^\s*SNB\.cubeInfo\s*=\s*({.*?})\s*;\s*$',
                      script.string, flags=re.DOTALL | re.MULTILINE).group(1)
    data = json.loads(json_text)
    print(data["view_rebalancing"]["holdings"])
    for d in data["view_rebalancing"]["holdings"]:
        if d['stock_name']+d['stock_symbol'] in projects.keys():
            projects[d['stock_name']+d['stock_symbol']] += d['weight']*cube_weight        
        else:
            projects[d['stock_name']+d['stock_symbol']]= d['weight']*cube_weight
    for d in data["view_rebalancing"]["holdings"]:
        if d['stock_name']+d['stock_symbol'] in cubeholding.keys():
            cubeholding[d['stock_name']+d['stock_symbol']] += d['weight']*cube_weight        
        else:
            cubeholding[d['stock_name']+d['stock_symbol']]= d['weight']*cube_weight
    print("组合："+cube_symbol+"权重："+str(cube_weight))
    print(cubeholding)
    print("-------------------------------------------------------------")
    

def get_xueqiu_cube_list(category,count,orderby):
    url=cube_list_url+"?category="+category+"&count="+count+"&market=cn&profit="+orderby
    data = request(url,cookie)
    jsonObj = json.loads(data.read())
    print(jsonObj)
    for TopestCube in jsonObj["list"]:
        daily_gain = TopestCube["daily_gain"]
        monthly_gain = TopestCube["monthly_gain"]
        annualized_gain_rate = TopestCube["annualized_gain_rate"]
        total_gain = TopestCube["total_gain"]
        symbol = TopestCube["symbol"]
        get_xueqiu_hold(symbol, total_gain/100)
    print("-------------------------------------------------------------")
    print(projects)
    print("-------------------------------------------------------------")
    sorted_stock = sort_by_value(projects)
    print(sorted_stock)
    return sorted_stock

def sort_by_value(d):
    items=d.items()
    backitems=[[v[1],v[0]] for v in items]
    backitems.sort(reverse=True)
    return [ backitems[i][1] for i in range(0,len(backitems))]

def searchFromDb():
    db = TinyDB('data/db_Cube')
    table = db.table('Cube')
    for row in table:
        get_xueqiu_hold(row.get('symbol'),row.get('annualized_gain_rate')/(100))

def calculate():
    db = TinyDB('data/db_holding.json')
    for cube_symbol in db.tables():
        HoldingTable = db.table(cube_symbol)
        for row in HoldingTable:
            print(row)

def adjust_weight():
    user = easytrader.use('xq')
    user.prepare('xq.json')
    sorted_stock = get_xueqiu_cube_list("14","100","annualized_gain_rate")
    totol_weight = 0.0
    adjust_weight = {}
    for i in range(5):
        totol_weight +=projects[sorted_stock[i]]
    for i in range(5):
        weight = projects[sorted_stock[i]]/totol_weight*100
        adjust_weight[sorted_stock[i]]= weight
        user.adjust_weight(sorted_stock[i][6:],math.floor(weight))
        print('雪球调仓成功，买入：'+sorted_stock[i]+", 仓位："+str(math.floor(weight)))
    print(adjust_weight)    
 
def xueqiu_adjust_weight():
    user = easytrader.use('xq')
    user.prepare('xq.json')
    sorted_stock = get_xueqiu_cube_list("14","10","annualized_gain_rate")[:5]
    #查看现在持仓股是否在计划买入内，不在的话卖出     
    for holding_stock in user.get_position():
        if holding_stock['stock_name']+holding_stock['stock_code'] in sorted_stock:
            pass
        else:
            user.adjust_weight(holding_stock['stock_code'][6:],0)
            print("卖出:"+holding_stock['stock_name']+holding_stock['stock_code'])
    totol_weight = 0.0
    adjust_weight = {}
    for i in range(5):
        totol_weight +=projects[sorted_stock[i]]
    for i in range(5):
        weight = projects[sorted_stock[i]]/totol_weight*100
        adjust_weight[sorted_stock[i]]= weight
#         user.adjust_weight(sorted_stock[i][6:],math.floor(weight))
        print('雪球调仓成功，买入：'+sorted_stock[i]+", 仓位："+str(math.floor(weight)))
    print(adjust_weight)

def download():
    stock_se = pd.Series()
    from_se = pd.Series()
    to_se = pd.Series()
    from_w_se = pd.Series()
    to_w_se = pd.Series()
    cash_se = pd.Series()
    price_se = pd.Series()
    df = pd.DataFrame()
    for page in range(1,19):
        symbol = "ZH003851"
        url = "https://xueqiu.com/cubes/rebalancing/history.json?cube_symbol="+symbol+"&count=50&page="
        cookie = "xq_a_token=d4cae93eb5b67871c8ee5ef2bd80813fc65ba34a; xq_r_token=a6cddf77f7d8a04010ec94ca7a39618ff09f5921;"
        data = request(url+str(page),cookie)
        jsonObj = json.loads(data.read())
        for rebalance in jsonObj["list"]:
            if rebalance["status"] == "success":
                items = rebalance["rebalancing_histories"]
                cash = rebalance["cash_value"]
                for item in items:
                    timeStp = item["updated_at"]
                    ltime=time.localtime(timeStp/1000.0) 
                    timeStr=time.strftime("%Y-%m-%d %H:%M:%S", ltime)
                    prev_value = item["prev_net_value"]
                    stock = item["stock_symbol"]
                    value = item["net_value"]
                    weight = item["weight"]
                    prev_weight = item["prev_weight_adjusted"]
                    price = item["price"]
                    cash_se[timeStr] = cash
                    # rebalance_type = ""
                    if prev_value is None and value > 0:
                        # rebalance_type = "BUY"
                        from_se[timeStr] = 0
                        from_w_se[timeStr] = 0
                    else:
                        from_se[timeStr] = prev_value
                        from_w_se[timeStr] = prev_weight

                    to_w_se[timeStr] = weight   
                    to_se[timeStr] = value
                    stock_se[timeStr] = stock
                    price_se[timeStr] = price
            else:
                print (rebalance["status"])
    df["stock"] = stock_se
    df["from"] = from_se
    df["to"] = to_se
    df["from_w"] = from_w_se
    df["to_w"] = to_w_se
    df["cash"] = cash_se
    df["price"] = price_se
    df.to_csv("data.csv")
#     print (df.head(20))

# url='https://xueqiu.com/snowman/login'
# session = requests.session()
# 
# session.cookies = http.cookiejar.LWPCookieJar(filename="cookies")
# try:
#     session.cookies.load(ignore_discard=True)
# except:
#     print ("Cookie can't load")
# 
# agent = 'Mozilla/5.0 (Windows NT 5.1; rv:33.0) Gecko/20100101 Firefox/33.0'
# headers = {'Host': 'xueqiu.com',
#            'Referer': 'https://xueqiu.com/',
#            'Origin':'https://xueqiu.com',
#            'User-Agent': agent}
# account=Toolkit.getUserData('data.cfg')
# print (account['snowball_user'])
# print (account['snowball_password'])
# 
# data={'username':account['snowball_user'],'password':account['snowball_password']}
# s=session.post(url,data=data,headers=headers)
# print (s.status_code)
projects = {}
cookie = "xq_a_token=d4cae93eb5b67871c8ee5ef2bd80813fc65ba34a; xq_r_token=a6cddf77f7d8a04010ec94ca7a39618ff09f5921;"
# session.cookies.save()
cube_list_url="https://xueqiu.com/cubes/discover/rank/cube/list.json"
cube_hold_url="https://xueqiu.com/P/"
xueqiu_adjust_weight()

# searchFromDb()
# calculate()
# get_xueqiu_hold("https://xueqiu.com/P/ZH003851");
# download()
# fav_temp='https://xueqiu.com/favs?page=1'
# collection=session.get(fav_temp,headers=headers)
# fav_content= collection.text
# p=re.compile('"maxPage":(\d+)')
# maxPage=p.findall(fav_content)[0]
# print (maxPage)
# print (type(maxPage))
# maxPage=int(maxPage)
# print (type(maxPage))
# for i in range(1,maxPage+1):
#     fav='https://xueqiu.com/favs?page=%d' %i
#     collection=session.get(fav,headers=headers)
#     fav_content= collection.text
#     #print fav_content
#     p=re.compile('var favs = {(.*?)};',re.S|re.M)
#     result=p.findall(fav_content)[0].strip()
# 
#     new_result='{'+result+'}'
#     #print type(new_result)
#     #print new_result
#     data=json.loads(new_result)
#     use_data= data['list']
#     host='https://xueqiu.com'
#     for i in use_data:
#         url=host+ i['target']
#         print (url)
#         txt_content=session.get(url,headers=headers).text
#         #print txt_content.text
# 
#         tree=etree.HTML(txt_content)
#         title=tree.xpath('//title/text()')[0]
# 
#         filename = re.sub('[\/:*?"<>|]', '-', title)
#         print (filename)
# 
#         content=tree.xpath('//div[@class="detail"]')
#         Toolkit.save2filecn(filename,"Link: %s\n\n" %url)
#         for i in content:
#             Toolkit.save2filecn(filename, i.xpath('string(.)'))
#         #print content
#         #Toolkit.save2file(filename,)
#         time.sleep(10)
