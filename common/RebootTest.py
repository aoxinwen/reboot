# coding = utf-8

"""
# @Time : 2021/1/14 9:41 
# @Author : Axw
# @File : RebootTest.py 
# @Software: PyCharm
"""

import paramiko
import os
from time import sleep


class Telent(object):
    def __init__(self, ip="", port=22, username="", password="", timeout=30):
        """
        通过IP, 端口，用户名，密码，超时时间，初始化一个远程主机
        :param str ip:
        :param int port: default value is 22
        :param str username:
        :param str password:
        :param int timeout: default value is 30.
        """
        # 连接信息参数
        self._ip = ip
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout

        # transport, channel, ssh, sftp, prompt初始化
        self._transport = None
        self._channel = None
        self._ssh = None
        self._sftp = None
        self._prompt = None
        # 连接失败的重试次数
        self._tryTimes = 3
        # 方便计算实际值是self._tryTimes+1
        self.allTimes = 4

    # 调用connect方法连接远程主机
    def connet(self):
        """
        :return: result
        """
        _result = ""
        while True:
            # try建立连接
            try:
                self._transport = paramiko.Transport(self._ip, self._port)
                self._transport.connect(username=self._username, password=self._password)
                _result += "{0} 创建成功".format(self._ip)
                break

            # 这里对可能的异常如网络不通、链接超时、socket.error, socket.timeout直接输出
            except Exception as _e:
                if self._tryTimes != 0:
                    _result += "第 {0} 次连接 {1} 失败，原因：{2}\n".format(self.allTimes - self._tryTimes, self._ip, _e)
                    _result += "开始重试\n"
                    self._tryTimes -= 1
                else:
                    _result += "第 {0} 次连接 {1} 失败，原因：{2}\n".format(self.allTimes - self._tryTimes, self._ip, _e)
                    _result += "尝试连接主机：{0} {1} 次都失败".format(self._ip, self.allTimes - 1)
                    break
        return _result

    # 开启ssh
    def create_ssh(self):
        try:
            self._ssh = paramiko.SSHClient()
            self._ssh._transport = self._transport
            return "创建{}ssh成功".format(self._ip)
        except Exception as _e:
            return "创建{}ssh失败：{}".format(self._ip, _e)

    # ssh发送非交互式命令
    def sshSendCommand(self, cmd):
        """
        仅支持无需交互的指令
        :param str cmd:
        :return: str stdout、str stderr
        """
        try:
            _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
            return _stdout.read().decode(), _stderr.read().decode()
        except Exception as _e:
            return "ssh指令执行失败：{}".format(_e)

    # 开启ftp服务
    def createSFTP(self):
        try:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            return "{}：SFTP连接成功".format(self._ip)
        except Exception as _e:
            return "{}：SFTP连接失败：{}".format(self._ip, _e)

    # 下载文件
    def sftp_down(self, remote_file="", local_file=""):
        """
        :param str remote_file: 远端的绝对路径+文件名
        :param str local_file: 本地的绝对路径+文件名
        :return: 下载结果
        """
        try:
            self._sftp.get(remote_file, local_file)
            return "{}下载成功".format(remote_file)
        except Exception as _e:
            return "{}下载失败:{}".format(remote_file, _e)

    # 上传文件
    def sftp_up(self, local_file="", remote_file=""):
        """
        :param str local_file: 本地的绝对路径+文件名
        :param str remote_file: 远端的绝对路径+文件名
        :return: 上传结果
        """
        try:
            self._sftp.put(local_file, remote_file)
            return "{}上传成功".format(local_file)
        except Exception as _e:
            return "{}上传失败：{}".format(local_file, _e)

    # 开启channel
    def create_channel(self):
        """
        :return: result
        """
        _result = ""
        try:
            self._channel = self._transport.open_session()  # 开启一个会话通道
            self._channel.settimeout(self._timeout)  # 设置超时时间
            self._channel.get_pty()  # 开启一个终端
            self._channel.invoke_shell()  # 建立一个交互式会话的shll
            _result += "{}channel建立成功\n".format(self._ip)
            sleep(2)
            _Banner = self._channel.recv(65535)  # 接收ssh banner信息
        except Exception as _e:
            _result += "{}channel建立失败：{}\n".format(self._ip, _e)
        return _result

    # 获取channel的提示符号
    def channel_get_prompt(self, expect_symbol=''):
        """
        :param str expect_symbol: The prompt's symbol,like '>','# ','$ ',etc.
        :return: result
        """
        _result = ""
        try:
            n = 0
            # 尝试3次
            while n < 3:
                self._channel.send("\r")
                # 暂停1秒接收输入回车后的返回结果
                _Prompt_vendor = self._channel.recv(64)
                # 获取提示符的两种方式：
                # 1. 按\r\n进行字符串分割，后边的就是完整的提示符
                self._prompt = _Prompt_vendor.decode('utf-8').split('\r\n')[-1]
                # 2. 提示符取输出的后x位，即_Prompt_vendor[-x:]
                # self._prompt = _Prompt_vendor[-2:].decode('utf-8')
                # 如果获取的提示符由期待的提示符末尾标识符结尾，判断为获取成功
                if self._prompt.endswith(expect_symbol):
                    _result += "提示符获取成功：{}".format(self._prompt)
                    break
                n += 1
            else:
                _result += "提示符获取异常：{}".format(self._prompt)
        except Exception as _e:
            _result += "提示符获取异常，原因：{}".format(_e)
        return _result

    # 通过channel发送指令，返回执行结果。如果指令是交互指令，则需要给出交互的断点提示符
    def channelSendCommand(self, cmd='', break_prompt=''):
        """
        通过channel发送指令。
        如果是交互式指令，必须要给出break_prompt！用来判断断点，结束while循环，返回结果
        无需交互的指令，break_prompt空着就行
        :param str cmd: 执行的指令，支持交互指令
        :param str break_prompt: 判断指令结束/断点的提示符。默认为channel的提示符
        :return: result
        """
        _stream = ""
        if not break_prompt:
            break_prompt = self._prompt
        try:
            cmd += '\r'
            # 发送命令
            self._channel.send(cmd)
            # 回显很长的命令可能执行较久，通过循环分批次取回回显
            while True:
                sleep(1)
                _stream += self._channel.recv(1024).decode('utf-8')
                if _stream.endswith(break_prompt):
                    break
            return _stream
        except Exception as _e:
            return "channel执行命令异常：{}".format(_e)

    # 关闭服务
    def close(self):
        if self._ssh:
            self._ssh.close()
        if self._channel:
            self._channel.close()
        if self._transport:
            self._transport.close()
        return "{}连接已经关闭".format(self._ip)

    def __del__(self):
        return


