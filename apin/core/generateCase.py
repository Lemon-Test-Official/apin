# Author:柠檬班-木森
# E-mail:musen_nmb@qq.com
import unittest
import json
import os
import yaml
from apin.core.httptest import HttpCase
from apin.core.basecase import GenerateTest


class ParserDataToCase:
    @staticmethod
    def parser_json_create_cases(dir: str):
        """解析json文件创建用例"""
        suite = unittest.TestSuite()
        load = unittest.TestLoader()
        files = os.listdir(dir)
        for filename in files:
            if filename.endswith('.json') and filename.startswith('test'):
                with open(os.path.join(dir, filename), 'rb') as f:
                    case_data = json.load(f)
                cls_name = filename.replace('.json', '').replace('test', '').split('_')
                cls_name = 'Test' + ''.join([i.capitalize() for i in cls_name])
                cls = GenerateTest(cls_name, (HttpCase,), case_data)
                suite.addTest(load.loadTestsFromTestCase(cls))
        return suite

    @staticmethod
    def parser_yaml_create_cases(dir: str):
        """解析yaml文件创建用例"""
        suite = unittest.TestSuite()
        load = unittest.TestLoader()
        files = os.listdir(dir)
        for filename in files:
            # 支持json
            if filename.endswith('.yaml') and filename.startswith('test'):
                with open(os.path.join(dir, filename), 'rb') as f:
                    case_data = yaml.load(f, Loader=yaml.FullLoader)
                cls_name = filename.replace('.yaml', '').replace('test', '').split('_')
                cls_name = 'Test' + ''.join([i.capitalize() for i in cls_name])
                cls = GenerateTest(cls_name, (HttpCase,), case_data)
                suite.addTest(load.loadTestsFromTestCase(cls))
        return suite

    @staticmethod
    def parser_data_create_cases(datas):
        """
        解析数据创建用例
        :param data:
        :return:
        """
        suite = unittest.TestSuite()
        load = unittest.TestLoader()
        for index, data in enumerate(datas):
            cls_name = 'TestCase{}'.format(index)
            cls = GenerateTest(cls_name, (HttpCase,), data)
            suite.addTest(load.loadTestsFromTestCase(cls))
        return suite
