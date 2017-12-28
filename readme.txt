   此工具是基于hmm，对中国地址进行切分，抽取出省、市、区、详细地址四部分。（以后可以扩展至街道部分）
并通过地址标准库，对地址切分后的结果进行了修正和补全。

示例（main.py中的代码）：

import jiedi

# 地址示例
adr = '安徽省阜阳市颍州区阜阳师范学院西湖校区100号'

# 调用地址切分库的cut方法对地址进行切分
pro, city, area, detailed,  *_ = jiedi.cut(adr)

# 输出：安徽省  阜阳市 颍州区 阜阳师范学院西湖校区100号
print（pro, city, area, detailed）


