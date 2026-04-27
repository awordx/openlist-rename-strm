import os
import re
import json
import sys
import time
from collections import defaultdict
from utils.log_utils import logger
from alist_file_tools import ALIST,read_config
import argparse
import configparser
# from folderwatcher import FolderWatcher
from utils.folderwatcher_emby import AUTO_refreash
# from utils.remove_garbage_files import remove_garbage_files
import math
from functools import reduce
from difflib import SequenceMatcher
# from utils.third_party_rename.trename import third_rename
import asyncio
import concurrent.futures
from utils.chatapi import ai_rename
from utils.chatapi import ai_rename_anime_movie
from utils.file_auto_copy import auto_copy
from utils.log_utils import config_path
from utils.config_verify import validate_config_from_file
class AlistRename():
    def __init__(self, config ,mapping_file='name_mapping.json'):
        # self.folder_path = folder_path
        self.file_size_dict = {}
        self.config = config
        self.mapping_file = mapping_file
        self.alist = ALIST(config)
        self.folder_watcher = AUTO_refreash(config)
        # 需要刷新的emby媒体库
        self.library_anime_new = config['emby_config']['library_anime_new']
        self.library_movie_new = config['emby_config']['library_movie_new']
        self.library_series = config['emby_config']['library_series']
        self.emby_refresh_status = {
                                     '动漫添加': ['动漫New', '添加'],
                                     '动漫删除': ['动漫New', '删除'],
                                     '电影添加': ['电影New', '添加'],
                                     '电影删除': ['电影New', '删除'],
                                    '剧集添加': ['剧集', '添加'],
                                    '剧集删除': ['剧集', '删除'],
                                   }
        self.local_strm_root_path = self.config['paths']['local_strm_root_path']
        self.anime_pattern = (r'(S\d+E\d+|'
                           r'OVA\d*|'
                           r'NCED\d*|'
                           r'Nced\d*|'
                           r'nced\d*|'
                           r'NCOP\d*|'
                           r'Ncop\d*|'
                           r'SP\d*|'
                           r'Sp\d*|'
                           r'OAD\d*|'
                           r'Oad\d*|'
                           r'sp\d*)')
        self.use_basename = True
        self.last_file_path = 'data/dict_files.json'
        self.is_use_asyncio = eval(config['user_config']['is_use_asyncio'])
        self.change = False
        self.offset = 0
        self.debugmodel = False
        self.useai = eval(config['user_config']['is_use_ai'])
        self.use_ai_title = eval(config['user_config']['use_ai_title'])
        self.ai_confidence = eval(config['user_config']['ai_confidence'])
        self.source_directory = config['copy_config']['source_directory'].split(',')
        self.target_directory = config['copy_config']['target_directory'].split(',')
        self.auto_copy = eval(config['copy_config']['auto_copy'])
        self.use_emby_refresh = eval(config['emby_config']['use_emby_refresh'])
        # self.use_thire_rename = os.getenv('use_thire_rename', False)
        # self.use_thire_rename = self.use_thire_rename.lower() in ['true', '1', 't', 'y', 'yes']
        # self.use_thire_rename = False


    def rename_files_with_offset(self, offset,folder_path):
        files = os.listdir(folder_path)
        files.sort()  # 按名称排序以保证顺序

        for filename in files:
            match = re.search(r'S(\d+)E([-+]?\d+)', filename)
            if match:
                season_number = int(match.group(1))
                episode_number = int(match.group(2))

                # 将集数加上偏移量
                new_episode_number = episode_number + offset
                new_name = f"S{season_number:02d}E{new_episode_number:02d}"
                new_filename = re.sub(r'S(\d+)E([-+]?\d+)', new_name, filename)

                old_file_path = os.path.join(folder_path, filename).replace('\\', '/')
                new_file_path = os.path.join(folder_path, new_filename).replace('\\', '/')

                os.rename(old_file_path, new_file_path)
                logger.info(f"Renamed: {old_file_path} to {new_file_path}")

    def remove_string_from_filenames(self, string_to_remove,folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename).replace('\\', '/')

            if not self.alist.is_file(file_path):
                continue

            new_filename = filename.replace(string_to_remove, '')
            new_file_path = os.path.join(folder_path, new_filename).replace('\\', '/')

            os.rename(file_path, new_file_path)
            logger.info(f"Renamed '{filename}' to '{new_filename}'")

    def find_true_episode_number(self, filename, episode_number_candidates,method1=False,method2=False,method3=False,keys_with_multiples = None):
        if method1 or method3 or method3:
            base_name, _ = os.path.splitext(filename)
            numbers = re.findall(r'\b\d+\.\d+|\d+', base_name)
            # #合并相同字符串
            # numbers = list(set(numbers))

            # 遍历 keys_with_multiples，去掉 numbers 中每个相同字符的一个实例
            for key in keys_with_multiples:
                if key in numbers:
                    numbers.remove(key)  # 只去掉第一个匹配的字符
            numbers = list(set(numbers))
            for number in numbers:
                if number in episode_number_candidates:
                    return number

    def save_name_mapping(self, name_map):
        with open(self.mapping_file, 'w') as file:
            json.dump(name_map, file)

    def load_name_mapping(self):
        with open(self.mapping_file, 'r') as file:
            return json.load(file)

    def format_episode_num(self, episode_num, offset):
        result = float(episode_num) + offset
        if result.is_integer():
            return f"{int(result):02d}"
        else:
            return f"{result:05.1f}"
    def rename_files_in_folder_t(self,parent_folderpath,last_data_path=None,t_rename=None):
        season_folders = self.alist.get_folder_files(parent_folderpath)
        for index, season_folder in enumerate(season_folders):
            if season_folder != 'Specials':
                folderpath = parent_folderpath + '/' + season_folder
                # if self.use_thire_rename:
                #     if self.third_rename(folderpath,season_folder,t_rename):
                #         continue#结束当前文件夹，开始下一个文件夹
                #     else:
                #         logger.info(f'三方命名失败')
                # #season_match = re.search(r'Season(\d+)', folderpath)
                season_match = re.search(r'(?:Season|S|s|season)(\d+)', folderpath, re.IGNORECASE)#兼容Season、season、S\s
                if season_match:
                    season_num = season_match.group(1).zfill(2)
                else:
                    logger.info("❌未找到合适的季编号，请确保文件夹名包含'Season'加数字")
                    return

                # offset = 0
                # offset_file_path = os.path.join(folderpath, 'offset.txt').replace('\\', '/')
                # if os.path.exists(offset_file_path):
                #     with open(offset_file_path, 'r') as offset_file:
                #         offset = int(offset_file.read().strip())
                offset = -self.offset
                files = self.alist.get_folder_files(folderpath,refresh=False)
                if files == None:
                    logger.info(f'❌文件夹:{folderpath},为空，开始退出')
                    continue
                files = [f for f in files]

                if len(files) == 1:
                    filename = files[0]
                    base_name, _ = os.path.splitext(filename)
                    episode_num = re.findall(r'\d+', base_name)
                    if episode_num:
                        episode_num = str(int(episode_num[0]) - offset).zfill(2)
                        new_filename = f"S{season_num}E{episode_num}{os.path.splitext(filename)[1]}"
                        old_file_path = os.path.join(folderpath, filename).replace('\\', '/')
                        # new_file_path = os.path.join(folderpath, new_filename).replace('\\', '/')
                        self.alist.rename_filename(old_file_path, new_filename)
                        logger.info(f"📝重命名 '{filename}' to '{new_filename}'")
                    return

                number_frequency = defaultdict(int)
                original_to_new_name_map = {}
                pattern = self.anime_pattern
                #统计数字出现频率
                for filename in files:
                    # file_path = os.path.join(folderpath, filename).replace('\\', '/')
                    # if self.alist.is_file(file_path):
                    #     continue
                    if re.search(pattern, filename, re.IGNORECASE):
                        continue
                    base_name, _ = os.path.splitext(filename)
                    # numbers = re.findall(r'\d+\.\d+|\d+', base_name)#可以提取小数
                    numbers = re.findall(r'\d+', base_name)#只能提取整数
                    for number in numbers:
                        number_frequency[number] += 1


                # 排除pattern，计算一共有多少个文件
                filtered_files = [file for file in files if not re.search(pattern, file, re.IGNORECASE)]
                len_files = len(filtered_files)

                #计算频率的最大公因数，应对一个视频两个字幕情况
                if number_frequency:
                    values = list(number_frequency.values())
                    def gcd(a, b):
                        return math.gcd(a, b)
                    result = reduce(gcd, values)
                else:
                    result = 1


                keys_with_multiples1 = [key for key, value in number_frequency.items() if
                                       value > 0 and value % len_files == 0]
                keys_with_multiples2 = [key for key, value in number_frequency.items() if
                                       (value-result) > 0 and (value-result) % len_files == 0]
                keys_with_multiples = keys_with_multiples1 + keys_with_multiples2
                if keys_with_multiples is [] or None:
                    logger.info(f'⚠️文件名称太乱，无法重命名，请确保除了集数数字，其他内容相同')
                    sys.exit()

                #去除所有文件相同数字
                for key in list(number_frequency.keys()):
                    while number_frequency[key] >= len_files:
                        number_frequency[key] -= len_files
                #剧集集数候选

                possible_episode_numbers = [number for number, freq in number_frequency.items() if freq > 0 ]
                for filename in files:
                    file_path = os.path.join(folderpath, filename).replace('\\', '/')
                    if re.search(pattern, filename, re.IGNORECASE):
                        logger.info(f'⚠️不在命名范围，或已命名，跳过：{filename}')
                        continue
                    episode_num = self.find_true_episode_number(filename, possible_episode_numbers,method1=True,keys_with_multiples=keys_with_multiples)
                    if episode_num:

                        episode_num = self.format_episode_num(episode_num, offset)
                        file_extension = os.path.splitext(filename)[1]
                        if self.use_basename:
                            base_name, _ = os.path.splitext(filename)
                            c = f"[S{season_num}E{episode_num}].{base_name}"
                        else:
                            c = f"S{season_num}E{episode_num}"
                        # if re.search(r'ass|srt|ssa|sub',file_extension,re.IGNORECASE):
                        #     new_filename = f"{c}{'.chs'+file_extension}"
                        # else:
                        #     new_filename = f"{c}{file_extension}"
                        new_filename = f"{c}{file_extension}"

                        original_to_new_name_map[filename] = new_filename
                        self.alist.rename_filename(file_path, new_filename)
                        logger.info(f"✅Renamed '{filename}' to '{new_filename}'")
                # self.save_name_mapping(original_to_new_name_map)
            else:
                logger.info('跳过Specials文件夹，不进行文件名命名')
            #对文件名实施追加更新
            self.series_files_update(last_data_path,parent_folderpath)
    async def async_rename_file(self, executor, file_path, new_filename):
        """异步执行重命名"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, self.alist.rename_filename, file_path, new_filename)
        logger.info(f"✅Renamed |{file_path}| to |{new_filename}|")

    async def process_files(self, folderpath, season_num, possible_episode_numbers, offset, keys_with_multiples):
        """异步批量处理文件重命名"""
        files = self.alist.get_folder_files(folderpath, refresh=False)
        if not files:
            logger.info(f'❌文件夹: {folderpath} 为空，退出')
            return

        original_to_new_name_map = {}
        pattern = self.anime_pattern

        tasks = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            if self.useai:
                ai_name_list = ai_rename(files)
            for index,filename in enumerate(files):
                file_path = os.path.join(folderpath, filename).replace('\\', '/')

                # 跳过不符合命名规则的文件
                if re.search(pattern, filename, re.IGNORECASE):
                    logger.info(f'⚠️ 不在命名范围，或已命名，跳过: {filename}')
                    continue
                if self.useai:
                    if ai_name_list[index] is None:
                        episode_num = self.find_true_episode_number(filename, possible_episode_numbers, method1=True,keys_with_multiples=keys_with_multiples)
                        logger.info(f'gpt命名结果：{ai_name_list[index]},可能错误，使用原始方法重命名结果{episode_num}')
                    else:
                        episode_num = ai_name_list[index]
                else:
                    episode_num = self.find_true_episode_number(filename, possible_episode_numbers, method1=True,
                                                            keys_with_multiples=keys_with_multiples)
                if episode_num:
                    episode_num = self.format_episode_num(episode_num, offset)
                    file_extension = os.path.splitext(filename)[1]

                    if self.use_basename:
                        base_name, _ = os.path.splitext(filename)
                        new_filename = f"[S{season_num}E{episode_num}].{base_name}{file_extension}"
                    else:
                        new_filename = f"S{season_num}E{episode_num}{file_extension}"

                    original_to_new_name_map[filename] = new_filename
                    tasks.append(self.async_rename_file(executor, file_path, new_filename))

            await asyncio.gather(*tasks)

    def rename_files_in_folder(self,parent_folderpath,last_data_path=None,t_rename=None):
        season_folders = self.alist.get_folder_files(parent_folderpath)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for index, season_folder in enumerate(season_folders):
            if season_folder != 'Specials':
                folderpath = parent_folderpath + '/' + season_folder
                # if self.use_thire_rename:
                #     if self.third_rename(folderpath,season_folder,t_rename):
                #         continue#结束当前文件夹，开始下一个文件夹
                #     else:
                #         logger.info(f'三方命名失败')
                # #season_match = re.search(r'Season(\d+)', folderpath)
                season_match = re.search(r'(?:Season|S|s|season)(\d+)', folderpath, re.IGNORECASE)#兼容Season、season、S\s
                if season_match:
                    season_num = season_match.group(1).zfill(2)
                else:
                    logger.info("❌未找到合适的季编号，请确保文件夹名包含'Season'加数字")
                    return

                # offset = 0
                # offset_file_path = os.path.join(folderpath, 'offset.txt').replace('\\', '/')
                # if os.path.exists(offset_file_path):
                #     with open(offset_file_path, 'r') as offset_file:
                #         offset = int(offset_file.read().strip())
                offset = -self.offset
                files = self.alist.get_folder_files(folderpath,refresh=False)
                if files == None:
                    logger.info(f'❌文件夹:{folderpath},为空，开始退出')
                    continue
                files = [f for f in files]

                if len(files) == 1:
                    filename = files[0]
                    base_name, _ = os.path.splitext(filename)
                    episode_num = re.findall(r'\d+', base_name)
                    if episode_num:
                        episode_num = str(int(episode_num[0]) - offset).zfill(2)
                        new_filename = f"S{season_num}E{episode_num}{os.path.splitext(filename)[1]}"
                        old_file_path = os.path.join(folderpath, filename).replace('\\', '/')
                        # new_file_path = os.path.join(folderpath, new_filename).replace('\\', '/')
                        self.alist.rename_filename(old_file_path, new_filename)
                        logger.info(f"📝重命名 '{filename}' to '{new_filename}'")
                    return

                number_frequency = defaultdict(int)
                original_to_new_name_map = {}
                pattern = self.anime_pattern
                #统计数字出现频率
                for filename in files:
                    # file_path = os.path.join(folderpath, filename).replace('\\', '/')
                    # if self.alist.is_file(file_path):
                    #     continue
                    if re.search(pattern, filename, re.IGNORECASE):
                        continue
                    base_name, _ = os.path.splitext(filename)
                    # numbers = re.findall(r'\d+\.\d+|\d+', base_name)#可以提取小数
                    numbers = re.findall(r'\d+', base_name)#只能提取整数
                    for number in numbers:
                        number_frequency[number] += 1


                # 排除pattern，计算一共有多少个文件
                filtered_files = [file for file in files if not re.search(pattern, file, re.IGNORECASE)]
                len_files = len(filtered_files)

                #计算频率的最大公因数，应对一个视频两个字幕情况
                if number_frequency:
                    values = list(number_frequency.values())
                    def gcd(a, b):
                        return math.gcd(a, b)
                    result = reduce(gcd, values)
                else:
                    result = 1


                keys_with_multiples1 = [key for key, value in number_frequency.items() if
                                       value > 0 and value % len_files == 0]
                keys_with_multiples2 = [key for key, value in number_frequency.items() if
                                       (value-result) > 0 and (value-result) % len_files == 0]
                keys_with_multiples = keys_with_multiples1 + keys_with_multiples2
                if keys_with_multiples is [] or None:
                    logger.info(f'⚠️文件名称太乱，无法重命名，请确保除了集数数字，其他内容相同')
                    sys.exit()

                #去除所有文件相同数字
                for key in list(number_frequency.keys()):
                    while number_frequency[key] >= len_files:
                        number_frequency[key] -= len_files
                #剧集集数候选

                possible_episode_numbers = [number for number, freq in number_frequency.items() if freq > 0 ]
                # **执行异步任务**
                async def main():
                    await self.process_files(folderpath, season_num, possible_episode_numbers, offset,
                                             keys_with_multiples)

                # 运行 `asyncio.run()` 并确保后续代码可以执行
                asyncio.run(main())
                # 这里的代码 **肯定会执行**
                self.series_files_update(last_data_path, parent_folderpath)


    def series_files_update_old(self,last_data_path,parent_folderpath):
        self.alist.get_folder_files(os.path.split(parent_folderpath)[0], refresh=True)  # 刷新电影的父目录，获取文件夹修改后的最新时间
        series_names_modified_time = self.alist.is_file(parent_folderpath, modified_time=True)
        series_names = os.path.basename(parent_folderpath)
        named_series = (series_names, series_names_modified_time)
        # 读取文件内容
        with open(last_data_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()  # 读取所有行
        # 过滤掉包含 series_names 的行
        filtered_lines = [line for line in lines if series_names not in line]
        # 写回文件，覆盖原文件
        with open(last_data_path, 'w', encoding='utf-8') as file:
            file.writelines(filtered_lines)  # 写入过滤后的行
        # 以追加模式打开文件
        if last_data_path is not None :#and index == len(season_folders) - 1:
            with open(last_data_path, 'a', encoding='utf-8') as file:
                # 将元组转换为字符串并写入文件
                file.write(','.join(named_series) + '\n')  # 元组元素用逗号分隔
    def series_files_update(self,last_data_path,parent_folderpath):
        partent_folder = os.path.split(parent_folderpath)[0]
        partent_folder_name = os.path.basename(partent_folder)
        self.alist.get_folder_files(partent_folder, refresh=True)  # 刷新电影的父目录，获取文件夹修改后的最新时间
        series_names_modified_time = self.alist.is_file(parent_folderpath, modified_time=True)
        series_names = os.path.basename(parent_folderpath)
        named_series = [series_names, series_names_modified_time]

        # 读取 JSON 文件内容
        with open(last_data_path, 'r', encoding='utf-8') as file:
            data = json.load(file)  # 加载 JSON 数据
        # 过滤掉包含 series_names 的行
        if partent_folder_name in data:
            # 过滤掉该目录下的电影名称
            data[partent_folder_name] = [movie for movie in data[partent_folder_name] if movie[0] != series_names]
            # 添加新的电影信息
            data[partent_folder_name].append(named_series)  # 添加新的电影字典
        # 写回文件，覆盖原文件
        with open(last_data_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)  # 写入更新后的 JSON 数据

    def movie_files_update_old(self,last_data_path,movie_folder_path):
        self.alist.get_folder_files(os.path.split(movie_folder_path)[0],refresh=True)#刷新电影的父目录，获取修改后的最新时间
        movie_modified_time = self.alist.is_file(movie_folder_path, modified_time=True)
        movie_names = os.path.basename(movie_folder_path)
        named_movies = (movie_names, movie_modified_time)
        # 读取文件内容
        with open(last_data_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()  # 读取所有行
        # 过滤掉包含 series_names 的行
        filtered_lines = [line for line in lines if movie_names not in line]
        # 写回文件，覆盖原文件
        with open(last_data_path, 'w', encoding='utf-8') as file:
            file.writelines(filtered_lines)  # 写入过滤后的行
        # 以追加模式打开文件
        with open(last_data_path, 'a', encoding='utf-8') as file:
            # 将元组转换为字符串并写入文件
            file.write(','.join(named_movies) + '\n')  # 元组元素用逗号分隔
    def movie_files_update(self,last_data_path,movie_folder_path):
        partent_folder = os.path.split(movie_folder_path)[0]
        partent_folder_name = os.path.basename(partent_folder)
        self.alist.get_folder_files(partent_folder,refresh=True)#刷新电影的父目录，获取修改后的最新时间
        movie_modified_time = self.alist.is_file(movie_folder_path, modified_time=True)
        movie_names = os.path.basename(movie_folder_path)
        named_movies = [movie_names, movie_modified_time]
        # 读取 JSON 文件内容
        with open(last_data_path, 'r', encoding='utf-8') as file:
            data = json.load(file)  # 加载 JSON 数据
        # 过滤掉包含 series_names 的行

        if partent_folder_name in data:
            # 过滤掉该目录下的电影名称
            data[partent_folder_name] = [movie for movie in data[partent_folder_name] if movie[0] != movie_names]
            # 添加新的电影信息
            data[partent_folder_name].append(named_movies)  # 添加新的电影字典
        # 写回文件，覆盖原文件
        with open(last_data_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)  # 写入更新后的 JSON 数据
    def movie_files_deleted(self,last_data_path,movie_folder_path):
        for folder_path in movie_folder_path:
            partent_folder = os.path.split(folder_path)[0]
            partent_folder_name = os.path.basename(partent_folder)
            movie_names = os.path.basename(folder_path)
            with open(last_data_path, 'r', encoding='utf-8') as file:
                data = json.load(file)  # 加载 JSON 数据
            if partent_folder_name in data:
                # 过滤掉该目录下的电影名称
                data[partent_folder_name] = [movie for movie in data[partent_folder_name] if movie[0] != movie_names]
            # 写回文件，覆盖原文件
            with open(last_data_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)  # 写入更新后的 JSON 数据
    def movie_files_deleted_old(self,last_data_path,movie_folder_path):
        for path in movie_folder_path:
            movie_names = os.path.basename(path)
            # 读取文件内容
            with open(last_data_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()  # 读取所有行
            # 过滤掉包含 series_names 的行
            filtered_lines = [line for line in lines if movie_names not in line]
            # 写回文件，覆盖原文件
            with open(last_data_path, 'w', encoding='utf-8') as file:
                file.writelines(filtered_lines)  # 写入过滤后的行
    def anime_files_deleted_old(self,last_data_path,anime_folder_path):
        for path in anime_folder_path:
            movie_names = os.path.basename(path)
            # 读取文件内容
            with open(last_data_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()  # 读取所有行
            # 过滤掉包含 series_names 的行
            filtered_lines = [line for line in lines if movie_names not in line]
            # 写回文件，覆盖原文件
            with open(last_data_path, 'w', encoding='utf-8') as file:
                file.writelines(filtered_lines)  # 写入过滤后的行

    def anime_files_deleted(self, last_data_path, anime_folder_path):
        for folder_path in anime_folder_path:
            partent_folder = os.path.split(folder_path)[0]
            partent_folder_name = os.path.basename(partent_folder)
            anime_name = os.path.basename(folder_path)
            # 读取 JSON 文件内容
            with open(last_data_path, 'r', encoding='utf-8') as file:
                data = json.load(file)  # 加载 JSON 数据

            if partent_folder_name in data:
                # 过滤掉该目录下的电影名称
                data[partent_folder_name] = [anime for anime in data[partent_folder_name] if anime[0] != anime_name]
                # 添加新的电影信息
            # 将更新后的数据写回 JSON 文件
            with open(last_data_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)  # 写入更新后的 JSON 数据



    def restore_original_filenames(self,folder_path):
        name_map = self.load_name_mapping()
        for original_name, new_name in name_map.items():
            original_path = os.path.join(folder_path, original_name).replace('\\', '/')
            new_path = os.path.join(folder_path, new_name).replace('\\', '/')
            if os.path.exists(new_path):
                os.rename(new_path, original_path)
                logger.info(f"✅Restored '{new_name}' to '{original_name}'")
    def file_arrangement_t(self,folder_path):
        folders = self.alist.get_folder_files(folder_path,refresh=False)
        for folder in folders:
            # files = self.alist.get_folder_files(folder_path+'/'+folder)
            files, all_files = self.alist.get_folder_files(folder_path+'/'+folder, need_content=True)
            if files == None:
                logger.info(f'❌文件夹:{folder},为空，开始退出')
                continue
            common_video_formats = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', 'rmvb']
            common_subtitle_formats = ['.srt', '.ass', '.ass.ass', '.sub', '.vtt']
            # 合并所有有效格式
            valid_formats = common_video_formats + common_subtitle_formats
            video_items = all_files['data']['content']
            video_files = [
                file for file in video_items
                if any(file["name"].lower().endswith(ext) for ext in self.alist.video_extensions)
            ]
            #找到小于20m的垃圾视频
            videos_under_20mb = list(filter(lambda x: x["size"] < 20 * 1024 * 1024, video_files))
            for file in files:
                new_name = file
                if not any(new_name.lower().endswith(ext) for ext in valid_formats):
                    # 如果文件不以常见格式结尾，则删除文件
                    file_path = os.path.join(folder_path+'/'+folder, file).replace('\\', '/')
                    self.alist.delete_file(file_path,single_name=file)
            #如果错误文件的比例小于0.3
            if videos_under_20mb is not [] and len(videos_under_20mb)/len(files) <= 0.3:
                for file in videos_under_20mb:
                    if not re.search(self.anime_pattern, file['name'], re.IGNORECASE):
                        logger.info(f"🗑️删除垃圾视频：{file['name']}")
                        self.alist.delete_file(folder_path+'/'+folder+'/'+file['name'],single_name=file['name'])
                        time.sleep(0.3)
            else:
                pass
    async def delete_file_async(self, file_path, single_name):
        # 这里是异步删除文件的逻辑
        await asyncio.to_thread(self.alist.delete_file, file_path, single_name)
    async def file_arrangement(self,folder_path):
        # if 'Season' not in os.path.basename(folder_path):
        #     parent_files = self.alist.get_folder_files(folder_path)
        #     # 检查是否存在任何以 'Season' 开头的文件夹
        #     existing_season_folders = [f for f in self.alist.get_folder_files(folder_path) if f.startswith('Season')]
        #     if not existing_season_folders:  # 如果没有找到以 'Season' 开头的文件夹
        #         season_folder = os.path.join(folder_path, 'Season1').replace('\\', '/')
        #         if not self.alist.get_folder_files(season_folder):  # 检查是否存在 Season1 文件夹
        #             logger.info("开始创建Season1文件夹")
        #             self.alist.create_new_folder(season_folder)
        #             # 移动文件到 Season1 文件夹
        #             for filename in parent_files:
        #                 self.alist.move_file(folder_path, season_folder, filename)
        #     else:
        #         logger.info("存在季节文件夹：{}".format(existing_season_folders))
        folders = self.alist.get_folder_files(folder_path,refresh=False)
        for folder in folders:
            # files = self.alist.get_folder_files(folder_path+'/'+folder)
            files, all_files = self.alist.get_folder_files(folder_path+'/'+folder, need_content=True)
            if files == None:
                logger.info(f'❌文件夹:{folder},为空，开始退出')
                continue
            common_video_formats = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', 'rmvb']
            common_subtitle_formats = ['.srt', '.ass', '.ass.ass', '.sub', '.vtt']
            # 合并所有有效格式
            valid_formats = common_video_formats + common_subtitle_formats
            video_items = all_files['data']['content']
            video_files = [
                file for file in video_items
                if any(file["name"].lower().endswith(ext) for ext in self.alist.video_extensions)
            ]
            #找到小于20m的垃圾视频
            videos_under_20mb = list(filter(lambda x: x["size"] < 20 * 1024 * 1024, video_files))
            delete_tasks = []  # 用于存储删除任务
            for file in files:
                new_name = file
                if not any(new_name.lower().endswith(ext) for ext in valid_formats):
                    file_path = os.path.join(folder_path + '/' + folder, file).replace('\\', '/')
                    delete_tasks.append(self.delete_file_async(file_path, file))  # 收集删除任务
                # 执行所有删除任务
            await asyncio.gather(*delete_tasks)
            #如果错误文件的比例小于0.3
            if videos_under_20mb and len(videos_under_20mb) / len(files) <= 0.3:
                for file in videos_under_20mb:
                    if not re.search(self.anime_pattern, file['name'], re.IGNORECASE):
                        logger.info(f"🗑️删除垃圾视频：{file['name']}")
                        await self.delete_file_async(folder_path + '/' + folder + '/' + file['name'], file['name'])
                        # await asyncio.sleep(0.3)  # 可选的延迟
            else:
                pass
    def is_newfile_add(self,new_folders_dict):
        logger.info('🔍 开始检测文件变化')
        if new_folders_dict['new_anime_files']:
            self.change = True
            logger.info("✨ 发现新剧集")
            logger.info("📺 新剧集列表:")
            logger.info("─────────────────────────────")
            for anime in new_folders_dict["new_anime_files"]:
                logger.info(f"• {anime}")
            logger.info("─────────────────────────────")
        if new_folders_dict['new_movie_files']:
            self.change = True
            logger.info("✨ 发现新电影")
            logger.info("🎬 新电影列表:")
            logger.info("─────────────────────────────")
            for movie in list(new_folders_dict["new_movie_files"]):
                logger.info(f"• {movie}")
            logger.info("─────────────────────────────")
        # if new_folders_dict['new_series_files']:
        #     self.change = True
        #     logger.info("✨ 发现新剧集 ✨")
        #     logger.info("📺 新剧集列表:")
        #     logger.info("─────────────────────────────")
        #     for series in new_folders_dict["new_series_files"]:
        #         logger.info(f"• {series}")
        #     logger.info("─────────────────────────────")
        if new_folders_dict['deleted_anime_files'] and new_folders_dict['deleted_anime_files'] != {''}:
            self.change = True
            logger.info("🗑️ 发现删除剧集 📺")
            logger.info("─────────────────────────────")
            for anime in new_folders_dict["deleted_anime_files"]:
                logger.info(f"• {anime}")
            logger.info("─────────────────────────────")
        # if new_folders_dict['deleted_series_files'] and new_folders_dict['deleted_series_files']!= {''}:
        #     self.change = True
        #     logger.info("🗑️ 发现删除剧集 📺")
        #     logger.info("─────────────────────────────")
        #     for series in new_folders_dict["deleted_series_files"]:
        #         logger.info(f"• {series}")
        #     logger.info("─────────────────────────────")
        if new_folders_dict['deleted_movie_files'] and new_folders_dict['deleted_movie_files']!= {''}:
            self.change = True
            logger.info("🗑️ 发现删除电影 🎬")
            logger.info("─────────────────────────────")
            for movie in list(new_folders_dict["deleted_movie_files"]):
                logger.info(f"• {movie}")
            logger.info("─────────────────────────────")
        if not self.change:
            logger.info(f'🔔 媒体库未发生变化')

    def folder_watch(self):
        new_folders_dict = self.folder_watcher.monitor_folder()
        return new_folders_dict
    def get_file_size(self,folder_path):
        def add_to_limited_dict(d, key, value, max_len=5):
            """
            向字典 d 添加 key:value，如果超过 max_len 条目，从头开始删除最早添加的
            """
            d[key] = value
            while len(d) > max_len:
                # popitem(last=False) 弹出最早插入的元素（需要 OrderedDict）
                d.pop(next(iter(d)))  # 删除字典中第一个元素

        if os.path.exists('data/temp.json') and os.path.getsize('data/temp.json') > 0:
            with open('data/temp.json', 'r', encoding='utf-8') as f:
                try:
                    temp_data = json.load(f)  # 直接读取整个 JSON 为字典
                except json.JSONDecodeError:
                    temp_data = {}  # 文件有内容但不是合法 JSON，也返回空字典
        else:
            temp_data = {}
        movie_path = folder_path['new_movie_folders_with_path']
        series_path = folder_path['new_anime_folders_with_path']
        movie_names = {}
        series_names = {}
        for path in movie_path:
            folder_name = os.path.basename(path.rstrip("/\\"))
            _,allfiles = self.alist.get_folder_files(path,refresh=False,need_content=True)
            contents = allfiles.get('data', {}).get('content', [])
            if contents:
                # 找到 size 最大的那个 dict
                max_file = max(contents, key=lambda x: x.get('size', 0))
                max_size = round(max_file['size'] / (1024 * 1024 * 1024), 2)
                add_to_limited_dict(temp_data, folder_name, max_size)
            else:
                print("没有内容")
                movie_names[folder_name] = '-'

        for path in series_path:
            folder_name = os.path.basename(path.rstrip("/\\"))
            # series_names[folder_name] = '-'
            add_to_limited_dict(temp_data, folder_name, '-')
        with open('data/temp.json', 'w', encoding='utf-8') as f:
            json.dump(temp_data, f, ensure_ascii=False, indent=4)
    def refresh_emby(self):
        if new_folders_dict['new_anime_files']:
            # logger.info(f'4.1发现新动漫🎉: {new_folders_dict["new_anime_files"]}')
            logger.info("✨ 开始生成剧集strm & 下载字幕 ✨")
            self.alist.start_to_create_strm(to_named_paths=new_folders_dict['new_anime_folders_with_path'],
                                            local_strm_root_path=self.local_strm_root_path)
            if alist_rename.use_emby_refresh:
                self.folder_watcher.emby_refresh(self.library_anime_new, new_folders_dict['new_anime_files'],self.emby_refresh_status['剧集添加'])
            #潜在bug，不会自动刷新emby剧集目录
        else:
            pass
            # logger.info("4.1没有发现新动漫🎨")

        if new_folders_dict['new_movie_files']:
            # logger.info(f'4.2发现新电影就🎇: {list(new_folders_dict["new_movie_files"])}')
            for index, new_movie_path in enumerate(new_folders_dict['new_movie_folders_with_path']) :
                if not self.alist.local_is_a_file(new_movie_path):
                    # self.alist.movie_rename(new_movie_path)

                    if alist_rename.useai and alist_rename.use_ai_title:
                        try:
                            new_path, confidence = ai_rename_anime_movie(new_movie_path)
                            if confidence >= alist_rename.ai_confidence:
                                named_folder = os.path.basename(new_path)
                                alist_rename.alist.rename_filename(new_movie_path, named_folder)
                                alist_rename.alist.get_folder_files(os.path.dirname(new_path), refresh=True)
                                new_movie_path = new_path
                                new_folders_dict['new_movie_files'][index] = named_folder
                                new_folders_dict['new_movie_folders_with_path'][index] = new_path
                            else:
                                logger.warning(f"AI置信度 {confidence:.2f} < {alist_rename.ai_confidence}, 跳过命名")
                        except Exception as e:
                            logger.error(f"AI命名失败: {e}")
                    else:
                        logger.info("未启用 AI 命名标题，保持原始标题")

                    # new_path, confidence = ai_rename_anime_movie(new_movie_path)
                    # if alist_rename.use_ai_title and confidence > alist_rename.ai_confidence:
                    #     named_folder = os.path.basename(new_path)
                    #     alist_rename.alist.rename_filename(new_movie_path, named_folder)
                    #     alist_rename.alist.get_folder_files(os.path.dirname(new_path),refresh=True)
                    #     new_movie_path = new_path
                    #     new_folders_dict['new_movie_files'][index] = named_folder
                    #     new_folders_dict['new_movie_folders_with_path'][index] = new_path
                    # else:
                    #     logger.info(f"置信度小于{alist_rename.ai_confidence} 或者未开启ai对标题命名,不对标题进行命名")
                    arrangement_and_rename_movies(alist_rename, moviepath=new_movie_path)
                else:
                    create_single_movie_strm(alist_rename,new_movie_path)
                    alist_rename.movie_files_update(alist_rename.last_file_path, new_movie_path)
                    pass
            logger.info("✨ 开始生成电影strm & 下载字幕 ✨")
            self.alist.start_to_create_strm(to_named_paths=new_folders_dict['new_movie_folders_with_path'],
                                            local_strm_root_path=self.local_strm_root_path)
            if alist_rename.use_emby_refresh:
                self.folder_watcher.emby_refresh(self.library_movie_new, new_folders_dict['new_movie_files'],self.emby_refresh_status['电影添加'])
        else:
            pass
            # logger.info("4.2没有发现新电影🎞")

        # if new_folders_dict['new_series_files']:
        #     # logger.info(f'4.3发现新剧集🎊: {new_folders_dict["new_series_files"]}')
        #     logger.info("✨ 开始生成剧集strm & 下载字幕 ✨")
        #     self.alist.start_to_create_strm(to_named_paths=new_folders_dict['new_series_folders_with_path'],
        #                                     local_strm_root_path=self.local_strm_root_path)
        #     self.folder_watcher.emby_refresh(self.library_series, new_folders_dict['new_series_files'],
        #                                      self.emby_refresh_status['剧集添加'])
        # else:
        #     pass
        #     # logger.info("4.3没有发现新剧集🛒")

        if new_folders_dict['deleted_anime_files'] and new_folders_dict['deleted_anime_files'] != {''}:
            # logger.info(f'🗑️4.4发现删除的动漫: {new_folders_dict["deleted_anime_files"]}')
            #从data的txt文件中删除已经删除的动漫
            self.anime_files_deleted(self.last_file_path,new_folders_dict["deleted_anime_folders_with_path"])
            self.alist.delete_local_strm_folders(new_folders_dict['deleted_anime_folders_with_path'],self.local_strm_root_path)
            if alist_rename.use_emby_refresh:
                self.folder_watcher.emby_refresh(self.library_anime_new, new_folders_dict['deleted_anime_files'],self.emby_refresh_status['剧集删除'])
        else:
            pass
            # logger.info("4.4没有动漫删除🎬")

        # if new_folders_dict['deleted_series_files'] and new_folders_dict['deleted_series_files']!= {''}:
        #     # logger.info(f'🗑️4.5发现删除的剧集: {new_folders_dict["deleted_series_files"]}')
        #     # 删除已经删除的剧集，从txt中删除
        #     self.anime_files_deleted(alist_rename.last_series_file_path,
        #                              new_folders_dict["deleted_series_folders_with_path"])
        #     self.alist.delete_local_strm_folders(new_folders_dict['deleted_series_folders_with_path'],self.local_strm_root_path)
        #     self.folder_watcher.emby_refresh(self.library_series, new_folders_dict['deleted_series_files'],self.emby_refresh_status['剧集删除'])
        # else:
        #     pass
        #     # logger.info("4.5没有剧集删除🎬")

        if new_folders_dict['deleted_movie_files'] and new_folders_dict['deleted_movie_files']!= {''}:
            # logger.info(f'🗑️4.6发现删除的电影: {list(new_folders_dict["deleted_movie_files"])}')
            #删除已经删除的电影，从txt中删除
            self.movie_files_deleted(alist_rename.last_file_path,new_folders_dict["deleted_movie_folders_with_path"])
            self.alist.delete_local_strm_folders(new_folders_dict['deleted_movie_folders_with_path'],self.local_strm_root_path)
            if alist_rename.use_emby_refresh:
                self.folder_watcher.emby_refresh(self.library_movie_new, new_folders_dict['deleted_movie_files'],self.emby_refresh_status['电影删除'])
        else:
            pass
            # logger.info("4.6没有电影删除🎬")
async def move_file_async(alist_rename, new_folder, season_folder, filename):
    """异步移动文件"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, alist_rename.alist.move_file, new_folder, season_folder, filename)

