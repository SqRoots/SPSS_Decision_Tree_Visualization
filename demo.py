# 导入模块
from spss_tree_visualization import extract_and_visualize as et

# 波士顿房价（回归树）

# 导入测试 XML 文件
with open('./data_for_testing/boston_house_prices.xml', 'r', encoding='utf-8') as fo:
    xml_c = fo.read()

# 提取决策树信息，并设置标题和颜色
e = et.Extract(
    xml_data=xml_c,
    title='SPSS决策树可视化示例 - 波士顿房价',
    sub_title='回归树',
    color_0='#f1faee',  # 默认值 #f1faee
    color_1='#0077b6'   # 默认值 #0077b6
)

# 导出决策树信息至 JSON 文件
e.save_json('data_for_testing/boston_house_prices__output.json')
# 导出可视化结果至 HTML 文件
e.save_html('data_for_testing/boston_house_prices__output.html')
