from flask import Flask, jsonify, request, render_template, Response,session
import subprocess,threading, queue, time
import threading
import json
import os
import random
from alist_rename import read_config
from utils.log_utils import config_path
from utils.get_statistics import stats
from flask_session import Session
app = Flask(__name__)
log_queue = queue.Queue()
process = None #全局进程，用于中断程序执行
# 首页路由
# @app.route('/')
# def index():
#     return render_template('index_new.html')  # 确保这个文件在templates文件夹中
log_buffer = []  # 用于存储日志的缓冲区



###########################随机图片相关###########################
@app.route("/")
def index():
    bg_folder = "static/backgrounds"  # 存放背景图片的文件夹
    # 获取所有图片文件
    all_images = [f for f in os.listdir(bg_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    # 随机选择一张
    bg_image = random.choice(all_images) if all_images else None
    return render_template("index_new.html", bg_image=bg_image)
###########################登录密码相关###########################
app.secret_key = "super_secret_key"  # session 需要
app.config['SESSION_TYPE'] = 'filesystem'  # session 存文件
Session(app)
CONFIG_PASSWORD = read_config(config_path)['user_config']['web_config_password']
# 验证密码接口
@app.route('/check_config_password', methods=['POST'])
def check_config_password():
    data = request.get_json()
    password = data.get('password', '')
    if password == CONFIG_PASSWORD:
        session['config_authenticated'] = True  # 登录状态
        return jsonify({"valid": True})
    return jsonify({"valid": False})

# 判断是否已登录接口（可选）
@app.route('/config_authenticated')
def config_authenticated():
    return jsonify({"authenticated": session.get('config_authenticated', False)})






###########################右侧展示相关路由###########################

@app.route('/get_stats')
def get_stats():
    movie_count, series_count = stats()
    movie_count = sum(movie_count.values())      # 示例：电影数量
    series_count = sum(series_count.values())          # 示例：电视剧数量

    return jsonify({
        "movies": movie_count,
        "series_count": series_count
    })
@app.route('/get_filesize')
def get_filesize():
    # 返回 JSON 给前端
    if os.path.exists("data/temp.json") and os.path.getsize("data/temp.json") > 0:
        with open("data/temp.json", 'r', encoding='utf-8') as f:
            new_medias = json.load(f)
    else:
        new_medias = {}
    return jsonify(new_medias)
###########################配置相关路由###########################
# 读取配置
@app.route('/get_config', methods=['GET'])
def get_config():
    config = read_config(config_path)
    return jsonify({
        'ai_confidence': config['user_config']['ai_confidence'],


        'movies': config['alistconfig']['movies'],
        'series': config['alistconfig']['series'],
        'use_library': config['emby_library_config']['use_library'],

        'use_ai_title': config['user_config']['use_ai_title'],
        'is_use_ai': config['user_config']['is_use_ai'],
        'is_use_asyncio': config['user_config']['is_use_asyncio'],
        'restart_update': config['user_config']['restart_update'],
        'cron': config['emby_library_config']['cron'],
        'iyuu_token': config['emby_config']['iyuu_token'],
        'use_emby_refresh': config['emby_config']['use_emby_refresh'],



        'alist_url': config['alistconfig']['alist_url'],
        'alist_apikey': config['alistconfig']['alist_apikey'],
        'alist_password': config['alistconfig']['alist_password'],

        'use_emby_refresh': config['emby_config']['use_emby_refresh'],
        'emby_url': config['emby_config']['emby_url'],
        'library_movie_new': config['emby_config']['library_movie_new'],
        'library_anime_new': config['emby_config']['library_anime_new'],
        'library_series': config['emby_config']['library_series'],
        'api_key': config['emby_config']['api_key'],

        'chat_api': config['user_config']['chat_api'],



    })

# 保存配置
@app.route('/save_config', methods=['POST'])
def save_config():
    data = request.json
    config = read_config(config_path)

    if 'ai_confidence' in data:
        config['user_config']['ai_confidence'] = str(data['ai_confidence'])


    if 'movies' in data:
        config['alistconfig']['movies'] = str(data['movies'])
    if 'series' in data:
        config['alistconfig']['series'] = str(data['series'])
    if 'use_library' in data:
        config['emby_library_config']['use_library'] = str(data['use_library'])

    if 'use_ai_title' in data:
        config['user_config']['use_ai_title'] = str(data['use_ai_title'])
    if 'is_use_ai' in data:
        config['user_config']['is_use_ai'] = str(data['is_use_ai'])
    if 'is_use_asyncio' in data:
        config['user_config']['is_use_asyncio'] = str(data['is_use_asyncio'])
    if 'restart_update' in data:
        config['user_config']['restart_update'] = str(data['restart_update'])

    if 'cron' in data:
        config['emby_library_config']['cron'] = str(data['cron'])
    if 'iyuu_token' in data:
        config['emby_config']['iyuu_token'] = str(data['iyuu_token'])
    if 'use_emby_refresh' in data:
        config['emby_config']['use_emby_refresh'] = str(data['use_emby_refresh'])



    if 'alist_url' in data:
        config['alistconfig']['alist_url'] = str(data['alist_url'])
    if 'alist_apikey' in data:
        config['alistconfig']['alist_apikey'] = str(data['alist_apikey'])
    if 'alist_password' in data:
        config['alistconfig']['alist_password'] = str(data['alist_password'])

    if 'emby_url' in data:
        config['emby_config']['emby_url'] = str(data['emby_url'])
    if 'library_movie_new' in data:
        config['emby_config']['library_movie_new'] = str(data['library_movie_new'])
    if 'library_anime_new' in data:
        config['emby_config']['library_anime_new'] = str(data['library_anime_new'])
    if 'library_series' in data:
        config['emby_config']['library_series'] = str(data['library_series'])
    if 'api_key' in data:
        config['emby_config']['api_key'] = str(data['api_key'])

    if 'chat_api' in data:
        config['user_config']['chat_api'] = str(data['chat_api'])



    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)
    return "配置已保存"


def generate_logs():
    while True:
        if log_buffer:
            log_line = log_buffer.pop(0)  # 从缓冲区获取日志
            yield f"data: {log_line}\n\n"
        time.sleep(0.5)

@app.route('/stop', methods=['POST'])
def stop_script():
    global process
    if process and process.poll() is None:  # 进程存在且没结束
        process.terminate()  # 尝试安全终止
        return "程序已停止"
    else:
        return "没有正在运行的程序"

@app.route('/log_stream')
def log_stream():
    def generate():
        while True:
            try:
                line = log_queue.get(timeout=1)
                yield f"data: {line}\n\n"
            except queue.Empty:
                continue
    return Response(generate(), content_type='text/event-stream; charset=utf-8')




@app.route('/refresh', methods=['GET','POST'])
def run_script2():
    global log_buffer
    config = read_config(config_path)
    scripts_path = config['user_config']['scripts_path']
    def execute_command():
        global process
        process = subprocess.Popen(
            ['python', '-u', scripts_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',  # 或尝试 'gbk'、'latin1'
            errors='replace',  # 替换无法解码的字符
            bufsize = 1,
        )
        # while True:
        #     # 逐行读取，但不会阻塞
        #     line = process.stdout.readline()
        #     if not line:
        #         if process.poll() is not None:  # 进程结束
        #             break
        #         time.sleep(0.01)
        #         continue
        #     log_queue.put(line.strip())  # 放到队列里
        for line in process.stdout:
            if line.strip():
                log_queue.put(line.strip())
    # 启动线程
    threading.Thread(target=execute_command, daemon=True).start()
    return "刷新已启动，请等待程序执行" #这个提示语会返回到前段右上角临时显示


@app.route('/stream')
def stream():
    config = read_config(config_path)
    scripts_path = config['user_config']['scripts_path']
    # scripts_path = r'D:\p41plus备份\git_code\openlist-rename-strm\alist_rename.py'
    def generate(tvpath=None, moviepath=None,offset=None):
        command = ['python', scripts_path]

        # 根据请求参数构建命令
        if tvpath is not None and offset is not None:
            command.append('--tvpath')
            command.append(tvpath)
            command.append('--offset')
            command.append(offset)
        if tvpath is not None and offset is None:
            command.append('--tvpath')
            command.append(tvpath)  # 使用传入的 tvpath
        if moviepath:
            command.append('--moviepath')
            command.append(moviepath)  # 使用传入的 moviepath

        # 打开日志文件以写入
        with open('data/实时日志.log', 'a') as log_file:
            # 记录执行的命令
            log_file.write(f"执行命令: {' '.join(command)}\n")
            log_file.flush()  # 刷新写入

        # process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # global process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',  # 添加
            errors='replace'  # 添加
        )

        # 打开日志文件以写入
        # with open('data/alist_rename_log.txt', 'a') as log_file:
        #     while True:
        #         output = process.stdout.readline()
        #         if output:
        #             # log_file.write(output)  # 将输出写入日志文件
        #             # log_file.flush()  # 刷新写入
        #             yield f"{output.strip()}\n\n"
        #         if process.poll() is not None:
        #             break
        #     # 如果有错误输出，也要返回
        #     stderr_output = process.stderr.read()
        #     if stderr_output:
        #         # log_file.write(stderr_output)  # 将错误输出写入日志文件
        #         # log_file.flush()  # 刷新写入
        #         yield f"{stderr_output.strip()}\n\n"

        # 实时读取 stdout
        while True:
            line = process.stdout.readline()
            if line:
                yield f"data: {line.rstrip()}\n\n"

            if process.poll() is not None:
                break
        # 读取 stderr
        stderr_output = process.stderr.read()
        if stderr_output:
            for line in stderr_output.splitlines():
                yield f"data: {line.rstrip()}\n\n"
        yield "data: [DONE]\n\n"

    # 从请求中获取 tvpath 和 moviepath 参数
    tvpath = request.args.get('tvpath')  # 获取 tvpath 参数
    moviepath = request.args.get('moviepath')  # 获取 moviepath 参数
    offset = request.args.get('offset')  # 获取 moviepath 参数
    return Response(generate(tvpath, moviepath,offset), content_type='text/event-stream; charset=utf-8')
# 启动Flask应用
if __name__ == '__main__':
    config = read_config(config_path)
    port = config['user_config']['flask_port']
    app.run(host='0.0.0.0', port=port)
