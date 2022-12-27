import json
import os


def plot(
        data: dict,
        title: str = '请输入标题',
        sub_title: str = '请输入副标题',
        color_0: str = '#f1faee',
        color_1: str = '#1d3557'
) -> str:
    """
    决策树可视化
    :param data: 从 SPSS 导出的 XML 文件经过解析后的 json 文件
    :param title: 标题
    :param sub_title: 副标题
    :param color_0: 最小值对应颜色，一般为浅色
    :param color_1: 最大值对应颜色，一般为深色
    :return: 返回值 HTML 字符串 + 剪切板或文件
    """

    # 根据结果分类数量选择模板
    with open(os.path.join(os.path.split(os.path.realpath(__file__))[0], 'template.html'), 'r', encoding='utf-8') as fo:
        _template = fo.read()

    # 对于二分类结果调整顺序（按 $.plot_info.y_binary 排序）
    if data.get('y_class_cnt') == 2:
        # 层数
        _level = 1
        # 用于存储排序后的节点信息
        _node_info = {'0': data.get('node_info').get('0')}
        while True:
            # 按层取节点列表
            _node_list = [(k, v) for k, v in data.get('node_info').items() if v.get('level') == _level]
            if len(_node_list) == 0:
                break
            # 层内 pid 列表
            _pid_list = set([_[1].get('pid') for _ in _node_list])
            # 遍历 pid
            for pid in list(_pid_list):
                _same_pid_node_list = [_ for _ in _node_list if _[1].get('pid') == pid]
                _same_pid_node_list.sort(key=lambda x: x[1].get('plot_info').get('y_binary'))
                _same_pid_node_list[0][1]['plot_info']['left_position'] = _node_info.get(pid).get('plot_info').get('left_position')
                _node_info.update({
                    _same_pid_node_list[0][0]: _same_pid_node_list[0][1]
                })
                # 遍历 pid 对应子节点列表
                for i in range(1, len(_same_pid_node_list)):
                    _same_pid_node_list[i][1]['plot_info']['left_position'] = _same_pid_node_list[i - 1][1]['plot_info']['left_position'] + _same_pid_node_list[i - 1][1]['plot_info']['width']
                    # 更新 _node_info
                    _node_info.update({
                        _same_pid_node_list[i][0]: _same_pid_node_list[i][1]
                    })
            _level += 1

    # 压缩 JSON 数据为字符串
    _data = {}
    for k, v in data['node_info'].items():
        _data.update({
            k: {
                'level': v.get('level'),
                'all_condition': v.get('plot_info').get('all_condition'),
                'width': v.get('plot_info').get('width'),
                'left_position': v.get('plot_info').get('left_position'),
                'y_multi': [{
                    'y_class': _.get('y_class'),
                    'sub_height': _.get('sub_height'),
                    'sub_top': _.get('sub_top')
                } for _ in v.get('plot_info').get('y_multi')]
            }
        })
    _data = json.dumps(_data, sort_keys=False, indent=None, ensure_ascii=False)
    _tree_info = json.dumps(
        {
            'spss_info': data.get('spss_info'),
            'tree_info': data.get('tree_info'),
            'y_name': data.get('y_name'),
            'y_class_cnt': data.get('y_class_cnt'),
            'y_class_dict': data.get('y_class_dict')
        }, sort_keys=False, indent=None, ensure_ascii=False
    )
    _html = _template.replace('{{title}}', title)
    _html = _html.replace('{{sub_title}}', sub_title)
    _html = _html.replace('{{color_0}}', color_0)
    _html = _html.replace('{{color_1}}', color_1)
    _html = _html.replace('{{tree_info}}', _tree_info)
    _html = _html.replace('{{data}}', _data)

    # 返回 HTML
    return _html