async def folder_arrangement(alist_rename,new_folder):
    not_check = False

    parent_files = alist_rename.alist.get_folder_files(new_folder)
    if parent_files == None or parent_files == False:
        logger.info(f'❌文件夹：{new_folder}为空')
        # sys.exit()

    #如果存在季度文件夹，则进行文件夹整理
    # 检查是否存在任何以 'Season' 开头的文件夹
    pattern = r'^[Ss]eason\s*[0-9]+$|^[Ss][0-9]+$|^[Ss]pecials$|^[sS]pecials$'
    existing_season_folders = [folder for folder in parent_files if re.match(pattern, folder)]
    # existing_season_folders = [f for f in alist_rename.alist.get_folder_files(new_folder, refresh=False) if f.startswith('Season')]
    if existing_season_folders:
        season_names, _ = alist_rename.alist.get_folder_files(new_folder, refresh=False, need_content=True)
        to_delete_folders = [item for item in season_names if item not in existing_season_folders]
        # if existing_season_folders ==['Season1']:
        #     logger.info('⚠️可能上次未完全移动文件，接着移动剩余文件')
        #     for folder in to_delete_folders:
        #         alist_rename.alist.move_file(new_folder, os.path.join(new_folder, 'Season1').replace('\\', '/'), folder)
        # else:
        for folder in to_delete_folders:
            alist_rename.alist.delete_file(new_folder+'/'+folder,single_name=folder)

    if not existing_season_folders:  # 如果没有找到以 'Season' 开头的文件夹
        season_folder = os.path.join(new_folder, 'Season1').replace('\\', '/')
        if not alist_rename.alist.get_folder_files(season_folder):  # 检查是否存在 Season1 文件夹
            logger.info("🛠️开始创建Season1文件夹")
            alist_rename.alist.create_new_folder(season_folder)
            # 移动文件到 Season1 文件夹
            # for filename in parent_files:
            #     alist_rename.alist.move_file(new_folder, season_folder, filename)
            # 异步移动文件到 Season1 文件夹
            tasks = [move_file_async(alist_rename, new_folder, season_folder, filename) for filename in parent_files]
            await asyncio.gather(*tasks)  # 等待所有异步任务完成
            return not_check  # 在此分支中返回not_check
    else:
        logger.info(f"📍存在季节文件夹")
        logger.info("─────────────────────────────")
        for folders in existing_season_folders:
            logger.info(f"• {folders}")
        logger.info("─────────────────────────────")



    #只有一个季时检测not_check文件是否存在
    if existing_season_folders and len(season_names) == 1:
        names, video_files = alist_rename.alist.get_folder_files(new_folder + '/' + season_names[0], refresh=False,
                                                                 need_content=True)
        if names ==None:
            logger.warning(f'⚠️文件夹{new_folder + "/" + season_names[0]}为空,跳过处理')
            return False
        else:
            video_dict = video_files['data']['content']
            for video in video_dict:
                if isinstance(video, dict) and video.get('name') == 'not_check':
                    not_check = True
                    break  #
            return not_check

    return not_check
