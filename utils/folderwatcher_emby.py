# -*- coding: utf-8 -*-
import sys
import io
from utils.log_utils import logger
import json
import os
# 设置标准输出为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from alist_file_tools import ALIST
import requests
import codecs
import configparser
class AUTO_refreash():
    def __init__(self,config):
        self.url = config['alistconfig']['alist_url']+"/api/fs/dirs"#alist获取文件夹的api /api/admin/storage/load_all
        self.list_url = config['alistconfig']['alist_url']+"/api/fs/list"
        self.alist_token = config['alistconfig']['alist_apikey']
        self.headers = {"Authorization": self.alist_token}#alisttoken
        self.emby_url = config['emby_config']['emby_url']  # 替换为你的 Emby 服务器地址
        self.api_key = config['emby_config']['api_key']  # 替换为你的 API 密钥
        self.libraries_url = config['emby_config']['emby_url']+"/emby/Library/VirtualFolders"#获取文件夹信息
        self.iyuu_token = config['emby_config']['iyuu_token']#iyuuu的token
        #需要监控的alist文件夹
        # self.sync_anime_new = config['alistconfig']['sync_anime_new']
        # self.sync_movie_new = config['alistconfig']['sync_movie_new']
        # self.sync_series = config['alistconfig']['sync_series']
        #需要刷新的emby媒体库
        self.library_anime_new = config['emby_config']['library_anime_new']
        self.library_movie_new = config['emby_config']['library_movie_new']
        self.library_series = config['emby_config']['library_series']

        self.alist = ALIST(config)

        self.sync_movies_paths = config['alistconfig']['movies'].split(',')
        self.sync_series_paths = config['alistconfig']['series'].split(',')
        self.last_dict_path = 'data/dict_files.json'

    def get_files(self,path):
        return self.alist.get_folder_files(path)
    def get_files_with_modifieddate(self,path):
        names,allfiles = self.alist.get_folder_files(path,need_content=True)
        modified_dates = [item['modified'] for item in allfiles['data']['content']]

        names_with_modified_date = [(name, modified_date) for name, modified_date in zip(names, modified_dates)]

        return names_with_modified_date
    def send_iyuu_message(self, title,content=None):

        token = self.iyuu_token # 替换为你的 IYUU 令牌
        if not token or token == 'None':
            logger.warning("⚠️ IYUU token 为空，消息未发送")
            return

        #############格言部分
        # result = self.fetch_data()
        # word = result['result']['word']
        # date = result['result']['date']
        #############


        # 构建请求的 URL
        url = f"https://iyuu.cn/{token}.send"
        # 构建请求体
        if content is not None:
            data = {"text": title,
                    "desp":f'{content}\n\n\n\n'
                           # f'❀✿❁❉❃✾❀✿❁❉❃✾❀✿❁❉\n'
                           # f'{word}\n'
                           # f'{date}\n'
                           # f'❉✿❁❀❃✾❉✿❁❀❃✾❉✿❁❀\n'
                    }
        else:
            data = {"text": title,
                    }

        # 发送 POST 请求
        response = requests.post(url, data=data)
        # 检查请求是否成功
        if response.status_code == 200:
            logger.info("✅消息发送成功！")
        else:
            logger.info(f"消息发送失败，状态码 message send fail,code: {response.status_code}")
    def monitor_folder_signle(self,monitor_folder,dict_files_path,dict_name,index,file_folders_list,need_all_filechanges=False):
    # def monitor_folder_signle(self,monitor_folder=self.sync_anime_new ,mointor_file_path='data/last_anime_files.txt'):
        def load_last_files(filename,dict_name):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    # 加载 JSON 数据
                    entries = json.load(f)
                    # 将数据转换为集合
                    try :
                        files_set = entries[dict_name]
                    except:
                        files_set = []
                    return files_set
            except FileNotFoundError:
                logger.info(f"文件未找到: {filename}")
                return set()
            except json.JSONDecodeError:
                logger.info(f"错误: 读取 {filename} 失败，文件格式无效!")
                return set()
        def check_files(filename, file_folders_list):
            need_write = False
            # 检查文件是否存在
            if os.path.exists(filename):
                # 如果文件存在，读取现有内容
                with open(filename, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        # 如果文件格式无效，初始化为空列表
                        data = {}
            else:
                # 如果文件不存在，初始化为空列表
                data = {}
            for key in list(data.keys()):
                if key not in file_folders_list:
                    del data[key]
                # 检查新增的文件夹并添加到数据中
            for folder in file_folders_list:
                if folder not in data:
                    need_write = True  # 初始化为空列表或其他适合的结构
            # 将数据写回 JSON 文件
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)  # 写入文件
            return need_write


        def save_current_files(filename, entries, dict_name):
            # 将 entries 转换为列表形式
            dicts = {f'{dict_name}':list(entries)}

            # 检查文件是否存在
            if os.path.exists(filename):
                # 如果文件存在，读取现有内容
                with open(filename, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        # 如果文件格式无效，初始化为空列表
                        data = {}
            else:
                # 如果文件不存在，初始化为空列表
                data = {}
            data.update(dicts)
            for key in list(data.keys()):
                if key not in file_folders_list:
                    del data[key]
            # 将数据写回 JSON 文件
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)  # 写入文件

        def calculate_changes(current, last):
            # 文件名集合
            current_names = {name for (name, _) in current}

            # 处理 last 为空的情况
            if not last:
                last_names = set()
                # last_mtime_dict = {}
            else:
                last_names = {item[0] for item in last}
                # last_mtime_dict = {item[1] for item in last}  # 用字典存储文件修改时间

            # 新增的文件
            new_names = current_names - last_names
            # 删除的文件
            deleted_names = last_names - current_names
            # 可能修改的文件
            common_names = current_names|last_names

            modified = set()

            current = [list(itme) for itme in current]
            last = [list(itme) for itme in last]
            for name in common_names:
                if last:
                    current_mtime = next((item[1] for item in current if item[0] == name), None)  # 获取当前文件的修改时间
                    last_mtime = next((item[1] for item in last if item[0] == name), None)  # 获取当前文件的修改时间
                    # last_mtime =    [item[1] for item in last    if item[0] == name][0] # 获取之前记录的修改时间

                    if last_mtime != current_mtime and current_mtime is not None and last_mtime is not None:
                        modified.add((name, current_mtime))

            for name, mtime in modified:
                new_names.add(name)
                logger.info(f'发现修改文件夹：{name}, 修改时间：{mtime}')

            return new_names, deleted_names, modified
        # 读取上次记录的文件及其修改时间
        last_anime_files = load_last_files(dict_files_path,dict_name)
        # 获取当前文件列表及其修改时间
        current_anime_files = set(self.get_files_with_modifieddate(monitor_folder))
        # 计算各类型事件
        new_anime, deleted_anime, modified_anime = calculate_changes(current_anime_files, last_anime_files)
        new_anime_folders_with_path = [monitor_folder + '/' + folder for folder in new_anime]
        deleted_anime_folders_with_path = [monitor_folder + '/' + folder for folder in deleted_anime]
        # 保存当前状态

        need_write = check_files(dict_files_path, file_folders_list)
        if need_all_filechanges or need_write:
            save_current_files(dict_files_path, current_anime_files,dict_name)
        if index==1:
            dict_files = {
                          'new_anime_folders_with_path': new_anime_folders_with_path,
                          'deleted_anime_folders_with_path': deleted_anime_folders_with_path,
                          'new_anime_files': new_anime,
                          'deleted_anime_files': deleted_anime,
                          }
        elif index==0:
            dict_files = {
                'new_movie_folders_with_path': new_anime_folders_with_path,
                'deleted_movie_folders_with_path': deleted_anime_folders_with_path,
                'new_movie_files': new_anime,
                'deleted_movie_files': deleted_anime,
            }
        else:
            dict_files = None
            logger.error(f'index错误')
        return dict_files

    def monitor_folder(self,need_all_filechanges=False,data_file_path=None):
        folders=[]
        movie_monitor_folder = self.sync_movies_paths
        for folder in movie_monitor_folder:
            folders.append(os.path.basename(folder))
        series_monitor_folder = self.sync_series_paths
        for folder in series_monitor_folder:
            folders.append(os.path.basename(folder))
        mointor_list = [movie_monitor_folder,series_monitor_folder]
        if data_file_path is not None:
            dict_files_path = data_file_path
        else:
            dict_files_path =self.last_dict_path
        data_dict_series = {
            'new_anime_folders_with_path': [],
            'deleted_anime_folders_with_path': [],
            'new_anime_files': [],
            'deleted_anime_files': [],
        }
        data_dict_movies = {
            'new_movie_folders_with_path': [],
            'deleted_movie_folders_with_path': [],
            'new_movie_files': [],
            'deleted_movie_files': [],
        }
        for index,mointor_folder in enumerate(mointor_list):
            if index==1:
                for mointor in mointor_folder:
                    new_data = self.monitor_folder_signle(mointor,dict_files_path,dict_name=os.path.basename(mointor),
                                                          index=index,file_folders_list=folders,need_all_filechanges=need_all_filechanges)
                    for key in data_dict_series:
                        if key in new_data:  # 确保 new_data 里有这个键
                            if isinstance(data_dict_series[key], set):
                                # 如果是 set，则取并集
                                data_dict_series[key] |= set(new_data.get(key, set()))
                            elif isinstance(data_dict_series[key], list):
                                # 如果是 list，则转换成 set 取并集，再转换回 list
                                data_dict_series[key] = list(set(data_dict_series[key]) | set(new_data.get(key, [])))
                            else:
                                # 其他类型（如 int、str），可以按需求处理
                                data_dict_series[key] = new_data[key]  # 这里选择覆盖原值，你可以改成别的逻辑
            else:
                for mointor in mointor_folder:
                    new_data = self.monitor_folder_signle(mointor,dict_files_path,
                                                          dict_name=os.path.basename(mointor),
                                                          index=index,file_folders_list=folders,need_all_filechanges=need_all_filechanges)
                    for key in data_dict_movies:
                        if key in new_data:  # 确保 new_data 里有这个键
                            if isinstance(data_dict_movies[key], set):
                                # 如果是 set，则取并集
                                data_dict_movies[key] |= set(new_data.get(key, set()))
                            elif isinstance(data_dict_movies[key], list):
                                # 如果是 list，则转换成 set 取并集，再转换回 list
                                data_dict_movies[key] = list(set(data_dict_movies[key]) | set(new_data.get(key, [])))
                            else:
                                # 其他类型（如 int、str），可以按需求处理
                                data_dict_movies[key] = new_data[key]  # 这里选择覆盖原值，你可以改成别的逻辑
        update_dict = {**data_dict_movies, **data_dict_series}
        return update_dict


    def monitor_folder_f(self,need_all_filechanges=False):
        def load_last_files(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    entries = set()
                    for line in f.read().splitlines():
                        if ',' in line:
                            name, mtime_str = line.split(',', 1)
                            try:
                                entries.add((name, mtime_str))
                            except ValueError:
                                logger.info(f"error:读取{filename}失败!")
                                continue
                    return entries
            except FileNotFoundError:
                return set()
        def save_current_files(filename, entries):
            with open(filename, 'w', encoding='utf-8') as f:
                for (name, mtime) in entries:
                    f.write(f"{name},{mtime}\n")

        def calculate_changes(current, last):
            # 文件名集合
            current_names = {name for (name, _) in current}
            last_names = {name for (name, _) in last}

            # 新增的文件名（全新文件）
            new_names = current_names - last_names
            # 删除的文件名（彻底消失的文件）
            deleted_names = last_names - current_names
            # 可能修改的文件名（存在于两次记录中的文件）
            common_names = current_names & last_names
            # 详细分析修改事件
            modified = set()
            # new = set()
            # deleted = set()
            # for name in new_names:
            #     new.add((name, [mtime for (n, mtime) in current if n == name][0]))
            # for name in deleted_names:
            #     deleted.add((name, [mtime for (n, mtime) in last if n == name][0]))
            for name in common_names:
                last_mtime = [mtime for (n, mtime) in last if n == name][0]
                current_mtime = [mtime for (n, mtime) in current if n == name][0]
                if current_mtime != last_mtime:
                    modified.add((name, current_mtime))

            for name in modified:
                new_names.add(name[0])
                logger.info(f'✏️发现修改文件夹：{name[0]},修改时间：{name[1]}')
            return new_names, deleted_names, modified

        # 读取上次记录的文件及其修改时间
        last_anime_files = load_last_files('data/last_anime_files.txt')
        last_movie_files = load_last_files('data/last_movie_files.txt')
        last_series_files = load_last_files('data/last_series_files.txt')
        # 获取当前文件列表及其修改时间
        current_anime_files = set(self.get_files_with_modifieddate(self.sync_anime_new))
        current_movie_files = set(self.get_files_with_modifieddate(self.sync_movie_new))
        current_series_files = set(self.get_files_with_modifieddate(self.sync_series))

        # 计算各类型事件
        new_anime, deleted_anime, modified_anime = calculate_changes(current_anime_files, last_anime_files)
        new_movie, deleted_movie, modified_movie = calculate_changes(current_movie_files, last_movie_files)
        new_series, deleted_series, modified_series = calculate_changes(current_series_files, last_series_files)

        new_anime_folders_with_path = [self.sync_anime_new + '/' + folder for folder in new_anime]
        new_movie_folders_with_path = [self.sync_movie_new + '/' + folder for folder in new_movie]
        new_series_folders_with_path = [self.sync_series + '/' + folder for folder in new_series]

        deleted_anime_folders_with_path = [self.sync_anime_new + '/' + folder for folder in deleted_anime]
        deleted_movie_folders_with_path = [self.sync_movie_new + '/' + folder for folder in deleted_movie]
        deleted_series_folders_with_path = [self.sync_series + '/' + folder for folder in deleted_series]
        # 保存当前状态
        if need_all_filechanges:
            save_current_files('data/last_anime_files.txt', current_anime_files)
            save_current_files('data/last_movie_files.txt', current_movie_files)
            save_current_files('data/last_series_files.txt', current_series_files)

        dict_files = {
                        'current_anime_files': current_anime_files,
                        'current_movie_files': current_movie_files,
                        'current_series_files': current_series_files,


                      'new_anime_folders_with_path': new_anime_folders_with_path,
                      'new_movie_folders_with_path': new_movie_folders_with_path,
                      'new_series_folders_with_path': new_series_folders_with_path,

                      'deleted_anime_folders_with_path': deleted_anime_folders_with_path,
                      'deleted_movie_folders_with_path': deleted_movie_folders_with_path,
                      'deleted_series_folders_with_path': deleted_series_folders_with_path,

                      'new_anime_files': new_anime,
                      'new_movie_files': new_movie,
                      'new_series_files': new_series,

                      'deleted_anime_files': deleted_anime,
                      'deleted_movie_files': deleted_movie,
                      'deleted_series_files': deleted_series
                      }
        return dict_files

    def fetch_data(self):
        url = "https://whyta.cn/api/tx/one?key=cc8cba0a7069"
        try:
            response = requests.get(url)
            response.raise_for_status()  # 检查请求是否成功
            data = response.json()  # 解析JSON响应
            return data
        except requests.exceptions.RequestException as e:
            logger.info(f"❌请求失败: {e}")
            return None
    def emby_refresh_old(self,library_name,name):
        params = {"api_key": self.api_key}
        response = requests.get(self.libraries_url, params=params)
        libraries = response.json()
        library_id = None
        for library in libraries:
            if library["Name"] == library_name:
                library_id = library["ItemId"]
                break

        if library_id:
            # 刷新该媒体库
            refresh_url = f"{self.emby_url}/emby/Library/Refresh"
            data = {"LibraryItemId": library_id}
            refresh_response = requests.post(refresh_url, json=data, params=params)
            if refresh_response.status_code == 204:
                logger.info(f"✅媒体库 '{library_name}' 刷新成功")
                try:
                    self.send_iyuu_message('✅Emby更新提醒',f"[{','.join(name)}]刷新成功")
                except:
                    self.send_iyuu_message('✅Emby更新提醒',f"{name}刷新成功")
            else:
                logger.info(f"刷新失败，状态码: {refresh_response.status_code}")
                self.send_iyuu_message('❌Emby刷新失败',f"刷新失败，状态码: {refresh_response.status_code}")
        else:
            logger.info(f"未找到名为 '{library_name}' 的媒体库")
            self.send_iyuu_message('❌Emby刷新失败',f"未找到名为[{library_name}]的媒体库")
    def emby_refresh(self,library_name,name,status,notify=True):
        params = {"api_key": self.api_key}
        response = requests.get(self.libraries_url, params=params)
        libraries = response.json()
        library_id = None
        for library in libraries:
            if library["Name"] == library_name:
                library_id = library["ItemId"]
                break
        for library in libraries:#因为动漫和剧集都归类到剧集里面了，所以要在识别到剧集的时候同时刷新动漫和剧集媒体库
            if library["Name"] == self.library_series:
                library_id2 = library["ItemId"]
                break

        if library_id:
            # 刷新该媒体库
            refresh_url = f"{self.emby_url}/emby/Items/{library_id}/Refresh"
            refresh_url2 = f"{self.emby_url}/emby/Items/{library_id2}/Refresh"
            refresh_params = {
                   'Recursive': 'true',
                   'ImageRefreshMode': 'Default',
                   'MetadataRefreshMode': 'Default',
                   'ReplaceAllImages': 'false',
                   'ReplaceAllMetadata': 'false',
                   'api_key': self.api_key
                    }
            refresh_response = requests.post(refresh_url, params=refresh_params)
            refresh_response2 = requests.post(refresh_url2, params=refresh_params)
            if refresh_response.status_code == 204:
                logger.info(f"✅媒体库 '{library_name}' 刷新成功")
                if notify:
                    try:
                        self.send_iyuu_message('✅Emby更新提醒',f"{status[0]}:[{','.join(name)}]{status[1]}成功")
                    except:
                        self.send_iyuu_message('✅Emby更新提醒',f"{status[0]}:{name}{status[1]}成功!")
            else:
                logger.info(f"刷新失败，状态码: {refresh_response.status_code}")
                self.send_iyuu_message('Emby刷新失败',f"刷新失败，状态码: {refresh_response.status_code}")
        else:
            logger.info(f"未找到名为 '{library_name}' 的媒体库")
            self.send_iyuu_message('Emby刷新失败',f"未找到名为[{library_name}]的媒体库")
def read_config(config_path):
    config = configparser.ConfigParser()
    with codecs.open(config_path, 'r', encoding='utf-8') as f:
        config.read_file(f)
    return config
if __name__ == "__main__":
    # pass
    config = read_config('../config/config.ini')
    auto_refreash = AUTO_refreash(config)
    # auto_refreash.monitor_folder()
    # auto_refreash.send_iyuu_message('测试','更新成功')
    # auto_refreash.refresh_files()
    # files = auto_refreash.get_files('/115_15TB/动漫New')
    # logger.info(files)
    # auto_refreash.emby_refresh('115动漫light','测试文件名')
    auto_refreash.monitor_folder(need_all_filechanges=True,data_file_path='../data/dict_files.json')

