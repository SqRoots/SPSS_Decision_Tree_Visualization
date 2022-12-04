# 从 SPSS 的决策树模型XML文件中提取信息


from bs4 import BeautifulSoup
import json
from .visualize import plot

operator = {
    'surrogate': 'surrogate',
    'isMissing': '=缺失',
    'greaterThan': '>',
    'lessOrEqual': '<=',
    'equal': '=',
    'and': '&',
    'or': '|'
}


def accumulate(table: list) -> list:
    """
    统计绘图数据中的子类别的高度等
    :param table:
    :return:
    """
    _top = 0
    _rs = []
    for t in table:
        _height = t.get('ratio_in_node', 0)
        _top += _height
        _rs.append(
            {
                'y_class': t.get('value'),
                'sub_bottom': _top - _height,
                'sub_top': _top,
                'sub_height': _height,
                'sub_cnt': t.get('count', 0)
            }
        )
    return _rs


def node_predicate(compound_predicate) -> str:
    """
    解析拆分条件，返回字符串
    :param compound_predicate: 复合谓语
    :return: [字符串] 可读拆分条件
    """
    if compound_predicate:
        _cp = compound_predicate[0].select_one('CompoundPredicate')
        _c1 = operator.get(_cp.get('booleanOperator'), 'operator?1')
        _sp = _cp.select('SimplePredicate')
        _c2_field = [_.get('field', '') for _ in _sp]
        _c2_o = [operator.get(_.get('operator', ''), 'operator?2') for _ in _sp]
        _c2_value = [_.get('value', '') for _ in _sp]

        # 分类变量
        if _c2_o[0] == '=':
            return _c2_field[0] + '∈{' + '|'.join(_c2_value) + '}'
        # 连续变量，1个判断
        if len(_c2_o) == 1:
            if _c2_o[0] == '>':
                return _c2_field[0] + '∈({x},+∞)'.format(x=_c2_value[0])
            if _c2_o[0] == '<=':
                return _c2_field[0] + '∈(-∞,{x}]'.format(x=_c2_value[0])
        # 连续变量，2个判断
        if len(_c2_o) == 2:
            return _c2_field[0] + '∈({x1},{x2}]'.format(x1=min(_c2_value), x2=max(_c2_value))
        return '程序有问题'
    return ''


def parse_one_node(node, all_count):
    """
    解析一个节点，返回节点信息+子节点列表
    :param node: bs4.element.Tag
    :param all_count: 样本总规模
    :return: 节点信息 dict
    """
    _extension = [_ for _ in node.children if _.name == 'Extension']
    if _extension:
        _reg_info = _extension[0].select_one('X-Node>X-RegInfo').attrs if _extension[0].select_one(
            'X-Node>X-RegInfo') else {}
        _node_stats = _extension[0].select_one('X-Node>X-NodeStats').attrs if _extension[0].select_one(
            'X-Node>X-NodeStats') else {}
    else:
        _reg_info = {}
        _node_stats = {}
    # y 分类或分区间统计结果
    _score_distribution = [{
        'value': _.get('value'),
        'count': int(_.get('recordCount', '0')),
        'ratio_in_node': int(_.get('recordCount', '0')) / int(node.get('recordCount', '0'))
    } for _ in node.children if _.name == 'ScoreDistribution']

    _score_distribution_binary = [_.get('ratio_in_node') for _ in _score_distribution if _.get('value') == '1'][0] \
        if len(_score_distribution) == 2 and len([_ for _ in _score_distribution if _.get('value') == '1']) == 1 else 0
    return {
        'id': node.get('id'),
        'cid_list': [_.get('id', '') for _ in node.children if _.name == 'Node'],
        'reg_info': {k: float(v) for k, v in _reg_info.items()},  # 回归树节点信息
        'node_stats': _node_stats,  # 回归树节点信息
        'node_count': int(node.get('recordCount', '0')),
        'node_ratio_in_all': int(node.get('recordCount', '0')) / all_count,
        'node_score': node.get('score', '0'),
        'condition': node_predicate([_ for _ in node.children if _.name == 'CompoundPredicate']),
        'score_distribution': _score_distribution,
        'node_ob_list': [_ for _ in node.children if _.name == 'Node'],

        'y_binary': _score_distribution_binary,  # 二分类：灰度值。也可以使用多分类
        'y_multi': accumulate(_score_distribution)  # 多分类（列表，值：value, count, ratio_in_node）
    }