def folder_arrangement_t(alist_rename,new_folder):
    not_check = False

    parent_files = alist_rename.alist.get_folder_files(new_folder)
    if parent_files == None or parent_files == False:
        logger.info(f'❌文件夹：{new_folder}为空，开始退出')
        sys.exit()

    #如果存在季度文件夹，则进行文件夹整理
    # 检查是否存在任何以 'Season' 开头的文件夹
    pattern = r'^[Ss]eason\s*[0-9]+$|^[Ss][0-9]+$|^[Ss]pecials$|^[sS]pecials$'
    existing_season_folders = [folder for folder in parent_files if re.match(pattern, folder)]
    # existing_season_folders = [f for f in alist_rename.alist.get_folder_files(new_folder, refresh=False) if f.startswith('Season')]
    if existing_season_folders:
        season_names, _ = alist_rename.alist.get_folder_files(new_folder, refresh=False, need_content=True)
        to_delete_folders = [item for item in season_names if item not in existing_season_folders]
        # if existing_season_folders == ['Season1']:
        #     logger.info('⚠️可能上次未完全移动文件，接着移动剩余文件')
        #     for folder in to_delete_folders:
        #         alist_rename.alist.move_file(new_folder, os.path.join(new_folder, 'Season1').replace('\\', '/'), folder)
        # else:
        for folder in to_delete_folders:
            alist_rename.alist.delete_file(new_folder + '/' + folder, single_name=folder)

    if not existing_season_folders:  # 如果没有找到以 'Season' 开头的文件夹
        season_folder = os.path.join(new_folder, 'Season1').replace('\\', '/')
        if not alist_rename.alist.get_folder_files(season_folder):  # 检查是否存在 Season1 文件夹
            logger.info("🛠️开始创建Season1文件夹")
            alist_rename.alist.create_new_folder(season_folder)
            # 移动文件到 Season1 文件夹
            for filename in parent_files:
                alist_rename.alist.move_file(new_folder, season_folder, filename)
    else:
        logger.info(f"📍存在季节文件夹")
        logger.info("─────────────────────────────")
        for folders in existing_season_folders:
            logger.info(f"• {folders}")
        logger.info("─────────────────────────────")



    #只有一个季时检测not_check文件是否存在
    if existing_season_folders and len(season_names) == 1:
        names, video_files = alist_rename.alist.get_folder_files(new_folder + '/' + season_names[0], refresh=False,
                                                                 need_content=True)
        if names ==None:
            logger.warning(f'⚠️文件夹{new_folder + "/" + season_names[0]}为空,跳过处理')
            return False
        else:
            video_dict = video_files['data']['content']
            for video in video_dict:
                if isinstance(video, dict) and video.get('name') == 'not_check':
                    not_check = True
            return not_check

    else:
        return False
