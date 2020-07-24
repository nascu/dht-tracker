#!/usr/bin/env python
#coding:utf-8
from copy import deepcopy
from . import BaseHandle
from ..common import control_in

class TaskHandle(BaseHandle):
    """"""
    
    #----------------------------------------------------------------------
    def _position(self):
        """"""
        pass
    #----------------------------------------------------------------------
    def loadtask(self,status):
        """"""
        res = deepcopy(status)
        res["id"] = status["id"].encode("hex")
        res["items"] = [(i[0].encode("hex") if i[0] else i[0],i[1]) for i in status["items"]]
        return res
    def loadtube(self,status):
        res = deepcopy(status)
        res["detail"] = [self.loadtask(i) for i in status["detail"]]
        return res 
    def loadline(self,status):
        res = deepcopy(status)
        res["detail"] = [(i[0],self.loadtube(i[1])) for i in status["detail"]]
        return res
    def get(self):
        """"""
        tubes = self.request.arguments.get("tubes")
        taskid = self.request.arguments.get("taskid")
        taskline = self.sync["taskline"]
        if not tubes:
            self.finish(self.jsondumps(self.loadline(taskline.status)))
            return
        tubes = tubes[0]      
        task_tube = taskline[tubes]
        if not taskid:
            self.finish(self.jsondumps(self.loadtube(task_tube.status)))
            return
        taskid = taskid[0]      
        task = task_tube[taskid.decode("hex")]
        if task is None:
            self.finish(self.jsondumps(
                {
                    "TaskIdError":"the taskid [%s] is not in this tubes (%s)"%(taskid,tubes)
                }
            ))
            return
        self.finish(self.jsondumps(self.loadtask(task.status)))

    #----------------------------------------------------------------------
    def post(self):
        """"""
        tubes = self.request.arguments.get("tubes")
        taskid = self.request.arguments.get("taskid")
        if not (tubes and taskid):
            self.finish(self.jsondumps(
                {
                    "InputError":"you must input tubes and taskid!"
                 }
            ))
            return
        tubes = tubes[0]
        taskid = taskid[0]        
        control_in.send(("push",(tubes,taskid.decode("hex"))))
        self.finish(self.jsondumps(
            {
                "post":"OK"
            }
        ))
    #----------------------------------------------------------------------
    def put(self):
        """"""
        tubes = self.request.arguments.get("tubes")
        taskid = self.request.arguments.get("taskid")
        started = self.request.arguments.get("started")
        if not (tubes and taskid and started):
            self.finish(self.jsondumps(
                {
                    "InputError":"you must input tubes and taskid and started!"
                 }))
            return
        try:
            started = int(started[0])
        except ValueError:
            self.finish(self.jsondumps(
                {
                    "ValueError":"the started is must be type -> int"
                 }))
            return  
        tubes = tubes[0]
        taskid = taskid[0]
        taskline = self.sync["taskline"]
        task = taskline[tubes][taskid.decode("hex")]
        if task is None:
            self.finish(self.jsondumps(
                {
                    "KeyError":"the taskid [%s] is not in the tubes %s"%(taskid,tubes)
                 }
            ))
            return
        control_in.send(("start" if started else "stop",(tubes,taskid.decode("hex"))))
        self.finish(self.jsondumps(
            {
                "post":"OK"
            }))
        
        
    #----------------------------------------------------------------------
    def delete(self):
        """"""
        tubes = self.request.arguments.get("tubes")
        taskid = self.request.arguments.get("taskid")
        if not (tubes and taskid):
            self.finish(self.jsondumps(
                {
                    "InputError":"you must input tubes and taskid!"
                 }))
            return  
        tubes = tubes[0]
        taskid = taskid[0]        
        taskline = self.sync["taskline"]
        task = taskline[tubes][taskid.decode("hex")]
        if task is None:
            self.finish(self.jsondumps(
                {
                    "KeyError":"the taskid [%s] is not in the tubes %s"%(taskid,tubes)
                 }
            ))
            return
        control_in.send(("remove",(tubes,taskid.decode("hex"))))
        self.finish(self.jsondumps(
            {
                "post":"OK"
            }))
        

    
