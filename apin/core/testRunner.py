# Author:柠檬班-木森
# E-mail:musen_nmb@qq.com
import json
import os
import unittest
import time
import copy
from jinja2 import Environment, FileSystemLoader
from concurrent.futures.thread import ThreadPoolExecutor
from apin.core.initEvn import log
from apin.core.testResult import ReRunResult
from apin.core.resultPush import DingTalk, WeiXin, SendEmail



class TestRunner():
    """unittest运行程序"""

    def __init__(self, suite: unittest.TestSuite,
                 filename="reports.html",
                 report_dir=".",
                 title='测试报告',
                 tester='测试员',
                 desc="XX项目测试生成的报告",
                 templates=1,
                 no_report=False
                 ):
        """
        初始化用例运行程序
        :param suites: 测试套件
        :param filename: 报告文件名
        :param report_dir:报告文件的路径
        :param title:测试套件标题
        :param templates: 可以通过参数值1或者2，指定报告的样式模板，目前只有两个模板
        :param tester:测试者
        :param no_report:不生成测试报告，以json数据格式返回测试结果，默认生成，设置True则不生成报告
        """
        if not isinstance(suite, unittest.TestSuite):
            raise TypeError("suites 不是测试套件")
        if not isinstance(filename, str):
            raise TypeError("filename is not str")
        if not filename.endswith(".html"):
            filename = filename + ".html"
        self.suite = suite
        self.filename = filename
        self.title = title
        self.tester = tester
        self.desc = desc
        self.templates = templates
        self.report_dir = report_dir
        self.result = []
        self.starttime = time.time()
        self.no_report = no_report

    def __classification_suite(self):
        """
        将测试套件中的用例，根据用例类位单位，拆分成多个测试套件，打包成列表类型
        :return: list-->[suite,suite,suite.....]
        """
        suites_list = []

        def wrapper(suite):
            for item in suite:
                if isinstance(item, unittest.TestCase):
                    suites_list.append(suite)
                    break
                else:
                    wrapper(item)

        wrapper(copy.deepcopy(self.suite))
        return suites_list

    def __get_reports(self,thread_count):
        """
        生成报告,返回测试汇中的结果
        :return: 包含测试结果的字典
        """
        # 汇总测试结果
        test_result = {
            "success": 0,
            "all": 0,
            "fail": 0,
            "skip": 0,
            "error": 0,
            "results": [],
            "testClass": [],

        }

        # 整合测试结果
        for res in self.result:
            for item in test_result:
                test_result[item] += res.fields[item]
        test_result['thread_count'] =thread_count
        test_result['runtime'] = '{:.2f} S'.format(time.time() - self.starttime)
        test_result["begin_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.starttime))
        test_result["title"] = self.title
        test_result["tester"] = self.tester
        test_result['desc'] = self.desc
        if test_result['all'] != 0:
            test_result['pass_rate'] = '{:.2f}'.format(test_result['success'] / test_result['all'] * 100)
        else:
            test_result['pass_rate'] = 0
        log.info("用例运行完毕,结果如下：\n共运行：{}条 "
                 "\n通过:{}条"
                 "\n失败:{}条"
                 "\n错误:{}条"
                 "\n运行时间:{}".format(
            test_result['all'], test_result['success'], test_result['fail'], test_result['error'],
            test_result['runtime']
        ))
        self.test_result = test_result
        # 判断是否要生产测试报告
        if os.path.isdir(self.report_dir):
            pass
        else:
            os.mkdir(self.report_dir)
        if self.no_report:
            return self.__get_results(test_result)
        log.info("正在生成测试报告中......")

        # 获取历史执行数据
        test_result['history'] = self.__handle_history_data(test_result)

        # 获取报告模板
        template_path = os.path.join(os.path.dirname(__file__), '../templates/reports')
        env = Environment(loader=FileSystemLoader(template_path))
        if self.templates == 2:
            template = env.get_template('templates2.html')
        elif self.templates == 3:
            template = env.get_template('templates3.html')
        else:
            template = env.get_template('templates1.html')

        file_path = os.path.join(self.report_dir, self.filename)
        # 渲染报告模板
        res = template.render(test_result)
        # 输出报告到文件
        with open(file_path, 'wb') as f:
            f.write(res.encode('utf8'))
        log.info("测试报告已经生成，报告路径为:{}".format(file_path))
        self.email_conent = {"file": os.path.abspath(file_path),
                             "content": env.get_template('templates03.html').render(test_result)
                             }

        return {'success': test_result['success'],
                'all': test_result['all'],
                'fail': test_result['fail'],
                'skip': test_result['skip'],
                'error': test_result['error'],
                'runtime': test_result['runtime'],
                'begin_time': test_result['begin_time'],
                'tester': test_result['tester'],
                'pass_rate': test_result['pass_rate'],
                'report': file_path,
                "thread_count":thread_count
                }

    def __handle_history_data(self, test_result):
        """
        处理历史数据
        :return:
        """
        try:
            with open(os.path.join(self.report_dir, 'history.json'), 'r', encoding='utf-8') as f:
                history = json.load(f)
        except FileNotFoundError as e:
            history = []
        history.append({'success': test_result['success'],
                        'all': test_result['all'],
                        'fail': test_result['fail'],
                        'skip': test_result['skip'],
                        'error': test_result['error'],
                        'runtime': test_result['runtime'],
                        'begin_time': test_result['begin_time'],
                        'pass_rate': test_result['pass_rate'],
                        })

        with open(os.path.join(self.report_dir, 'history.json'), 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=True)
        return history

    def __get_notice_content(self):
        """获取通知的内容"""
        template_path = os.path.join(os.path.dirname(__file__), '../templates/reports')
        env = Environment(loader=FileSystemLoader(template_path))
        res_text = env.get_template('dingtalk.md').render(self.test_result)
        return res_text

    def __get_results(self, test_result):
        """返回测试结果"""
        results = []
        for case in test_result.get('results'):
            results.append({k: v for k, v in case.__dict__.items() if not k.startswith('_')})
        test_result['results'] = results
        return test_result

    def run(self, thread_count=1, rerun=0, interval=2):
        """
        支持多线程执行
        注意点：如果多个测试类共用某一个全局变量，由于资源竞争可能会出现错误
        :param thread_count:线程数量，默认位1
        :return:测试运行结果
        """
        # 将测试套件按照用例类进行拆分
        suites = self.__classification_suite()
        with ThreadPoolExecutor(max_workers=thread_count) as ts:
            for i in suites:
                res = ReRunResult(count=rerun, interval=interval)
                self.result.append(res)
                ts.submit(i.run, result=res).add_done_callback(res.stopTestRun)
            ts.shutdown(wait=True)
        result = self.__get_reports(thread_count)
        return result

    def send_email(self, host, port, user, password, to_addrs, is_file=True):
        """
        发生报告为附件到邮箱
        :param host: str类型，(smtp服务器地址)
        :param port: int类型，(smtp服务器地址端口)
        :param user: str类型，(邮箱账号)
        :param password: str类型（邮箱密码）
        :param to_addrs: str(单个收件人) or list(多个收件人)收件人列表，
        :return:
        """
        sm = SendEmail(host=host, port=port, user=user, password=password)
        if is_file:
            filename = self.email_conent["file"]
        else:
            filename = None
        content = self.email_conent["content"]

        sm.send_email(subject=self.title, content=content, filename=filename, to_addrs=to_addrs)

    def get_except_info(self):
        """
        获取错误用例和失败用例的报错信息
        :return:
        """
        except_info = []
        num = 0
        for i in self.result:
            for texts in i.failures:
                t, content = texts
                num += 1
                except_info.append("*{}、用例【{}】执行失败*，\n失败信息如下：".format(num, t._testMethodDoc))
                except_info.append(content)
            for texts in i.errors:
                num += 1
                t, content = texts
                except_info.append("*{}、用例【{}】执行错误*，\n错误信息如下：".format(num, t._testMethodDoc))
                except_info.append(content)
        except_str = "\n".join(except_info)
        return except_str

    def dingtalk_notice(self, url, key=None, secret=None, atMobiles=None, isatall=False, except_info=False):
        """
        钉钉通知
        :param url: 钉钉机器人的Webhook地址
        :param key: （非必传：str类型）如果钉钉机器人安全设置了关键字，则需要传入对应的关键字
        :param secret:（非必传:str类型）如果钉钉机器人安全设置了签名，则需要传入对应的密钥
        :param atMobiles: （非必传，list类型）发送通知钉钉中要@人的手机号列表，如：[137xxx,188xxx]
        :param isatall: 是否@所有人，默认为False,设为True则会@所有人
        :param except_info:是否发送未通过用例的详细信息，默认为False，设为True则会发送失败用例的详细信息
        :return:  发送成功返回 {"errcode":0,"errmsg":"ok"}  发送失败返回 {"errcode":错误码,"errmsg":"失败原因"}
        """
        if not url:
            raise ValueError("url(钉钉群机器人的Webhook地址)不能为空")

        res_text = self.__get_notice_content()
        if except_info:
            res_text += '\n ### 未通过用例详情：\n'
            res_text += self.get_except_info()
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": '{}({})'.format(self.title, key),
                "text": res_text
            },
            "at": {
                "atMobiles": atMobiles,
                "isAtAll": isatall
            }
        }
        ding = DingTalk(url=url, data=data, secret=secret)
        response = ding.send_info()
        return response.json()

    def weixin_notice(self, chatid, access_token=None, corpid=None, corpsecret=None):
        """
        测试结果推送到企业微信群，【access_token】和【corpid，corpsecret】至少要传一种
        可以传入access_token ,也可以传入（corpid，corpsecret）来代替access_token
        :param chatid: 企业微信群ID
        :param access_token: 调用企业微信API接口的凭证
        :param corpid: 企业ID
        :param corpsecret:应用的凭证密钥
        :return:
        """
        # 获取通知结果
        res_text = self.__get_notice_content()
        data = {
            "chatid": chatid,
            "msgtype": "markdown",
            "markdown": {
                "content": res_text
            }
        }
        wx = WeiXin(access_token=access_token, corpid=corpid, corpsecret=corpsecret)
        response = wx.send_info(data=data)
        return response
