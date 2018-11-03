FROM ubuntu:16.04

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

RUN echo 'Asia/Shanghai' >/etc/timezone

RUN echo 'deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial main restricted universe multiverse' > /etc/apt/sources.list

RUN apt update && apt install -y google-chrome-stable && apt install -y python3.5 && apt install -y python3-pip

COPY ./req.txt /tmp

RUN pip install -r /tmp/req.txt

CMD ['python', 'main.py']

