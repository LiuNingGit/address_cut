"""
根据语料库，训练初始状体概率、状态转移概率、发射概率
"""
import pandas as pd
import numpy as np
from common import cal_log, save_cache
import os
import config


# # 定义状态的前置状态
# PrevStatus = {
#     'pB': [],  # 省份的开始字
#     'pM': ['pB'],  # 省份的中间字
#     'pE': ['pB', 'pM'],  # 省份的结尾字
#     'cB': ['pE'],  # 市的开始字
#     'cM': ['cB'],  # 市的中间字
#     'cE': ['cB', 'cM'],  # 市的结尾字
#     'aB': ['cE'],  # 区的开始字
#     'aM': ['aB'],  # 区的中间字
#     'aE': ['aB', 'aM'],  # 区的结尾字
#     'dB': ['aE'],  # 详细地址的开始字
#     'dM': ['dB'],  # 详细地址的中间字
#     'dE': ['dB', 'dM'],  # 详细地址的结尾字
# }


# 生成隐马尔科夫模型的训练概率
def build_porb():
    start_p, trans_p, emit_p = cal_prob()
    save_cache(start_p, os.path.join(config.get_data_path(), 'start_p.p'))
    save_cache(trans_p, os.path.join(config.get_data_path(), 'trans_p.p'))
    save_cache(emit_p, os.path.join(config.get_data_path(), 'emit_p.p'))


# 计算状态转移概率
def cal_prob():
    # 初始化
    trans_p = {}  # 状态转移概率
    emit_p = {}  # 发射概率

    # 读取省市区的标准名称
    address_standard = pd.read_table(r'E:\project\poc\address_cut\data\dict3.txt',
                                     header=None, names=['name', 'num', 'type'], delim_whitespace=True)
    # 读取一些切分地址后的样本
    address_sample = pd.read_excel(r'E:\project\poc\address_cut\data\df.xlsx')

    # 1、计算状态转移概率矩阵
    trans_p.setdefault('pB', {})['pE'],  trans_p.setdefault('pB', {})['pM'], \
        trans_p.setdefault('pM', {})['pM'], trans_p.setdefault('pM', {})['pE'] = \
        cal_trans_BE_BM_MM_ME(set(address_standard.loc[address_standard['type'] == 'prov', 'name'].values))

    trans_p.setdefault('cB', {})['cE'], trans_p.setdefault('cB', {})['cM'], \
        trans_p.setdefault('cM', {})['cM'], trans_p.setdefault('cM', {})['cE'] = \
        cal_trans_BE_BM_MM_ME(set(address_standard.loc[address_standard['type'] == 'city', 'name'].values))

    trans_p.setdefault('aB', {})['aE'], trans_p.setdefault('aB', {})['aM'], \
        trans_p.setdefault('aM', {})['aM'], trans_p.setdefault('aM', {})['aE'] = \
        cal_trans_BE_BM_MM_ME(set(address_standard.loc[address_standard['type'] == 'dist', 'name'].values))

    detailed_address_sample = get_detailed_address(address_sample)  # 详细地址样本库，后续需要完善和清洗筛选

    trans_p.setdefault('dB', {})['dE'], trans_p.setdefault('dB', {})['dM'], \
        trans_p.setdefault('dM', {})['dM'], trans_p.setdefault('dM', {})['dE'] = \
        cal_trans_BE_BM_MM_ME(set(detailed_address_sample))

    # 计算省市区详细地址之间的转移矩阵
    cal_trans_p_c_a_d(address_sample, trans_p)

    # 2、计算初始概率矩阵
    start_p = cal_start_p(address_sample)  # 初始状态概率

    # 3、计算发射概率矩阵
    emit_p['pB'], emit_p['pM'], emit_p['pE'] = \
        cal_emit_p(set(address_standard.loc[address_standard['type'] == 'prov', 'name'].values))

    emit_p['cB'], emit_p['cM'], emit_p['cE'] = \
        cal_emit_p(set(address_standard.loc[address_standard['type'] == 'city', 'name'].values))

    emit_p['aB'], emit_p['aM'], emit_p['aE'] = \
        cal_emit_p(set(address_standard.loc[address_standard['type'] == 'dist', 'name'].values))

    emit_p['dB'], emit_p['dM'], emit_p['dE'] = \
        cal_emit_p(set(detailed_address_sample))

    return start_p, trans_p, emit_p


# 计算发射概率矩阵
def cal_emit_p(str_set):
    str_list = list(str_set)
    stat_B = {}
    stat_M = {}
    stat_E = {}
    length = len(str_list)
    M_length = 0
    for str in str_list:
        str_len = len(str)
        for index, s in enumerate(str):
            if index == 0:
                stat_B[s] = stat_B.get(s, 0) + 1
            elif index < str_len - 1:
                stat_M[s] = stat_M.get(s, 0) + 1
                M_length += 1
            else:
                stat_E[s] = stat_E.get(s, 0) + 1
    B = {key: cal_log(value / length) for key, value in stat_B.items()}
    M = {key: cal_log(value / M_length) for key, value in stat_M.items()}
    E = {key: cal_log(value / length) for key, value in stat_E.items()}
    return B, M, E


