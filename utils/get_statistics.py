from alist_file_tools import read_config
from utils.log_utils import config_path

import os
import json
def count_items_by_folders(data: dict, folder_names: list):
    """
    统计每个文件夹名在 data 中的子条目数量
    """
    result = {}
    for name in folder_names:
        result[name] = len(data.get(name, []))
    return result
def stats():
    with open("data/dict_files.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    config = read_config(config_path)
    movies = config['alistconfig']['movies']
    series = config['alistconfig']['series']

    movie_folders = [
        os.path.basename(path.rstrip('/'))
        for path in movies.split(',')
        if path.strip()
    ]
    series_folders = [
        os.path.basename(path.rstrip('/'))
        for path in series.split(',')
        if path.strip()
    ]

    movie_count = count_items_by_folders(data, movie_folders)
    series_count = count_items_by_folders(data, series_folders)
    return movie_count, series_count
if __name__ == '__main__':
    stats()
