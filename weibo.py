# coding: utf-8
import requests
import os
import pickle
from bs4 import BeautifulSoup
from datetime import date, timedelta
from random import randint
import redis
from mylogger import MyLogger
from selenium_login import selenium_login
import json


class Weibo(object):
    def __init__(self, account_file):
        self.check_paths(['log', 'pic', 'cookies', 'driver', 'account'])
        self.username, self.password = self.get_account(account_file)
        self.login_api = 'https://passport.weibo.cn/sso/login'
        self.user_info_api = 'https://m.weibo.cn/home/me?format=cards'
        self.user_weibo_api = "https://m.weibo.cn/api/container/getIndex?uid={}&luicode=20000174&type=uid&value={}&containerid=107603{}"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:56.0) Gecko/20100101 Firefox/56.0',
        }
        self.logger = MyLogger('weibo').get_logger()
        self.cookie_path = 'cookies'
        self.conn = redis.Redis(connection_pool=redis.ConnectionPool(host='redis', port=6379, decode_responses=True))
        self.cookies = self.get_cookies()

    def get_account(self, filename):
        with open(filename, 'r') as f:
            d = json.load(f)
            return d.get('username'), d.get('password')

    def check_paths(self, paths):
        for p in paths:
            if not os.path.exists(p):
                os.mkdir(p)

    def make_headers(self, items=None):
        headers = self.headers.copy()
        if items:
            headers.update(items)
        return headers

    def login(self):
        login_data = {
            'username': self.username,
            'password': self.password,
            'savestate': 1,
            'r': 'http%3A%2F%2Fm.weibo.cn%2F',
            'ec': 0,
            'pagerefer': '',
            'entry': 'mweibo',
            'wentry': '',
            'loginfrom': '',
            'client_id': '',
            'code': '',
            'qq': '',
            'mainpageflag': 1,
            'hff': '',
            'hfp': ''
        }
        items = {
            'Referer': 'https://passport.weibo.cn/signin/login?entry='
                       'mweibo&res=wel&wm=3349&r=https%3A%2F%2Fm.weibo.cn%2F'
        }
        try:
            r = requests.post(self.login_api, headers=self.make_headers(items), data=login_data)
            if r.json()['retcode'] == 20000000:
                self.logger.info('登录成功')
                r.cookies.pop('login')
                self.save_cookie(r.cookies)
                return r.cookies
            else:
                self.logger.error('登录失败, 可能需要验证码 {}'.format(r.text))
                self.logger.info('正在尝试用selenium登录')
                cookies = selenium_login(self.username, self.password)
                if not cookies:
                    self.logger.error('selenium登录失败')
                    exit(1)
                self.logger.info('selenium登录成功')
                self.save_cookie(cookies)
                return cookies
        except Exception as e:
            self.logger.error('登录失败 {}'.format(e), exc_info=True)

    def save_cookie(self, cookies):
        file = os.path.join(self.cookie_path, self.username + '.pkl')
        try:
            with open(file, 'wb') as f:
                self.logger.info('cookie保存成功')
                pickle.dump(cookies, f)
        except Exception as e:
            self.logger.error('保存cookie失败 {}'.format(e), exc_info=True)

    def get_cookies(self):
        file = os.path.join(self.cookie_path, self.username + '.pkl')
        try:
            with open(file, 'rb') as f:
                cookies = pickle.load(f)
            if self.verify_cookie(cookies):
                self.logger.info('cookie验证成功')
                return cookies
            else:
                self.logger.warning('cookie过期')
                self.logger.warning('正在重新登录')
                cookies = self.login()
            if not cookies:
                self.logger.error('登陆失败', exc_info=True)
        except Exception as e:
            self.logger.error('cookie不存在，重新登录 {}'.format(e), exc_info=True)
            cookies = self.login()
            if not cookies:
                exit(1)
            return cookies

    def verify_cookie(self, cookies):
        try:
            r = requests.get(self.user_info_api, headers=self.make_headers(), cookies=cookies)
            data = r.json()
            user_info = data[0]["card_group"][0]["user"]
            if user_info:
                return True
        except Exception as e:
            self.logger.error('验证cookie失败 {}'.format(e), exc_info=True)
            return False

    def get_user_basic_info(self):
        try:
            r = requests.get(self.user_info_api, headers=self.make_headers(), cookies=self.cookies)
            data = r.json()
            user_info = data[0]["card_group"][0]["user"]
            user = dict()
            user["user_id"] = user_info["id"]
            user["user_name"] = user_info["name"]
            user["weibo_count"] = user_info["mblogNum"]
            user["follow_count"] = user_info["attNum"]
            return user
        except Exception as e:
            self.logger.error('获取个人信息失败 {}'.format(e), exc_info=True)
            return

    def get_user_weibo(self, uid):  # 获取前十条微博
        self.logger.info('正在获取 {}的微博'.format(uid))
        url = self.user_weibo_api.format(uid, uid, uid)
        try:
            r = requests.get(url, headers=self.make_headers(), cookies=self.cookies)
            cards = r.json().get("data").get("cards")
            for card in cards:
            # weibo = {}
                try:
                    # weibo["weibo_content_id"] = card.get("mblog").get("id")
                    # weibo["weibo_content"] = card.get("mblog").get("text")
                    # weibo["weibo_user_id"] = card.get("mblog").get("user").get("id")
                    # weibo["weibo_username"] = card.get("mblog").get("user").get("screen_name")
                    # weibo["mid"] = card.get("mblog").get("mid")
                    wid = card.get("mblog").get("id")
                    mid = card.get("mblog").get("mid")
                    self.logger.info('{} - {}'.format(wid, mid))
                    yield wid, mid
                except AttributeError:
                    continue  # cards列表里面不一定是微博，用try来过滤
        except Exception as e:
            self.logger.error('获取用户微博失败 {}'.format(e))

    def get_st(self):  # st是转发微博post必须的参数
        url = "https://m.weibo.cn/api/config"
        # self.s.get(url, headers=self.make_cookie_header(), cookies=self.cookies, proxies=self.proxies, verify=False)
        try:
            s = requests.session()
            r = s.get(url, headers=self.make_headers(), cookies=self.cookies)
            data = r.json()
            st = data["data"]["st"]
            return st, s
        except Exception as e:
            self.logger.error('http error {}'.format(e), exc_info=True)

    def forward_weibo(self, weibo, content):
        st, s = self.get_st()
        url = "https://m.weibo.cn/api/statuses/repost"
        data = {"id": weibo["wid"], "content": content, "mid": weibo["mid"], "st": st}
        # 这里一定要加referer， 不加会变成不合法的请求
        items = {
            'Referer': 'https://m.weibo.cn/compose/repost?id={}'.format(weibo['wid'])
        }
        try:
            r = s.post(url, data=data, headers=self.make_headers(items), cookies=self.cookies)
            if r.json().get("ok") == 1:
                self.logger.info('转发微博{}成功'.format(weibo['wid']))
                return True
            else:
                self.logger.warning('转发微博{}失败 {}'.format(weibo['wid'], r.text))
                return None
        except Exception as e:
            self.logger.error('http error {}'.format(e), exc_info=True)
            return None

    # 发送原创微博
    def send_original_weibo(self, content, pic_path=None):
        st, s = self.get_st()
        data = {
            # "luicode": "10000011",
            # "lfid": "2304135827525376_ - _WEIBO_SECOND_PROFILE_MORE_WEIBO",
            # "featurecode": "20000320",
            "content": content,
            "st": st
        }
        if pic_path:
            pic_id = self.upload_pic(pic_path)
            if pic_id:
                data["picId"] = pic_id
        url = "https://m.weibo.cn/api/statuses/update"
        items = {
            'Referer': 'https://m.weibo.cn/compose/'
        }
        try:
            r = s.post(url, data=data, headers=self.make_headers(items), cookies=self.cookies)
            if r.json()["ok"] == 1:
                self.logger.info('原创微博发送成功')
            else:
                self.logger.warning('原创微博发送失败')
        except Exception as e:
            self.logger.error('http error {}'.format(e))
            return None

    def upload_pic(self, pic_path):
        url = "https://m.weibo.cn/api/statuses/uploadPic"
        st, s = self.get_st()
        pic_name = os.path.split(pic_path)[-1]
        # 这里如果pic_name 中有 '\' 会上传失败， 在windows里 \是路径，要去掉
        try:
            files = {"pic": (pic_name, open(pic_path, "rb").read(), "image/jpeg")}
        except Exception as e:
            self.logger.error('打开图片失败 {}'.format(e), exc_info=True)
            return None
        items = {
            'Referer': 'https://m.weibo.cn/compose/'
        }
        data = {"type": "json", "st": st}

        # print(r.json())
        try:
            r = s.post(url, data=data, files=files, headers=self.make_headers(items), cookies=self.cookies)
            pic_id = r.json()["pic_id"]
            self.logger.info('图片上传成功')
            return pic_id
        except Exception as e:
            self.logger.error('图片上传失败 {}'.format(e), exc_info=True)
            return None


