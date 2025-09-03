# try:
#     from loguru import logger
# except:
#     # 兼容无loguru模块的环境，例如docker和群晖
#     class logger:
#         def info(s):
#             print(f'| INFO   | {s}')
#
#         def warning(s):
#             print(f'| WARNING| {s}')
from datetime import datetime
config_path = 'config/config.ini'
# config_path = r'K:\git_code\openlist-rename-strm\config\config_test.ini'
try:
    from loguru import logger
except ImportError:
    class Logger:
        # def __init__(self, log_file='../data/实时日志.log'):#windowsLujing
        def __init__(self, log_file='/usr/local/data/实时日志.log'):
            self.log_file = log_file

        def _write_log(self, level, message):
            log_message = f'|{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}|{level}| {message}'
            print(log_message)  # 输出到控制台
            with open(self.log_file, 'a') as f:  # 追加写入文件
                f.write(log_message + '\n')

        def info(self, message):
            self._write_log('INFO', message)

        def warning(self, message):
            self._write_log('WARNING', message)

        def error(self, message):
            self._write_log('ERROR', message)

    logger = Logger()

if __name__ == '__main__':
    logger.info('hello')
    logger.warning('this is a warning')
    logger.error('this is an error')
