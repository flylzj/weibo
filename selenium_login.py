# encoding=utf-8
# ----------------------------------------
# 语言：Python2.7
# 日期：2017-05-01
# 作者：九茶<http://blog.csdn.net/bone_ace>
# 功能：破解四宫格图形验证码，登录m.weibo.cn
# ----------------------------------------

import time
import random
from PIL import Image
from math import sqrt
from ims import ims
from requests.cookies import RequestsCookieJar
from selenium import webdriver
from selenium.webdriver.remote.command import Command
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait

PIXELS = []


def getExactly(im):
    """ 精确剪切"""
    imin = -1
    imax = -1
    jmin = -1
    jmax = -1
    row = im.size[0]
    col = im.size[1]
    for i in range(row):
        for j in range(col):
            if im.load()[i, j] != 255:
                imax = i
                break
        if imax == -1:
            imin = i

    for j in range(col):
        for i in range(row):
            if im.load()[i, j] != 255:
                jmax = j
                break
        if jmax == -1:
            jmin = j
    return (imin + 1, jmin + 1, imax + 1, jmax + 1)


def getType(browser):
    """ 识别图形路径 """
    ttype = ''
    time.sleep(3.5)
    # print(browser.get_screenshot_as_png().decode('utf-8'))
    browser.get_screenshot_as_file('./pic/screen.png')
    im0 = Image.open('./pic/screen.png')
    box = browser.find_element_by_id('patternCaptchaHolder')
    im = im0.crop((int(box.location['x']) + 10, int(box.location['y']) + 100, int(box.location['x']) + box.size['width'] - 10, int(box.location['y']) + box.size['height'] - 10)).convert('L')
    newBox = getExactly(im)
    im = im.crop(newBox)
    width = im.size[0]
    height = im.size[1]
    for png in list(ims.keys()):
        isGoingOn = True
        for i in range(width):
            for j in range(height):
                if ((im.load()[i, j] >= 245 and ims[png][i][j] < 245) or (im.load()[i, j] < 245 and ims[png][i][j] >= 245)) and abs(ims[png][i][j] - im.load()[i, j]) > 10: # 以245为临界值，大约245为空白，小于245为线条；两个像素之间的差大约10，是为了去除245边界上的误差
                    isGoingOn = False
                    break
            if isGoingOn is False:
                ttype = ''
                break
            else:
                ttype = png
        else:
            break
    px0_x = box.location['x'] + 40 + newBox[0]
    px1_y = box.location['y'] + 130 + newBox[1]
    PIXELS.append((px0_x, px1_y))
    PIXELS.append((px0_x + 100, px1_y))
    PIXELS.append((px0_x, px1_y + 100))
    PIXELS.append((px0_x + 100, px1_y + 100))
    return ttype


def move(browser, coordinate, coordinate0):
    """ 从坐标coordinate0，移动到坐标coordinate """
    time.sleep(0.05)
    length = sqrt((coordinate[0] - coordinate0[0]) ** 2 + (coordinate[1] - coordinate0[1]) ** 2)  # 两点直线距离
    if length < 4:  # 如果两点之间距离小于4px，直接划过去
        ActionChains(browser).move_by_offset(coordinate[0] - coordinate0[0], coordinate[1] - coordinate0[1]).perform()
        return
    else:  # 递归，不断向着终点滑动
        step = random.randint(3, 5)
        x = int(step * (coordinate[0] - coordinate0[0]) / length)  # 按比例
        y = int(step * (coordinate[1] - coordinate0[1]) / length)
        ActionChains(browser).move_by_offset(x, y).perform()
        move(browser, coordinate, (coordinate0[0] + x, coordinate0[1] + y))