class OriginWeibo(Weibo):
    def __init__(self, account_file):
        super(OriginWeibo, self).__init__(account_file)

    def get_pic_url(self):
        return "http://random-pic.oss-cn-hangzhou.aliyuncs.com/pc/{}.jpg".format(randint(1, 3000))

    def make_content(self, content, mode, forword=False):  # 这方法用来构造用于转发微博的content
        if not forword:
            content = "#食品青春#【{}】{} @南昌大学食品学院团委@南昌大学食品学院学生会".format(mode, content)
        else:
            content = "#食品青春#@南昌大学食品学院团委@南昌大学食品学院学生会"
        return content

    def get_pic(self, pic_url, pic_name):
        try:
            r = requests.get(pic_url, headers=self.make_headers())
            with open("%s" % pic_name, "wb") as f:
                f.write(r.content)
                self.logger.info('"图片保存成功"')
            return True
        except Exception as e:
            self.logger.error('图片下载失败 {}'.format(e), exc_info=True)

    def one_word(self):
        url = "https://v1.hitokoto.cn/"
        try:
            r = requests.get(url, headers=self.make_headers())
            word = r.json()
            content = word["hitokoto"] + " --- by " + word["from"]
            content = self.make_content(content, '一言')
            return content
        except Exception as e:
            self.logger.error('获取一言失败 {}'.format(e), exc_info=True)

    def weather(self, day=0):
        # day = 0 => 今天, day = 1 => 明天
        if day == 0:
            mode = '早安'
        else:
            mode = '晚安'
        url = 'http://www.weather.com.cn/weather/101240102.shtml'
        try:
            r = requests.get(url, headers=self.make_headers())
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.text, 'html.parser')
            weather = soup.find_all('ul', class_='t clearfix')[0].find_all('li')[day]
            wea = weather.find('p', class_='wea').text
            tem = weather.find('p', class_='tem').text
        except Exception as e:
            self.logger.error('获取天气失败 {}'.format(e), exc_info=True)
            return
        d = date.today() + timedelta(days=day)
        content = str(d) + wea + tem
        content = self.make_content(content, mode)
        return content

    def daily_news(self):
        url = "http://idaily-cdn.appcloudcdn.com/api/list/v3/android/zh-hans?ver=android&app_ver=36&page=1"
        headers = {"User-Agent": "okhttp/3.3.0"}
        try:
            r = requests.get(url, headers=headers)
            new = dict()
            new["title_wechat_tml"] = r.json()[0]["title_wechat_tml"]
            new["cover_landscape_hd"] = r.json()[0]["cover_landscape_hd"]
            new["link_share"] = r.json()[0]["link_share"]
            new["content"] = r.json()[0]["content"]

            self.get_pic(new["cover_landscape_hd"], os.path.join('pic', 'news.jpg'))
            content = new["content"] + " --- " + new["title_wechat_tml"] + " " + new["link_share"]
            content = self.make_content(content, '每日国际视野')
            return content
        except Exception as e:
            self.logger.error('获取新闻失败 {}'.format(e), exc_info=True)
            return None

    def history_of_today(self):
        url = "https://app.jike.ruguoapp.com/1.0/messages/showDetail?topicId=55557b24e4b058f898707ab5"
        try:
            r = requests.get(url, headers=self.make_headers())
            content = r.json()["messages"][0]["content"]
            content = self.make_content(content, '历史上的今天')
            return content
        except Exception as e:
            self.logger.error('获取历史上的今天失败 {}'.format(e), exc_info=True)
            return

    def get_peoples_weibo(self):
        uids = [
            '3937348351',  # 共青团中央
            '5209383952',  # 食品学院学生会
            '5228331496'   # 食品学院团委
        ]
        for uid in uids:
            for wid, mid in self.get_user_weibo(uid):
                k = wid + '-' + mid
                if not self.conn.hexists('weibo-hash', k):
                    self.conn.hset('weibo-hash', k, 1)
                    self.conn.zadd('weibo-zet', k, 1)

    def get_weibo_from_redis(self):
        w = self.conn.zrevrange('weibo-zet', 0, 0, withscores=True, score_cast_func=int)[0]
        self.conn.zadd('weibo-zet', w[0], 0)
        if w[1] != 1:
            return None
        weibo = {
            'wid': w[0].split('-')[0],
            'mid': w[0].split('-')[1]
        }
        return weibo

