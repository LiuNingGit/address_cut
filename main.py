"""
切地址的脚本文件
对于输入的字符串，需要切词前清洗，如：.strip().strip('\ufeff')
"""
import jiedi

# 地址示例
adr = '安徽省阜阳市颍州区阜阳师范学院西湖校区100号'

# 调用地址切分库的cut方法对地址进行切分
# 使用前需要修改
pro, city, area, detailed,  *_ = jiedi.cut(adr)
print(pro)
print(city)
print(area)
print(detailed)



