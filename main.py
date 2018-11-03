# coding: utf-8
from apscheduler.schedulers.blocking import BlockingScheduler
from weibo import OriginWeibo
import os


class WeiboSche(object):
    def __init__(self, account_file):
        self.pic_path = 'pic'
        self.ow = OriginWeibo(account_file)

    def send(self, mode):
        self.ow.get_cookies()
        if mode == 'one_word':
            content = self.ow.one_word()
            pic = os.path.join(self.pic_path, 'one_word.jpg')
            self.ow.get_pic(self.ow.get_pic_url(), pic)
        elif mode == 'weather0':
            content = self.ow.weather(0)
            pic = os.path.join(self.pic_path, 'weather.jpg')
            self.ow.get_pic(self.ow.get_pic_url(), pic)
        elif mode == 'weather1':
            content = self.ow.weather(1)
            pic = os.path.join(self.pic_path, 'weather.jpg')
            self.ow.get_pic(self.ow.get_pic_url(), pic)
        elif mode == 'news':
            content = self.ow.daily_news()
            pic = os.path.join(self.pic_path, 'news.jpg')
        elif mode == 'history_of_today':
            content = self.ow.history_of_today()
            pic = None
        else:
            return
        self.ow.send_original_weibo(content, pic)

    def forword(self):
        self.ow.get_cookies()
        weibo = self.ow.get_weibo_from_redis()
        content = self.ow.make_content(content=None, mode=None, forword=True)
        self.ow.forward_weibo(weibo, content)

    def get_forword(self):
        self.ow.get_cookies()
        self.ow.get_peoples_weibo()


def main():
    ws = WeiboSche('./account/a.json')
    sche = BlockingScheduler()
    sche.add_job(ws.get_forword, 'cron', hour='0-23/2', minute=1)  # 获取微博
    sche.add_job(ws.forword, 'cron', hour='0-23/1', minute=2)  # 转发微博
    sche.add_job(ws.send, 'cron', args=('one_word',), hour=8, minute=1)  # 一言
    sche.add_job(ws.send, 'cron', args=('weather0',), hour=6, minute=1)  # 早安
    sche.add_job(ws.send, 'cron', args=('weather1',), hour=23, minute=1)  # 晚安
    sche.add_job(ws.send, 'cron', args=('news',), hour=9, minute=1)  # 每日国际视野
    sche.add_job(ws.send, 'cron', args=('history_of_today',), hour=10, minute=1)  # 历史上的今天
    for job in sche.get_jobs():
        ws.ow.logger.info('add job {} {}'.format(job.name, job.args))
    sche.start()


if __name__ == '__main__':
    main()