def create_single_movie_strm(alist_rename,single_movie_path):
    movie_alist_path = os.path.split(single_movie_path)[0]
    single_movie_strm_path = alist_rename.local_strm_root_path+movie_alist_path
    movie_name = os.path.basename(single_movie_path)
    os.makedirs(single_movie_strm_path, exist_ok=True)
    alist_rename.alist.create_strm(single_movie_strm_path,
                                   movie_name,
                                   strm_content=alist_rename.alist.encode_chinese_only(
                                alist_rename.alist.alist_url + '/d'+movie_alist_path+'/'+movie_name))
def arrangement_and_rename_movies(alist_rename,moviepath):
    alist_rename.alist.movie_rename(moviepath)
    alist_rename.movie_files_update(alist_rename.last_file_path,moviepath)
    # alist_rename.alist.start_to_create_strm(to_named_paths=moviepath,
    #                                         local_strm_root_path=alist_rename.local_strm_root_path)
# 使用示例
if __name__ == '__main__':
    # config = read_config('/volume1/docker/alist_rename/config.ini')#nas配置文件
    config = read_config(config_path)#windows配置文件
    try:
        validate_config_from_file(config_path)
    except:
        sys.exit(1)
    alist_rename = AlistRename(config)
    # 创建解析器
    parser = argparse.ArgumentParser(description='选择一个库类型。')
    # 添加 --library 参数，默认值为 None
    parser.add_argument('--library', choices=['animenew', 'movienew', 'anime', 'movie', 'series'],
                        default=None, help='选择库类型: animenew, movienew, anime, movie, 或 series (默认为 None)')
    parser.add_argument('--tvpath',default=None)
    parser.add_argument('--moviepath',default=None)
    parser.add_argument('--offset', type=int,default=0)
    args = parser.parse_args()
    alist_rename.offset = args.offset
    if alist_rename.auto_copy:
        auto_copy(alist_rename)
    # 监测新文件夹
    if not alist_rename.debugmodel and args.tvpath is None:#仅在正常模式下监控文件，如果tvpath存在则不监控文件
        new_folders_dict = alist_rename.folder_watch()
        alist_rename.get_file_size(new_folders_dict)
        alist_rename.is_newfile_add(new_folders_dict)
        new_anime_folders_with_path = new_folders_dict['new_anime_folders_with_path']
        # new_series_folders_with_path = new_folders_dict['new_series_folders_with_path']
    if args.tvpath is not None:
        folders_with_paths = [[args.tvpath]]
        # folders_with_lastfiles = [alist_rename.last_file_path, alist_rename.last_file_path]
    elif args.moviepath is not None:
        refresh_movie_folder_name = os.path.basename(args.moviepath)
        if not alist_rename.alist.local_is_a_file(args.moviepath):
            alist_rename.alist.movie_rename(args.moviepath)
            alist_rename.alist.start_to_create_strm(to_named_paths=args.moviepath,
                                            local_strm_root_path=alist_rename.local_strm_root_path)
        else:
            create_single_movie_strm(alist_rename, args.moviepath)
        # alist_rename.folder_watcher.emby_refresh(alist_rename.library_movie_new, [refresh_movie_folder_name],
        #                                  alist_rename.emby_refresh_status['电影添加'])
        # logger.info(f'✅{refresh_movie_folder_name}刷新执行完毕，程序开始退出')
        sys.exit()
    else:
        folders_with_paths = [new_anime_folders_with_path]
        #监测新文件夹
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        pending_not_check_indexes = []
        for index, folders_with_path in enumerate(folders_with_paths) :
            if folders_with_path:
                for index2 ,new_folder in enumerate(folders_with_path):
                    # logger.info(f'✨检测到新文件:[{os.path.basename(new_folder)}]，开始重命名')
                    ###检测文件夹是否含有not_check,以及整理文件夹
                    # not_check = folder_arrangement_t(alist_rename,new_folder)
                    if alist_rename.useai and alist_rename.use_ai_title:
                        try:
                            new_path, confidence = ai_rename_anime_movie(new_folder)
                            if confidence >= alist_rename.ai_confidence:
                                named_folder = os.path.basename(new_path)
                                alist_rename.alist.rename_filename(new_folder, named_folder)
                                alist_rename.alist.get_folder_files(os.path.dirname(new_path), refresh=True)
                                new_folder = new_path
                                new_folders_dict['new_anime_files'][index2] = named_folder
                                new_folders_dict['new_anime_folders_with_path'][index2] = new_path
                            else:
                                logger.warning(f"AI置信度 {confidence:.2f} < {alist_rename.ai_confidence}, 跳过命名")
                        except Exception as e:
                            logger.error(f"AI命名失败: {e}")
                    else:
                        logger.info("未启用 AI 命名标题，保持原始标题")


                    # if alist_rename.use_ai_title:
                    #     new_path, confidence = ai_rename_anime_movie(new_folder)
                    # if alist_rename.use_ai_title and confidence > alist_rename.ai_confidence:
                    #     named_folder = os.path.basename(new_path)
                    #     alist_rename.alist.rename_filename(new_folder, named_folder)
                    #     alist_rename.alist.get_folder_files(os.path.dirname(new_path),refresh=True)
                    #     new_folder = new_path
                    #     new_folders_dict['new_anime_files'][index2] = named_folder
                    #     new_folders_dict['new_anime_folders_with_path'][index2] = new_path
                    # else:
                    #     logger.warning(f"置信度小于 {alist_rename.ai_confidence} 或者未开启ai对标题命名,不对标题进行命名")
                    if alist_rename.is_use_asyncio:
                        logger.info(f'🔧使用异步操作进行文件夹整理')
                        not_check = loop.run_until_complete(folder_arrangement(alist_rename, new_folder))
                    else:
                        not_check = folder_arrangement_t(alist_rename, new_folder)
                    if not_check:
                        logger.info(f'⚠️not_check:{new_folder}，不进行命名以及生成strm')
                        pending_not_check_indexes.append(index2)
                        alist_rename.series_files_update(last_data_path=alist_rename.last_file_path, parent_folderpath=new_folder)
                        continue
                    ###检测文件夹是否含有not_check,以及整理文件夹
                    # logger.info(f'2.已取消文件名剔除操作')

                    ##文件名整理操作
                    logger.info(f'🔧 正在进行文件整理 🔧')
                    if alist_rename.is_use_asyncio:
                        logger.info(f'🔧使用异步操作进行文件整理')
                        loop.run_until_complete(alist_rename.file_arrangement(new_folder))
                    else:
                        alist_rename.file_arrangement_t(new_folder)
                    logger.info(f'✅ 文件整理完成 ✅')
                    ##文件名整理操作

                    logger.info(f'🔄 正在进行文件重命名 🔄')
                    if alist_rename.is_use_asyncio:
                        logger.info(f'🔧使用异步操作进行文件重命名')
                        alist_rename.rename_files_in_folder(new_folder,last_data_path=alist_rename.last_file_path)
                    else:
                        alist_rename.rename_files_in_folder_t(new_folder,last_data_path=alist_rename.last_file_path)
                    logger.info('✅ 文件重命名完成 ✅')
            else:
                pass
        if pending_not_check_indexes:
            for remove_index in sorted(set(pending_not_check_indexes), reverse=True):
                if remove_index < len(new_folders_dict['new_anime_files']):
                    del new_folders_dict['new_anime_files'][remove_index]
                if remove_index < len(new_folders_dict['new_anime_folders_with_path']):
                    del new_folders_dict['new_anime_folders_with_path'][remove_index]
        if args.tvpath is not None:
            alist_rename.alist.start_to_create_strm(args.tvpath, alist_rename.local_strm_root_path)
        else:
            alist_rename.refresh_emby()
    finally:
        loop.close()
    #最后更新下时间
    # alist_rename.folder_watch()




