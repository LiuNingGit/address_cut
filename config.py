"""
全局静态配置文件，方便统一管理和修改。
"""
import os


class GlobalVar:
    # 服务启动的配置变量
    # data_path = r'E:\project\poc\address_cut\data'
    data_path = os.path.join(os.getcwd(), 'data')


def get_data_path():
    return GlobalVar.data_path