class Extract:
    """
    从 SPSS 的决策树模型XML文件中提取信息
    """

    def __init__(self, xml_data: str,
                 title: str = '请输入标题', sub_title: str = '请输入副标题',
                 color_0: str = '#f1faee', color_1: str = '#0077b6'):
        self.xml_soup = BeautifulSoup(xml_data, 'xml')
        self.spss_info = {}  # SPSS版本号
        self.tree_model = {}  # 模型信息
        self.data_field = {}  # 字段信息
        self.node_dict = {}  # 节点信息
        self.root_node = self.xml_soup.select_one('Node')  # 根节点
        self.y_name = ''
        self.y_class_dict = {}
        self.y_class_cnt = 2
        self.left_dict = {}  # 仅用于统计绘图时的 left 值
        # 输出
        self.output_tree_info = {}  # 树信息
        self.output_tree_html = ''  # 可视化树 HTML

        # SPSS版本号
        _version = self.xml_soup.select_one('Header>Application')
        self.spss_info = {'spss_version': _version.get('version') if _version else ''}
        # 模型信息
        _tree_model = self.xml_soup.select_one('TreeModel')
        self.tree_model = {
            'algorithm': _tree_model.get('algorithmName') if _tree_model else '',
            'function': _tree_model.get('functionName') if _tree_model else '',
            'field_usage_type': {_.get('name'): _.get('usageType') for _ in
                                 _tree_model.select('MiningSchema>MiningField')}
        }
        # 字段信息
        for d in self.xml_soup.select('DataDictionary>DataField'):
            _temp = d.attrs
            _temp.update({'value_list': [_.get('value') for _ in d.select('Value')]})
            self.data_field.update({d.get('name'): _temp})

        # 预测字段分类信息
        _y = [k for k, v in self.tree_model.get('field_usage_type').items() if v == 'predicted'][0]
        self.y_name = _y
        self.y_class_dict = {v: i for i, v in enumerate(
            [_.get('value') for _ in self.root_node.select('Node[id="0"]>ScoreDistribution')])}
        self.y_class_cnt = len(self.y_class_dict)

        # 节点信息
        self.sample_count = int(self.root_node.get('recordCount', '1'))
        self.parse_node(node=self.root_node, pid='', pid_list=[], condition='', level=0)

        # 可视化HTML
        self.output_tree_html = plot(
            data=self.output_tree_info,
            title=title,
            sub_title=sub_title,
            color_0=color_0,
            color_1=color_1
        )

    def parse_node(self, node, pid: str, pid_list: list, condition: str, level: int = 0) -> None:
        """
        递归
        :param node:        节点
        :param pid:         父节点
        :param pid_list:   全部父节点
        :param condition: 全部条件
        :param level:     树深度
        :return:          无返回值
        """
        _temp = parse_one_node(node, self.sample_count)
        _id = _temp.get('id')
        _width = _temp.get('node_ratio_in_all')
        _sub_bottom = 0
        _pid_left = self.node_dict.get(pid, {'plot_info': {'left_position': 0}}).get('plot_info').get('left_position',
                                                                                                      0)
        self.left_dict.update({pid: self.left_dict.get(pid, _pid_left) + _width})
        self.node_dict.update(
            {
                _id: {
                    'id': _id,
                    'level': level,
                    'pid': pid,
                    'pid_list': pid_list,
                    'cid_list': _temp.get('cid_list'),
                    'reg_info': _temp.get('reg_info'),  # 回归树：节点信息
                    'node_stats': _temp.get('node_stats'),
                    'node_count': _temp.get('node_count'),
                    'node_ratio_in_all': _width,
                    'node_score': _temp.get('node_score'),
                    'score_distribution': _temp.get('score_distribution'),
                    # 绘图数据
                    'plot_info': {
                        'is_classification': 1 if self.tree_model.get('functionName') == 'classification' else 0,
                        'bottom': level,
                        'left_position': self.left_dict.get(pid, 0) - _width,
                        'right_position': self.left_dict.get(pid, 0),
                        'width': _width,
                        'y_binary': _temp.get('y_binary'),  # 二分类，灰度值，已经归一化。也可以使用多分类
                        'y_multi': _temp.get('y_multi'),  # 多分类（列表，值：value, count, ratio_in_node）
                        'y_reg': _temp.get('reg_info'),  # 连续：灰度值，未做归一化处理（mean，stdDev）
                        'condition': _temp.get('condition', ''),
                        'all_condition': (condition + '【' + _temp.get('condition') + '】').replace('】【',
                                                                                                  '】&【') if _temp.get(
                            'condition') else condition
                    }
                }
            }
        )
        for c_node in _temp.get('node_ob_list'):
            self.parse_node(node=c_node,
                            pid=_id,
                            pid_list=pid_list + [_id],
                            condition=condition + '【' + _temp.get('condition') + '】' if _temp.get(
                                'condition') else condition,
                            level=level + 1)
        self.output_tree_info = {
            'spss_info': self.spss_info,
            'tree_info': self.tree_model,
            'y_name': self.y_name,
            'y_class_cnt': self.y_class_cnt,
            'y_class_dict': self.y_class_dict,
            'sample_cnt': self.sample_count,
            'node_info': self.node_dict
        }

    def save_json(self, save_path: str) -> None:
        with open(save_path, 'w', encoding='utf-8') as fo:
            fo.write(json.dumps(self.output_tree_info, sort_keys=False, indent=4, ensure_ascii=False))

    def save_html(self, save_path: str) -> None:
        with open(save_path, 'w', encoding='utf-8') as fo:
            fo.write(self.output_tree_html)