if __name__ == "__main__":
    # ip = '192.168.0.57'
    ip = '192.168.0.58'
    port = 22
    username = 'root'
    password = '123'
    timeout = 50
    reboot_times = 10000
    local_file = os.path.join(os.path.abspath('.'), 'reboot.sh')
    remote_file = '/oem/reboot.sh'
    f = open(os.path.join(os.path.abspath('..'), 'logFile', 'rebootTest.log'), 'a+', encoding='utf-8')
    nt = Telent(ip=ip, port=port, username=username, password=password, timeout=timeout)
    print("首先连接终端，并且拷贝脚本到终端，拷贝情况：\n", file=f)
    print(nt.connet(), file=f)
    print(nt.createSFTP(), file=f)
    print(nt.sftp_up(local_file=local_file, remote_file=remote_file), file=f)
    print(nt.create_ssh(), file=f)
    print(nt.sshSendCommand('chmod 777 /oem/reboot.sh'), file=f)
    print(nt.close(), file=f)
    print("拷贝脚本结束！！！！开始测试：", file=f)
    f.close()
    for i in range(reboot_times):
        f = open(os.path.join(os.path.abspath('..'), 'logFile', 'rebootTest.log'), 'a+', encoding='utf-8')
        print("\n第{}次重启开始:\n\n".format(i+1), file=f)
        print(nt.connet(), file=f)
        print(nt.create_ssh(), file=f)
        print(nt.sshSendCommand('sh /oem/reboot.sh'), file=f)
        print(nt.close(), file=f)
        f.close()
        sleep(timeout)
