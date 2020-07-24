#!/usr/bin/env python
#coding:utf-8
import os
from setuptools import setup, find_packages
setup(name='dht-tracker',
      version='1.0',
      description='DHT网络',
      author='NASCU',
      author_email='1107775282@qq.com',
      license='BSD',
      url='https://github.com/nascu/dht-tracke/',
      download_url="https://github.com/nascu/dht-tracke/releases/latest",      
      packages=find_packages(),
      install_requires=[
          'gevent>=1.2.1',
          'bencode>=1.0',
          'tornado>=4.4.2',
          'logging'
          ],   
      zip_safe=False,
)