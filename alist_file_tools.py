import requests
import json
import os
import configparser
import urllib.parse
from utils.log_utils import logger, config_path
import codecs
import shutil
import time
import argparse
import hashlib
import sys

class ALIST():
    def __init__(self,config):
        self.alist_url = config['alistconfig']['alist_url']
        self.get_folder_files_url = self.alist_url + '/api/fs/list'
        self.rename_filename_url = self.alist_url + '/api/fs/rename'
        self.move_file_url = self.alist_url + '/api/fs/move'
        self.is_file_url = self.alist_url + '/api/fs/get'
        self.new_folder_url = self.alist_url + '/api/fs/mkdir'
        self.delete_file_url = self.alist_url + '/api/fs/remove'
        self.get_dirs = self.alist_url + '/api/fs/dirs'
        self.copy_file_url = self.alist_url + '/api/fs/copy'
        self.delete_user_cache = self.alist_url + '/api/admin/user/del_cache'
        self.alist_token = config['alistconfig']['alist_apikey']
        self.password = config['alistconfig']['alist_password']
        # self.get_folder_files(folder_path=config['alistconfig']['refresh_folder'], refresh=True)#程序执行第一次进行刷新
        self.video_extensions = {
                                            '.mp4',    # MPEG-4 Part 14
                                            '.avi',    # Audio Video Interleave
                                            '.mkv',    # Matroska Video
                                            '.mov',    # Apple QuickTime Movie
                                            '.wmv',    # Windows Media Video
                                            '.flv',    # Adobe Flash Video
                                            '.webm',   # WebM Video
                                            '.mpeg',   # MPEG Video
                                            '.mpg',    # MPEG Video
                                            '.ts',     # MPEG Transport Stream
                                            '.m4v',    # MPEG-4 Video
                                            '.3gp',     # 3GPP Multimedia
                                            '.3g2',    # 3GPP2 Multimedia
                                            '.rm',     # RealMedia
                                            '.rmvb',   # RealMedia Variable Bitrate
                                            '.vob',    # Video Object
                                            '.ogg',    # Ogg Video
                                            '.drc',    # Dynamic Range Control
                                            '.mts',    # AVCHD Video
                                            '.m2ts',   # Blu-ray Disc Audio-Video MPEG-2 Transport Stream
                                            '.xvid',   # Xvid Video
                                            '.divx',   # DivX Video
                                            '.nsv',    # Nullsoft Streaming Video
                                            '.f4v',    # Flash MP4 Video
                                            '.svi',    # Samsung Video Interleave
                                            '.asf',    # Advanced Streaming Format
                                            '.iso',
                                        }
        self.download_extensions = {
                                            '.ass',  # Advanced SubStation Alpha
                                            '.srt',  # SubRip Subtitle
                                            '.ssa',  # SubStation Alpha
                                            '.vtt',  # WebVTT
                                            '.sub',  # MicroDVD Subtitle
                                            '.idx',  # IDX/Sub Subtitle
                                            '.dvb',  # DVB Subtitles
                                            '.mpl2',  # MPlayer Subtitle
                                            '.ttxt',  # Teletext Subtitle
                                            '.xml',  # XML Subtitle (some formats)
                                            '.sbv',  # SubRip VTT
                                            '.lrc',  # Lyrics file format
                                            '.pjs',  # Pomcast Subtitle
                                            '.smi',  # SAMI Subtitle
                                            '.txt',  # Plain text subtitles
                                            '.aqt',  # AQT Subtitle
                                            '.jss',  # JSS Subtitle
                                            '.dks',  # DKS Subtitle
                                            '.cap',  # Captions
                                            '.subrip',  # SubRip Subtitle (sometimes used as a full name)
                                            '.stl',  # Spruce Subtitle File
                                            '.srtv',  # SRT Video Subtitle
                                            '.txtv',  # Text Video Subtitle
                                            '.sup',  # DVD Subtitle
                                            }
        # self.download_extensions = {}
        pass
    def get_dirs_info(self,folder_path):
        url = self.get_dirs
        payload = json.dumps({
            "path": folder_path,
            "password": self.password,
            "force_root": False
        })
        headers = {
            'Authorization': self.alist_token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }

        allfiles = requests.request("POST", url, headers=headers, data=payload).json()
        if allfiles.get('code') == 200:
            modified_time = allfiles['data'][0]['modified']
        else:
            modified_time = None
        return modified_time

    def get_folder_files(self,folder_path,refresh=True,need_content=False,single_name = None):
        url = self.get_folder_files_url
        payload = json.dumps({
           "path": folder_path,
           "password": self.password,
           "page": 1,
           "per_page": 0,
           "refresh": refresh
        })
        # if refresh:
        #     logger.info('调用刷新')
        headers = {
           'Authorization': self.alist_token,
           'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
           'Content-Type': 'application/json'
        }

        allfiles = requests.request("POST", url, headers=headers, data=payload).json()
        # time.sleep(1)
        if allfiles.get('code') == 200 and allfiles['data']['content'] is not None:
            names = [item['name'] for item in allfiles['data']['content']]
        elif allfiles.get('code') == 500:
            if single_name is not None:
                logger.warning(
                    f'❌未找到[{single_name}]文件夹，可能此文件夹不存在')
            else:
                logger.warning(
                    f'❌未找到[{folder_path}]文件夹，可能此文件夹不存在')
            names = False
            # sys.exit(1)
        else:
            names = None#表示文件夹是空的
        if need_content:
            return names,allfiles
        else:
            return names

    def rename_filename(self,src_name_path,renamed_name):
        """
        :param src_name_path: 需要命名文件的绝对路径
        :param renamed_name:  需要命名文件的新名字
        :return: None
        """
        url = self.rename_filename_url
        #alsit.rename_filename(ori_name_path='/115_15TB/动漫New/新建文件夹', renamed_name='renamed')
        payload = json.dumps({
            "name": renamed_name,
            "path": src_name_path
        })
        headers = {
            'Authorization': self.alist_token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload).json()
        if response.get('code') == 200:
            pass
        else:
            logger.info(f"❌Error: {response.get('message')}，此错误与alist的api相关")
    def move_file(self,src_dir,dst_dir,file_names):
        url = self.move_file_url
        #alsit.rename_filename(ori_name_path='/115_15TB/动漫New/新建文件夹', renamed_name='renamed')
        payload = json.dumps({
            "src_dir": src_dir,
            "dst_dir": dst_dir,
            "names": [file_names]
        })
        headers = {
            'Authorization': self.alist_token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload).json()
        attempts = 1
        while attempts < 5:
            time.sleep(0.3)
            if not self.if_file_exist(src_dir + '/' + file_names):
                break
            self.get_folder_files(src_dir)
            time.sleep(3)
            attempts += 1
            logger.info(f'正在移动{file_names}...attempts:{attempts}')
        else:
            logger.error(f"❌超过最大尝试次数，文件[{file_names}] 可能未移动，执行退出")
            logger.error(f"❌请重新刷新程序！")
            sys.exit()
        if response.get('code') == 200:
            logger.info(f"✅|{file_names}| 从 |{src_dir}| 移动到了 |{dst_dir}|")
            # logger.info(f"Successfully moved files")
        else:
            logger.info(f"❌Error: {response.get('message')}，此错误与alist的api相关，可能115的cookies失效了")
    def copy_file(self,src_dir,dst_dir,file_names):
        url = self.copy_file_url
        payload = json.dumps({
            "src_dir": src_dir,
            "dst_dir": dst_dir,
            "names": [file_names]
        })
        headers = {
            'Authorization': self.alist_token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload).json()
        if response.get('code') == 200:
            logger.info(f"✅{file_names}从{src_dir}复制到了{dst_dir}")
        else:
            logger.info(f"❌Error: {response.get('message')}，目标文件夹已存在")
    def is_file(self,file_path,hash=False,modified_time=False):
        '''
        如果hash为True，则file_path应该是单个文件的地址，然后次函数会返回文件的sha1
        '''
        url = self.is_file_url
        # alsit.rename_filename(ori_name_path='/115_15TB/动漫New/新建文件夹', renamed_name='renamed')
        payload = json.dumps({
            "path": file_path,
            "password": self.password,
            "page": 1,
            "per_page": 0,
            "refresh": False
        })
        headers = {
            'Authorization': self.alist_token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload).json()
        if response.get('code') == 200:
            pass
        elif response.get('code') == 500:
            logger.info(f"❌Error: {response.get('message')}，此错误与alist的api相关，可能115的cookies失效了")
        status = response.get('data')['is_dir']
        if hash:
            hash_info: dict = response.get('data')['hash_info']
            status = hash_info.get('sha1')
        if modified_time:
            status = response.get('data')['modified']
        return status
    def if_file_exist(self,file_path):
        '''
        如果hash为True，则file_path应该是单个文件的地址，然后次函数会返回文件的sha1
        '''
        url = self.is_file_url
        # alsit.rename_filename(ori_name_path='/115_15TB/动漫New/新建文件夹', renamed_name='renamed')
        payload = json.dumps({
            "path": file_path,
            "password": self.password,
            "page": 1,
            "per_page": 0,
            "refresh": False
        })
        headers = {
            'Authorization': self.alist_token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload).json()
        if response.get('code') == 200:
            status = True
        elif response.get('code') == 500:
            status = False
        else:
            status = False
        return status
    def create_new_folder(self,folder_ptah):
        url = self.new_folder_url
        payload = json.dumps({
            "path": folder_ptah,
        })
        headers = {
            'Authorization': self.alist_token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload).json()
        if response.get('code') == 200:
            logger.info(f"✅成功创建文件夹:{folder_ptah}")
        else:
            logger.info(f"❌Error: {response.get('message')}，此错误与alist的api相关，可能115的cookies失效了")
    # def local_is_a_file(self,path):
    #     _, ext = os.path.splitext(path)
    #     if bool(ext):
    #         return True
    #     else:
    #         return False

    def local_is_a_file(self, path):
        '''
        判断一个文件夹的尾端是文件还是文件夹
        文件返回True，否则返回False
        '''
        # 分割路径获取扩展名（包括点，如 ".mp4"）
        _, ext = os.path.splitext(path)
        # 统一转为小写，避免大小写敏感问题（如 ".MP4"）
        ext_lower = ext.lower()
        # 直接判断扩展名是否在预定义的视频扩展名集合中，如果在返回True，否则返回False
        return ext_lower in self.video_extensions
    def is_localfile_is_a_folder(self, path):
        '''
        判断一个路径的末端是不是文件夹，是的话返回True，否则返回False
        '''
        # 分割路径获取扩展名（包括点，如 ".mp4"）
        _, ext = os.path.splitext(path)
        # 统一转为小写，避免大小写敏感问题（如 ".MP4"）
        ext_lower = ext.lower()
        if ext_lower:
            return False
        else:
            return True
    def delete_file(self,filename,single_name = None):
        url = self.delete_file_url
        payload = json.dumps({
            "names": [filename],
        })
        headers = {
            'Authorization': self.alist_token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload).json()
        if not self.local_is_a_file(filename):
            attempts = 1
            while attempts < 5:
                time.sleep(0.5)
                if not self.if_file_exist(filename):
                    break
                attempts += 1
                logger.info(f'🗑️正在删除文件：{filename}...attempts:{attempts}')
                time.sleep(3)
                if self.is_localfile_is_a_folder(filename):
                    time.sleep(1)
                    self.get_folder_files(filename)
                else:
                    self.get_folder_files(os.path.split(filename)[0])
            else:
                logger.error(f"❌Error: 超过最大尝试次数，文件[{filename}] 可能未能删除，执行退出")
                sys.exit()

        if response.get('code') == 200:
            if single_name != None:
                logger.info(f"🗑️已删除文件：[{single_name}]")
            else:
                logger.info(f"🗑️已删除文件：[{filename}]")
        else:
            logger.info(f"❌Error: {response.get('message')}，此错误与alist的api相关，可能115的cookies失效了")

    def delete_usercache(self,username):
        url = self.delete_user_cache
        params = {"username": username}
        headers = {
            'Authorization': self.alist_token,
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, params=params).json()
        if response.get('code') == 200:
            logger.info(f"✅用户[{username}]缓存成功删除")
        else:
            logger.info(f"❌Error: {response.get('message')}，此错误与alist的api相关，可能115的cookies失效了")
    def create_strm(self, strm_local_path, strm_file_name, strm_content):
        full_path = os.path.join(strm_local_path, f"{strm_file_name}.strm")

        # 检查文件是否存在
        if os.path.exists(full_path):
            # 如果文件存在，读取其内容并进行比较
            with open(full_path, 'r',encoding='utf-8') as file:
                existing_content = file.read()
                # 如果内容相同，打印信息并返回
                if existing_content == strm_content:
                    logger.info(f"⚠️{strm_file_name}.strm已经存在或内容相同，跳过生成strm")
        # 如果文件不存在或内容不同，则创建文件
        else:
            try:
                with open(full_path, 'w',encoding='utf-8') as file:
                    file.write(strm_content)
                    logger.info(f'✅{strm_file_name}的strm创建成功')
                    # logger.info(f"Created file '{full_path}'.")
            except Exception as e:
                logger.error(f'❌{e}')

    def filename_to_filepath(self,files_path,filename):#输入内容是列表形式，输出也是列表形式
        filespath = []
        for name in filename:
            filespath.append(files_path+'/'+name)
        return filespath

    def detect_is_file_or_path(self,allfiles):
        file_labels = {}
        allfiles_items = allfiles['data']['content']
        for item in allfiles_items:
            if item['is_dir']:  # 假设 `is_file` 方法返回 True 表示是文件
                file_labels[item['name']] = "folder"  # 文件标签
            else:
                file_labels[item['name']] = "file"  # 文件夹标签
        return file_labels

    def is_video_file(self, name):
        # 定义常见的视频文件扩展名
        video_extensions = self.video_extensions
        # 获取文件的扩展名
        _, ext = os.path.splitext(name.lower())  # 使用 lower() 确保忽略大小写
        # 检查扩展名是否在视频扩展名列表中
        if ext in video_extensions:
            # 返回去掉扩展名的文件名
            return os.path.splitext(name)[0]  # 返回没有扩展名的文件名
        return False  # 如果不是视频文件，则返回 None

    def download_file(self,url, save_directory, file_name=None):
        # 确保保存目录存在
        os.makedirs(save_directory, exist_ok=True)
        # 如果未提供文件名，则从 URL 提取文件名
        if file_name is None:
            file_name = url.split('/')[-1]

        file_path = os.path.join(save_directory, file_name)
        try:
            # 发送 GET 请求
            response = requests.get(url, stream=True)
            response.raise_for_status()  # 检查请求是否成功

            # 写入文件
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):  # 逐块写入
                    file.write(chunk)
                return True
        except requests.exceptions.RequestException as e:
            logger.error(f'❌文件下载失败：{e},此错误与alist的api相关，可能115的cookies失效了')
            return False

    def encode_chinese_only(self,text):
        """
        Encode only Chinese characters in the given text to URL format.

        Parameters:
            text (str): The input string to encode.

        Returns:
            str: The encoded string with only Chinese characters encoded.
        """
        encoded_string = ''

        for char in text:
            # 检测是否为中文字符
            if '\u4e00' <= char <= '\u9fff':  # 检查是否在中文字符范围内
                encoded_string += urllib.parse.quote(char)  # 对中文字符进行编码
            else:
                encoded_string += char  # 保留其他字符不变

        return encoded_string

    def remove_local_folder(self,folder_path):
        """
        Remove a folder (empty or non-empty).

        Parameters:
            folder_path (str): The path of the folder to remove.
        """
        if os.path.exists(folder_path):
            try:
                # 首先尝试使用shutil.rmtree
                shutil.rmtree(folder_path, ignore_errors=True)  # 添加ignore_errors=True参数

                # 检查文件夹是否仍然存在
                if os.path.exists(folder_path):
                    # 如果仍然存在，使用系统命令强制删除
                    import subprocess
                    logger.info(f"强制删除：{os.path.basename(folder_path)}")
                    subprocess.run(['rm', '-rf', folder_path], check=False)

                if not os.path.exists(folder_path):
                    logger.info(f"🗑️成功删除文件夹: {os.path.basename(folder_path)}")
                else:
                    logger.warning(f"⚠️文件夹删除失败，可能需要更高权限: {os.path.basename(folder_path)}")
            except Exception as e:
                logger.warning(f"Error: {e}")
        else:
            logger.warning(f"⚠️所要删除的文件夹不存在: {os.path.basename(folder_path)}")

    def remove_local_single_file(self, file_path):
        """
        Remove a single file.

        Parameters:
            file_path (str): The path of the file to remove.
        """
        if os.path.exists(file_path):
            try:
                os.remove(file_path)  # 删除单个文件
                logger.info(f"🗑️成功删除文件: {os.path.basename(file_path)}")
            except Exception as e:
                logger.error(f"❌Error: {e}")
        else:
            logger.warning(f"⚠️所要删除的文件不存在: {os.path.basename(file_path)}")
    def start_to_create_strm(self,to_named_paths,local_strm_root_path):
        if isinstance(to_named_paths, list):
            to_named_paths = to_named_paths
        else:
            to_named_paths = [to_named_paths]
        for to_named_path in to_named_paths:
            logger.info(f'🔄开始遍历[{os.path.basename(to_named_path)}]')
            if self.local_is_a_file(to_named_path):
                # logger.info(f'❌生成strm报错：{to_named_path}是单文件，或者文件夹名称含有视频后缀结尾，请放到文件夹中，或者修改文件夹名称')
                continue
            folder_files,allfiles = self.get_folder_files(to_named_path,refresh=False, need_content=True)

            if folder_files is None:
                logger.warning(f'❌文件夹: {to_named_path}，是空的文件夹，请删除文件夹后再来操作')
                return  # 直接返回，避免后续操作
            name_path_map = self.detect_is_file_or_path(allfiles)
            for name in name_path_map:
                if name_path_map[name]=='file':
                    is_video = self.is_video_file(name)
                    if is_video:
                        strm_name = name
                        strm_content = self.encode_chinese_only(self.alist_url+'/d'+ to_named_path+'/'+strm_name)
                        strm_local_path = local_strm_root_path+to_named_path
                        try:
                            os.makedirs(strm_local_path, exist_ok=True)
                        except:
                            logger.error(f'❌目录名称无效：{strm_local_path} 跳过')
                            continue
                        self.create_strm(strm_local_path, is_video, strm_content)

                    else:
                        _, file_extension = os.path.splitext(name)
                        if file_extension in self.download_extensions:
                            strm_local_path = local_strm_root_path + to_named_path
                            url = self.alist_url + '/d'+to_named_path+'/'+name
                            if not os.path.exists(strm_local_path+'/'+name):
                                if self.download_file(url,strm_local_path):
                                    time.sleep(0.1)
                                    logger.info(f'⬇️{name}：下载成功')
                            else:
                                sha1 = hashlib.sha1()
                                with open(strm_local_path+'/'+name, 'rb') as file:
                                    while chunk := file.read(8192):  # 以块的形式读取文件
                                        sha1.update(chunk)
                                local_file_sha1 = sha1.hexdigest().upper()
                                remote_file_sha1 = self.is_file(to_named_path+'/'+name, hash=True)
                                if local_file_sha1 == remote_file_sha1:
                                    logger.info(f'⚠️{name}已经存在,且hash相同，无需下载')
                                else:
                                    logger.info(f'⚠️{name}已经存在,但hash不相同，开始重新下载')
                                    if self.download_file(url, strm_local_path):
                                        time.sleep(0.1)
                                        logger.info(f'⬇️{name}：下载成功')
                        else:
                            logger.info(f'⏭️跳过：{name}，文件格式：{file_extension} 不在下载范围')
                else:
                    new_to_named_path = to_named_path+'/'+name
                    # logger.info(f'现在正在遍历的路径是：*****{new_to_named_path}*****')
                    self.start_to_create_strm(new_to_named_path,local_strm_root_path)

    def delete_local_strm_folders(self, to_delete_strm_folder_path, local_strm_folder):#输入是一个列表
        # logger.info(f'开始删除{to_delete_strm_folder_path}')
        # logger.info(f'strm的目标root文件夹为*****{local_strm_root_path}*****')
        for path in to_delete_strm_folder_path:
            if self.local_is_a_file(path):
                base_path, filename = os.path.split(path)
                # filename_wo_extension,extension = os.path.splitext(filename)
                path = base_path+'/'+filename + '.strm'
                self.remove_local_single_file(local_strm_folder + path)
            else:
                self.remove_local_folder(local_strm_folder + path)
    def movie_rename(self,moviepath):
        for _ in range(2):#有重名文件删除两次
            _,file_list = self.get_folder_files(moviepath, need_content=True)
            """
            处理单个视频文件夹
            1.保留视频文件夹中最大的视频文件，以及所有字幕文件
            2.对字幕文件重命名，命名为视频的名字
            """
            video_items = file_list['data']['content']
            if video_items is None:
                logger.error(f'❌文件夹{moviepath}是空的,程序将会删除')
                self.delete_file(moviepath,single_name=os.path.basename(moviepath))
                return
            # 常见的视频扩展名和字幕扩展名
            video_extensions = self.video_extensions
            subtitle_extensions = {".srt", ".ass", ".sub", ".ssa", ".idx"}

            # 筛选出视频文件
            video_files = [
                file for file in video_items
                if any(file["name"].lower().endswith(ext) for ext in video_extensions)
            ]
            # 找到最大的常见视频文件
            largest_video = max(video_files, key=lambda x: x["size"], default=None)
            # 遍历文件列表，标记要保留的文件
            remaining_files = []
            for file in video_items:
                file_name = file["name"].lower()
                if any(file_name.endswith(ext) for ext in video_extensions):  # 视频文件
                    if file == largest_video:
                        remaining_files.append(file)
                    else:
                        self.delete_file(moviepath +'/'+ file['name'],single_name=file['name'])
                        # logger.info(f"✅已删除视频文件: {file['name']}")
                elif any(file_name.endswith(ext) for ext in subtitle_extensions):  # 字幕文件
                    remaining_files.append(file)
                else:
                    self.delete_file(moviepath+'/'+file['name'],single_name=file['name'])
                    # logger.info(f"✅已删除文件: {file['name']}")
        for file in remaining_files:
            logger.info(f'🎬文件删除完毕，保留：{file["name"]}')
        """
                将字幕的名字命名为视频的名字
                video_path：是需要命名字幕所在的文件夹
                video_and_subtitle：包含视频名字以及字幕名字的列表
                """
        name_list = []
        for item in remaining_files:
            name_list.append(item['name'])
        video_name = None
        subtitle_name = None
        for file_name in name_list:
            if self.is_video_file(file_name):
                video_name, _ = os.path.splitext(file_name)
            else:
                subtitle_name = file_name
        if video_name is not None and subtitle_name is not None:
            self.rename_filename(moviepath + '/' + subtitle_name, video_name + '.chs.ass')
            logger.info(f'✅字幕命名完毕,新名字为：{video_name + ".chs.ass"}')

        else:
            logger.info('只有单个文件，不进行字幕命名')


def read_config(config_path):
    config = configparser.ConfigParser()
    with codecs.open(config_path, 'r', encoding='utf-8') as f:
        config.read_file(f)
    return config
def main():
    config = read_config(config_path)
    alist = ALIST(config)
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', default=None, help='to_named_path的路径')
    args = parser.parse_args()
    if args.path == None:
        local_strm_root_path = config['paths']['local_strm_root_path']
        to_named_path = config['paths']['to_named_path']
        alist.start_to_create_strm(to_named_path, local_strm_root_path)
    else:
        local_strm_root_path = config['paths']['local_strm_root_path']
        to_named_path = args.path
        alist.start_to_create_strm(to_named_path, local_strm_root_path)

if __name__ == '__main__':
    main()
    logger.info(f'✅strm已经全部生成！')
    # config = read_config('config/test_config.ini')
    # alist = ALIST(config)
    # alist.get_folder_files('/115_15TB/动漫New/海贼王')
    # pass









