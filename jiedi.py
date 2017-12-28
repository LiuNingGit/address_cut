"""
根据隐马尔科夫模型，进行切分地址
其中隐层状态定义为：
    'pB':  # 省份的开始字
    'pM':  # 省份的中间字
    'pE':  # 省份的结尾字
    'cB':  # 市的开始字
    'cM':  # 市的中间字
    'cE':  # 市的结尾字
    'aB':  # 区的开始字
    'aM':  # 区的中间字
    'aE':  # 区的结尾字
    'dB':  # 详细地址的开始字
    'dM':  # 详细地址的中间字
    'dE':  # 详细地址的结尾字
"""
from common import load_cache, MIN_FLOAT
import config
import os
import pandas as pd
import numpy as np
import datetime


# 分词器
class Tokenizer(object):
    def __init__(self):
        try:
            self.start_p = load_cache(os.path.join(config.get_data_path(), 'start_p.p'))
            self.trans_p = load_cache(os.path.join(config.get_data_path(), 'trans_p.p'))
            self.emit_p = load_cache(os.path.join(config.get_data_path(), 'emit_p.p'))
            self.mini_d_emit_p = self.get_mini_emit_p('d')
            standard_address_library = pd.read_excel(os.path.join(config.get_data_path(), 'adress_area.xlsx'))
            self.standard_address_library = standard_address_library.fillna('')
            self.time = datetime.datetime.now()
            self.time_takes = {}
        except Exception:
            raise

    # 维特比算法求大概率路径
    def viterbi(self, address):
        length = len(address)
        V = []  # tabular
        path = {}
        temp_pro = {}
        for hidden_state, prop in self.start_p.items():
            temp_pro[hidden_state] = self.start_p[hidden_state] + self.get_emit_p(hidden_state, address[0])
            path[hidden_state] = [hidden_state]
        V.append(temp_pro)
        for i_c, character in enumerate(address[1:]):
            temp_pro = {}
            new_path = {}
            for hidden_state, _ in self.start_p.items():
                pre_hidden_state_pro = {pre_hidden_state: (pre_pro
                                                           + self.get_trans_p(pre_hidden_state, hidden_state)
                                                           + self.get_emit_p(hidden_state, character))
                                        for pre_hidden_state, pre_pro in V[i_c].items()}

                max_pre_hidden_state, max_pro = max(pre_hidden_state_pro.items(), key=lambda x: x[1])
                temp_pro[hidden_state] = max_pro
                new_path[hidden_state] = path[max_pre_hidden_state] + [hidden_state]
            V.append(temp_pro)
            path = new_path

        # 解析最大概率路径, 只从可能的最后一个字符状态进行解析
        (prob, state) = max((V[length - 1][y], y) for y, _ in self.start_p.items())
        self.note_time_takes('viterbi_time_takes', self.get_time_stamp())
        return prob, path[state]

    # 获取隐含状态到可见状态的发射概率
    def get_emit_p(self, hidden_state, visible_state):
        # 详细地址如果出现未登记词的处理
        if 'd' in hidden_state:
            # 对省、市、县等关键字进行过滤，防止出现在详细地址中
            if '省' in visible_state or '市' in visible_state or '县' in visible_state:
                return self.emit_p.get(hidden_state, {}).get(visible_state, MIN_FLOAT)
            else:
                return self.emit_p.get(hidden_state, {}).get(visible_state, self.mini_d_emit_p)
        # 省市区县出现未登记词的处理
        else:
            return self.emit_p.get(hidden_state, {}).get(visible_state, MIN_FLOAT)
        pass

    # 获取详细地址最小的发射概率
    def get_mini_emit_p(self, h_state_feature):
        mini_p = -MIN_FLOAT
        for h_state, v_states_pro in self.emit_p.items():
            if h_state_feature in h_state:
                for v_state, pro in v_states_pro.items():
                    mini_p = min(mini_p, pro)
        return mini_p

    # 获取前一隐含状态到下一隐含状态的转移概率
    def get_trans_p(self, pre_h_state, h_state):
        return self.trans_p.get(pre_h_state, {}).get(h_state, MIN_FLOAT)

    # 修正市区详细地址
    def revise_address_cut(self, pro, city, area, detailed):
        # 1、修正省市区地址
        list_addr = [pro, city, area, detailed]
        col_name = ['pro', 'city', 'area']
        revise_addr_list = ['', '', '', '']
        i = 0
        k = 0
        filter_df = self.standard_address_library
        while i < len(col_name) and k < len(col_name):
            add = list_addr[k]
            if add == '':
                k += 1
                continue
            while i < len(col_name):
                # 避免重复判断字符串是否被包含，优化匹配效率
                area_set = set(filter_df[col_name[i]].values)
                match_area_set = {a for a in area_set if add in a}
                # 筛选出符合条件的子地址库
                filter_temp = filter_df.loc[filter_df[col_name[i]].isin(match_area_set), :]
                if len(filter_temp) > 0:
                    revise_addr_list[i] = add
                    filter_df = filter_temp
                    i += 1
                    k += 1
                    break
                else:
                    i += 1
                    continue
        # 将剩余的值全作为详细地址
        revise_addr_list[3] = ''.join(list_addr[k:len(list_addr)])
        self.note_time_takes('revise_address_0_time_takes', self.get_time_stamp())

        # 2、补全省市区地址
        effective_index_arr = np.where([s != '' for s in revise_addr_list[0:3]])[0]
        max_effective_index = 0
        if len(effective_index_arr) > 0:
            max_effective_index = effective_index_arr[-1]
        if len(filter_df) > 0:
            for index, addr in enumerate(revise_addr_list):
                if addr == '' and index < max_effective_index:
                    revise_addr_list[index] = filter_df.iloc[0, :][col_name[index]]

        self.note_time_takes('revise_address_1_time_takes', self.get_time_stamp())
        return revise_addr_list[0], revise_addr_list[1], revise_addr_list[2], revise_addr_list[3]

    # 初始化耗时初始时刻和耗时记录
    def time_init(self):
        self.time = datetime.datetime.now()
        self.time_takes = {}

    # 计算初始时刻至今的耗时
    def get_time_stamp(self):
        time_temp = datetime.datetime.now()
        time_stamp = (time_temp - self.time).microseconds / 1000000
        self.time = time_temp
        return time_stamp

    # 记录时间段名称和耗时时间
    def note_time_takes(self, key, time_takes):
        self.time_takes[key] = time_takes


