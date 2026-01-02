import configparser
from utils.log_utils import logger
import sys
import os
import traceback

def validate_config_from_file(file_path: str) -> bool:
    if not os.path.exists(file_path):
        logger.error(f"\n\n错误: 配置文件 '{file_path}' 不存在。")
        raise FileNotFoundError(f"错误: 配置文件 '{file_path}' 不存在。")

    try:
        # 1. 先用 configparser 做基础解析，用于后续的类型检查
        config = configparser.ConfigParser()
        config.read(file_path, encoding='utf-8')

        # 2. 读取文件的原始行，用于进行严格的格式校验
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()


        boolean_keys = {
            'use_library', 'is_use_ai', 'use_ai_title', 'is_use_asyncio',
            'restart_update', 'auto_copy'
        }
        integer_keys = {'flask_port', 'ai_confidence'}
        allowed_empty_keys = {'to_named_path'}


        # 对于这些键，我们只检查尾部是否有非法字符，而不是整个值
        keys_allowing_spaces_in_value = {
            'cron', 'library', 'movies', 'series', 'refresh_folder'
        }

        # logger.info(f"开始对配置进行校验: '{file_path}'...")

        # 3. 【核心校验】遍历原始行，检查格式
        for line_num, line in enumerate(raw_lines, 1):
            cleaned_line = line.strip()
            # 跳过空行、纯注释行和节头
            if not cleaned_line or cleaned_line.startswith((';', '#', '[')):
                continue

            if '=' in cleaned_line:
                key_part, value_part = cleaned_line.split('=', 1)
                key_name = key_part.strip()

                # 根据键名选择不同的校验策略
                if key_name in keys_allowing_spaces_in_value:
                    # **宽松策略**：只检查值的尾部空格后是否还有内容
                    if value_part.rstrip() != value_part:
                        logger.error(f"\n\n校验失败 (在config.ini第 {line_num} 行): 键 '{key_name}' 的值末尾的空格后不能有注释等其他字符。")
                        raise ValueError(
                            f"校验失败 (在文件第 {line_num} 行): 键 '{key_name}' 的值末尾的空格后不能有注释等其他字符。"
                        )
                else:
                    # **严格策略**：检查值的后面是否有任何多余的内容
                    # .strip() 会移除前后的空格，.split() 会按内部的空格/制表符分割
                    value_components = value_part.strip().split()

                    # 如果分割后的组件超过1个（允许0个，即值为空），说明值后面有其他东西
                    if len(value_components) > 1:
                        logger.error(f"\n\n校验失败 (在config.ini第 {line_num} 行): 键 '{key_name}' 的值 ('{value_components[0]}') "
                            f"后面不允许有内联注释或多余字符，但检测到了 '{' '.join(value_components[1:])}'。")
                        raise ValueError(
                            f"校验失败 (在文件第 {line_num} 行): 键 '{key_name}' 的值 ('{value_components[0]}') "
                            f"后面不允许有内联注释或多余字符，但检测到了 '{' '.join(value_components[1:])}'。"
                        )

        # 4. 遍历解析后的值，检查类型（布尔、整数）和空值
        for section in config.sections():
            for key, value in config.items(section):
                if not value and key not in allowed_empty_keys:
                    logger.error(f"\n\n在节 '[{section}]' 中, 键 '{key}' 的值为空。")

                    raise ValueError(
                        f"在节 '[{section}]' 中, 键 '{key}' 的值为空。"
                    )
                if not value: continue

                if key in boolean_keys:
                    if value not in ['True', 'False']:
                        logger.error(f"\n\n类型校验失败: 在节 '[{section}]' 中, 键 '{key}' 的值必须是 'True' 或 'False', 但现在是 '{value}'。")
                        raise ValueError(
                            f"类型校验失败: 在节 '[{section}]' 中, 键 '{key}' 的值必须是 'True' 或 'False', 但现在是 '{value}'。"
                        )

                if key in integer_keys:
                    if not value.isdigit():
                        logger.error(f"\n\n类型校验失败: 在节 '[{section}]' 中, 键 '{key}' 的值必须是一个纯数字, 但现在是 '{value}'。")
                        raise ValueError(
                            f"类型校验失败: 在节 '[{section}]' 中, 键 '{key}' 的值必须是一个纯数字, 但现在是 '{value}'。"
                        )

        # logger.info(f"配置文件 '{file_path}' 校验成功！格式正确。")
        return True

    except Exception :
        pass




if __name__ == "__main__":
    try:
        validate_config_from_file('../config/config_test.ini')
    except (ValueError, FileNotFoundError, configparser.Error) as e:
        logger.error(f"Configuration check failed: {e}")
