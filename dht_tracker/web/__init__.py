from __future__ import absolute_import
import tornado.ioloop 
from ._basehandle import BaseHandle
from ._counthandle import CountHandle
from ._taskhandle import TaskHandle
from ..config import WEBPORT
approte = [(r"/count.*",CountHandle),(r"/task",TaskHandle),]
application = tornado.web.Application(approte
)  
#----------------------------------------------------------------------
def web_start(port = WEBPORT):
    """"""
    application.listen(port)  
    tornado.ioloop.IOLoop.instance().start()
