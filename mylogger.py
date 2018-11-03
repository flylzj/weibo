# coding: utf-8
import logging
import os


class MyFilter(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, log_record):
        return log_record.levelno <= self.__level


class MyLogger(object):
    def __init__(self, name):
        self.check_log_path()
        path = "log/{}.log".format(name)
        warn_path = "log/{}-warn.log".format(name)
        error_path = "log/{}-error.log".format(name)
        self.logger = logging.getLogger(name)
        # logging.basicConfig(level=logging.INFO)
        fmt_str = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        sh = logging.StreamHandler()
        sh.setFormatter(fmt_str)
        sh.setLevel(logging.INFO)
        # info log
        th = logging.FileHandler(filename=path, mode="a", encoding="utf-8", delay=True)
        th.setFormatter(fmt_str)
        th.setLevel(logging.INFO)
        th.addFilter(MyFilter(logging.INFO))
        # warning log
        warn_th = logging.FileHandler(filename=warn_path, mode="a", encoding="utf-8", delay=True)
        warn_th.setFormatter(fmt_str)
        warn_th.setLevel(logging.WARNING)
        warn_th.addFilter(MyFilter(logging.WARN))
        # error log
        error_th = logging.FileHandler(filename=error_path, mode="a", encoding="utf-8", delay=True)
        error_th.setFormatter(fmt_str)
        error_th.setLevel(logging.ERROR)
        error_th.addFilter(MyFilter(logging.ERROR))
        self.logger.addHandler(th)
        self.logger.addHandler(error_th)
        self.logger.addHandler(warn_th)
        # self.logger.addHandler(sh)
        self.logger.setLevel(logging.INFO)

    def get_logger(self):
        return self.logger

    def check_log_path(self):
        if not os.path.exists('log'):
            os.mkdir('log')