# 根据地址样本，省市区详细地址之间的转移矩阵.....注：没有考虑没有详细地址的情况
def cal_trans_p_c_a_d(address_df, t_p):
    df_prov = address_df[address_df['prov'].isnull().values == False]
    df_prov_no_city = df_prov[df_prov['city'].isnull().values == True]
    df_prov_no_city_no_area = df_prov_no_city[df_prov_no_city['dist'].isnull().values == True]
    t_p.setdefault('pE', {})['cB'] = cal_log(1 - len(df_prov_no_city) / len(df_prov))
    t_p.setdefault('pE', {})['aB'] = cal_log((len(df_prov_no_city) - len(df_prov_no_city_no_area)) / len(df_prov))
    t_p.setdefault('pE', {})['dB'] = cal_log(len(df_prov_no_city_no_area) / len(df_prov))

    df_city = address_df[address_df['city'].isnull().values == False]
    df_city_no_area = df_city[df_city['dist'].isnull().values == True]
    t_p.setdefault('cE', {})['aB'] = cal_log(1 - len(df_city_no_area) / len(df_city))
    t_p.setdefault('cE', {})['dB'] = cal_log(len(df_city_no_area) / len(df_city))

    t_p.setdefault('aE', {})['dB'] = cal_log(1.0)


# 根据地址样本， 计算初始概率矩阵
def cal_start_p(address_df):
    length = len(address_df)
    df_prov_nan = address_df[address_df['prov'].isnull().values == True]
    length_pB = length - len(df_prov_nan)
    df_city_nan = df_prov_nan[df_prov_nan['city'].isnull().values == True]
    length_cB = len(df_prov_nan) - len(df_city_nan)
    df_area_nan = df_city_nan[df_city_nan['dist'].isnull().values == True]
    length_aB = len(df_city_nan) - len(df_area_nan)
    length_dB = len(df_area_nan)
    s_p = {'pB': cal_log(length_pB / length),  # 省份的开始字
           'pM': -3.14e+100,  # 省份的中间字
           'pE': -3.14e+100,  # 省份的结尾字
           'cB': cal_log(length_cB / length),  # 市的开始字
           'cM': -3.14e+100,  # 市的中间字
           'cE': -3.14e+100,  # 市的结尾字
           'aB': cal_log(length_aB / length),  # 区的开始字
           'aM': -3.14e+100,  # 区的中间字
           'aE': -3.14e+100,  # 区的结尾字
           'dB': cal_log(length_dB / length),  # 详细地址的开始字
           'dM': -3.14e+100,  # 详细地址的中间字
           'dE': -3.14e+100,  # 详细地址的结尾字
           }
    return s_p


# 获取样本数据中的详细地址
def get_detailed_address(address_df):
    detailed_address = []
    for index, row in address_df.iterrows():
        tmp = row['address_'].strip().strip('\ufeff')
        if row['prov'] is not None and row['prov'] is not np.nan:
            tmp = tmp.replace(row['prov'], '', 1)
        if row['city'] is not None and row['city'] is not np.nan:
            tmp = tmp.replace(row['city'], '', 1)
        if row['dist'] is not None and row['dist'] is not np.nan:
            tmp = tmp.replace(row['dist'], '', 1)
        detailed_address.append(tmp)
    return detailed_address


# 计算字符串数组中“开始字-->结束字”、“开始字-->中间字”、“中间字-->中间字”和“中间字-->结束字”的转移概率
def cal_trans_BE_BM_MM_ME(str_set):
    str_list = list(str_set)
    length = len(str_list)
    if length == 0:
        raise Exception('输入的集合为空')

    str_len_ori = np.array([len(str) for str in str_list])

    # 筛选出字数大于1的地名,进行计算
    str_len = str_len_ori[np.where(str_len_ori > 1)]
    # if sum(str_len < 2):
    #     raise Exception('含有单个字的省、市、区名称!')

    # “开始字-->结束字“的概率
    p_BE = sum(str_len == 2) / length
    # “开始字-->中间字”的概率
    p_BM = 1 - p_BE
    # “中间字 -->结束字”的概率
    p_ME = sum(str_len > 2) / sum(str_len - 2)
    # “中间字-->中间字”的概率
    p_MM = 1 - p_ME

    return cal_log(p_BE), cal_log(p_BM), cal_log(p_MM), cal_log(p_ME)


if __name__ == '__main__':
    build_porb()
    pass

