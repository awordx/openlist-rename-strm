#!/bin/bash

cd /usr/local
python start_run.py &
sleep 2
python run_flask.py &
sleep 2
python utils/poster/poster.py &
# 等待所有后台任务完成
wait
#python start_run.py
#
#sleep 4
## 运行第二个 Python 脚本
#python run_flask.py
#
#sleep 2
## 运行第二个 Python 脚本
#python utils/poster/poster.py