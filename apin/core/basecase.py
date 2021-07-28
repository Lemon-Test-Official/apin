# Author:柠檬班-木森
# E-mail:musen_nmb@qq.com
import os
import yaml
import json
import unittest
from functools import wraps
from apin.core.dataParser import DataParser
from apin.core.initEvn import BaseEnv, func_tools, ENV


class GenerateTest(type):
    """生成用例的类"""

    def __new__(cls, name, bases, namespace, *args, **kwargs):

        if name in ('BaseTestCase', 'HttpCase'):
            return super().__new__(cls, name, bases, namespace)
        else:
            # -------------------生成用例---------------------
            # Case外的类属性中，是否有需要动态执行的函数
            for k, v in list(namespace.items()):
                if k not in ['Cases', "extract", "verification"]:
                    # 解析数据中的变量
                    v = DataParser.parser_func(namespace.get('env'), v)
                    v = DataParser.parser_variable(namespace.get('env'), v)
                    namespace[k] = v
                if k == 'env':
                    _v = BaseEnv('env')
                    _v.update(v)
                    namespace[k] = _v
            test_cls = super().__new__(cls, name, bases, namespace)
            func = getattr(test_cls, "perform")
            datas = cls.__handle_datas(namespace.get('Cases'))
            for index, case_data in enumerate(datas):
                # 生成用例名称，
                new_test_name = cls.__create_test_name(index, case_data, test_cls)
                # 生成用例描述
                if isinstance(case_data, dict) and case_data.get("title"):
                    test_desc = case_data.get("title")
                elif isinstance(case_data, dict) and case_data.get("desc"):
                    test_desc = case_data.get("desc")
                elif hasattr(case_data, 'title'):
                    test_desc = case_data.title
                else:
                    test_desc = func.__doc__
                func2 = cls.__update_func(new_test_name, case_data, test_desc, func)
                setattr(test_cls, new_test_name, func2)
            return test_cls

    @classmethod
    def __create_test_name(cls, index, case_data, test_cls):
        interface = case_data.get('interface') or getattr(test_cls, 'interface')
        if index + 1 < 10:
            test_name = 'test' + "_0" + str(index + 1) + '_' + interface.strip('/').replace('/', '_')
        else:
            test_name = 'test' + "_" + str(index + 1) + '_' + interface.strip('/').replace('/', '_')
        return test_name

    @classmethod
    def __update_func(cls, new_func_name, params, test_desc, func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(self, params, *args, **kwargs)

        wrapper.__wrapped__ = func
        wrapper.__name__ = new_func_name
        wrapper.__doc__ = test_desc
        return wrapper

    @classmethod
    def __handle_datas(cls, datas):
        if isinstance(datas, list):
            return datas
        if isinstance(datas, str) and datas.endswith('.json') or datas.endswith('.yaml'):
            if os.getcwd().split() == "testcases":
                filepath = os.path.join('..', 'casedata', datas)
            else:
                filepath = os.path.join('.', 'casedata', datas)
            # 支持json
            if filepath.endswith('.json'):
                with open(filepath, 'rb') as f:
                    return json.load(f)
            # 支持yaml
            if filepath.endswith('.yaml'):
                with open(filepath, 'rb') as f:
                    return yaml.load(f, Loader=yaml.FullLoader)
            # 支持excel：暂未实现
        raise ValueError('测试用例数据格式有误！')


class BaseTestCase(unittest.TestCase, metaclass=GenerateTest):

    def perform(self, item):
        pass

    def get(self, attr):
        """支持通过get方法获取属性"""
        return getattr(self, attr, None)
