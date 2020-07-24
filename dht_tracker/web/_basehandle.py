#!/usr/bin/env python
#coding:utf-8
import json
import tornado.web
from ..common import sync

########################################################################
class BaseHandle(tornado.web.RequestHandler):
    """"""
    sync = sync
    #----------------------------------------------------------------------
    def jsondumps(self,data):
        """"""
        return json.dumps(data)
        
        
    
    