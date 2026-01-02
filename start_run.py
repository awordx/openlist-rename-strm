import time

from alist_rename import read_config
from utils.folderwatcher_emby import AUTO_refreash
from utils.log_utils import logger
import sys
from utils.log_utils import config_path
import os
from utils.config_verify import validate_config_from_file
import configparser
if __name__ == '__main__':
    art = r'''          _   _         _                                                                            _                      
   __ _  | | (_)  ___  | |_           _ __    ___   _ __     __ _   _ __ ___     ___           ___  | |_   _ __   _ __ ___  
  / _` | | | | | / __| | __|  _____  | '__|  / _ \ | '_ \   / _` | | '_ ` _ \   / _ \  _____  / __| | __| | '__| | '_ ` _ \ 
 | (_| | | | | | \__ \ | |_  |_____| | |    |  __/ | | | | | (_| | | | | | | | |  __/ |_____| \__ \ | |_  | |    | | | | | |
  \__,_| |_| |_| |___/  \__|         |_|     \___| |_| |_|  \__,_| |_| |_| |_|  \___|         |___/  \__| |_|    |_| |_| |_|
                                                                                                                            '''
    print(art)
    # try:
    #     validate_config_from_file(config_path)
    # except (ValueError, FileNotFoundError, configparser.Error) as e:
    #     raise ValueError(f"Configuration check failed: {e}")
    config = read_config(config_path)  # windows配置文件
    restart_update = eval(config['user_config']['restart_update'])
    time.sleep(1)
    logger.info(f'项目地址：https://github.com/awordx/openlist-rename-strm')
    # restart_update = os.getenv('restart_update', True)
    # restart_update = restart_update.lower() in ['true', '1', 't', 'y', 'yes']
    # restart_update = True
    if restart_update:
        logger.info(f'程序正在启动中...')
        logger.info(f'程序启动完成')
        logger.info(f'程序刷新端口监控在5050端口')
        logger.info(f'正在更新当前data文件为最新网盘文件')
        refresh = AUTO_refreash(config)
        try:
            _ = refresh.monitor_folder(need_all_filechanges=True)
        except Exception as e:
            logger.info(f'发生错误，程序退出运行,请检查配置文件是否有问题')
            sys.exit()
        logger.info(f'data文件已更新为最新网盘文件')
        logger.info(f'访问：http://192.168.x.x:5050/stream即可对新增文件进行重命名')
        logger.info(f'如果想对旧的文件进行重命名，请删除data相应文件内的剧集名称（不要删除txt文档），再次访问刷新端口即可刷新')
    else:
        logger.info(f'程序正在启动中...')
        logger.info(f'程序启动完成')
        logger.info(f'程序刷新端口监控在5050端口')
        logger.info(f'不更新当前data文件')
        logger.info(f'访问：http://192.168.x.x:5050/stream即可对新增文件进行重命名')
        logger.info(
            f'如果想对旧的文件进行重命名，请删除data相应文件内的剧集名称（不要删除txt文档），再次访问刷新端口即可刷新')