def draw(browser, ttype):
    """ 滑动 """
    if len(ttype) == 4:
        px0 = PIXELS[int(ttype[0]) - 1]
        login = browser.find_element_by_id('loginAction')
        ActionChains(browser).move_to_element(login).move_by_offset(px0[0] - login.location['x'] - int(login.size['width'] / 2), px0[1] - login.location['y'] - int(login.size['height'] / 2)).perform()
        browser.execute(Command.MOUSE_DOWN, {})

        px1 = PIXELS[int(ttype[1]) - 1]
        move(browser, (px1[0], px1[1]), px0)

        px2 = PIXELS[int(ttype[2]) - 1]
        move(browser, (px2[0], px2[1]), px1)

        px3 = PIXELS[int(ttype[3]) - 1]
        move(browser, (px3[0], px3[1]), px2)
        browser.execute(Command.MOUSE_UP, {})
        return True
    else:
        print('Sorry! Failed! Maybe you need to update the code.')
        return False


# 用来创建requestsCookiejar类
def make_request_cookie(cookies):
    c = RequestsCookieJar()
    for cookie in cookies:
        c.set(cookie.get('name'), cookie.get('value'))
    return c


def selenium_login(username, password):
    opt = webdriver.ChromeOptions()
    opt.add_argument('-headless')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-gpu')
    opt.add_argument('--disable-dev-shm-usage')
    # opt.add_argument('--proxy-server=http://139.199.183.108:8989')
    browser = webdriver.Chrome(executable_path='./driver/chromedriver', chrome_options=opt)
    WebDriverWait(browser, timeout=10)

    browser.set_window_size(1050, 840)
    browser.get('https://passport.weibo.cn/signin/login?entry=mweibo&r=https://m.weibo.cn/')

    time.sleep(1)
    name = browser.find_element_by_id('loginName')
    psw = browser.find_element_by_id('loginPassword')
    login = browser.find_element_by_id('loginAction')
    name.send_keys(username)  # 测试账号
    psw.send_keys(password)
    login.click()

    ttype = getType(browser)  # 识别图形路径
    print('图形路径', ttype)
    result = draw(browser, ttype)  # 滑动破解
    if not result:
        return None
    time.sleep(3)
    print(browser.current_url)
    cookies = browser.get_cookies()
    print(cookies)
    browser.close()
    cookiejar = make_request_cookie(cookies)
    return cookiejar


if __name__ == '__main__':
    # options = Options()
    # proxy = {
    #     'host': '139.199.183.108',
    #     'port': '8989'
    # }

    # profile = webdriver.FirefoxProfile()
    # profile.set_preference('network.proxy.type', 1)
    # profile.set_preference('network.proxy.http', proxy['host'])
    # profile.set_preference('network.proxy.http_port', int(proxy['port']))
    # profile.set_preference('network.proxy.ssl', proxy['host'])
    # profile.set_preference('network.proxy.ssl_port', int(proxy['port']))
    # profile.set_preference('network.proxy.no_proxies_on', 'localhost, 127.0.0.1')
    # options.add_argument('-headless')  # 无头参数
    # browser = Firefox(executable_path='./geckodriver/geckodriver', firefox_options=options, firefox_profile=profile)
    opt = webdriver.ChromeOptions()
    opt.add_argument('-headless')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-gpu')
    opt.add_argument('--disable-dev-shm-usage')
    opt.add_argument('--proxy-server=http://139.199.183.108:8989')
    browser = webdriver.Chrome(executable_path='./driver/chromedriver', chrome_options=opt)
    wait = WebDriverWait(browser, timeout=10)

    browser.set_window_size(1050, 840)
    browser.get('https://passport.weibo.cn/signin/login?entry=mweibo&r=https://m.weibo.cn/')

    time.sleep(1)
    name = browser.find_element_by_id('loginName')
    psw = browser.find_element_by_id('loginPassword')
    login = browser.find_element_by_id('loginAction')
    name.send_keys('15282343727')  # 测试账号
    psw.send_keys('162162162')
    login.click()

    ttype = getType(browser)  # 识别图形路径

    print('Result: %s!' % ttype)
    draw(browser, ttype)  # 滑动破解
    while browser.current_url != 'https://m.weibo.cn/':
        time.sleep(0.1)
    cookies = browser.get_cookies()
    make_request_cookie(cookies)
    browser.close()