dt = Tokenizer()


# 对输入的地址进行切分
def cut(address):
    # 带切分地址必须大于一个字符
    if address is None or len(address) < 2:
        return '', '', '', '', 0, [], {}
    dt.time_init()
    p, max_path = dt.viterbi(address)
    pro = ''
    city = ''
    area = ''
    detailed = ''
    for i_s, state in enumerate(max_path):
        character = address[i_s]
        if 'p' in state:
            pro += character
        elif 'c' in state:
            city += character
        elif 'a' in state:
            area += character
        else:
            detailed += character

    # 通过字典修正输出
    r_pro, r_city, r_area, r_detailed = dt.revise_address_cut(pro, city, area, detailed)
    return r_pro, r_city, r_area, r_detailed, p, max_path, dt.time_takes


if __name__ == '__main__':
    # 读取execel批量测试
    # 读取一些切分地址后的样本
    address_sample = pd.read_excel(r'E:\project\poc\address_cut\data\df_test.xlsx')
    address_sample['pro_hmm'] = ''
    address_sample['city_hmm'] = ''
    address_sample['area_hmm'] = ''
    address_sample['detailed_hmm'] = ''
    address_sample['route_state_hmm'] = ''
    s_time = datetime.datetime.now()
    time_takes_total = {}
    for index, row in address_sample.iterrows():
        addr = row['address_'].strip().strip('\ufeff')
        pro, city, area, detailed, *route_state, time_takes = cut(addr)
        address_sample.loc[index, 'pro_hmm'] = pro
        address_sample.loc[index, 'city_hmm'] = city
        address_sample.loc[index, 'area_hmm'] = area
        address_sample.loc[index, 'detailed_hmm'] = detailed
        address_sample.loc[index, 'route_state_hmm'] = str(route_state)
        time_takes_total = {key: (time_takes_total.get(key, 0) + value) for key, value in time_takes.items()}

    e_time = datetime.datetime.now()
    times_total = (e_time - s_time).seconds
    print('总共{}条数据，共耗时:{}秒，平均每条{}秒。'.format(index+1, times_total, times_total/(index+1)))
    print({key: value for key, value in time_takes_total.items()})
    address_sample.to_excel(r'E:\project\poc\address_cut\data\df_test_hmm.xlsx')

    # adr = '青岛路6号  一楼厂房'
    # pro, city, area, detailed,  *_ = cut(adr)
    # print(pro)
    # print(city)
    # print(area)
    # print(detailed)


