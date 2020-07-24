#!/usr/bin/env python
#coding:utf-8
from . import BaseHandle

########################################################################
class CountHandle(BaseHandle):
    """"""
    #----------------------------------------------------------------------
    def get(self):
        """"""
        res_netcount = self.sync['netcount']
        args = [i for i in self.request.uri.split('/') if i][1:]
        for index,arg in enumerate(args):
            if arg in res_netcount:
                res_netcount = res_netcount[arg]
            else:
                self.finish(self.jsondumps(
                    {
                        "KeyError":"the key [%s] is not in %s"%(arg,"/".join(["count"]+args[:index]))
                    }
                ))
                return
        self.finish(self.jsondumps(res_netcount.status))

        
    
    