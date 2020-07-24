#!/usr/bin/env python
#coding:utf-8
from multiprocessing import Manager,Pipe
#多进程信息同步字典
sync = Manager().dict()
#任务控制管道
control_out,control_in = Pipe(duplex=False)
