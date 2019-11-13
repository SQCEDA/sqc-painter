# -*- coding: utf-8 -*-


from math import cos,sin,pi,tan,atan2,sqrt,ceil,floor

import pya

from .IO import IO
from .CavityBrush import CavityBrush
from .BasicPainter import BasicPainter
from .CavityPainter import CavityPainter
from .PcellPainter import PcellPainter

class Collision(object):
    '''处理图形冲突的类'''
    pointRadius=1000
    def __init__(self):
        self.region=pya.Region()
    def insert(self,polygon):
        if isinstance(polygon,list):
            for x in polygon:
                if isinstance(x,pya.DPolygon):
                    self.region.insert(pya.Polygon.from_dpoly(x))
            return self
        if isinstance(polygon,pya.DPolygon):
            self.region.insert(pya.Polygon.from_dpoly(polygon))
            return self
        if isinstance(polygon,pya.Region):
            self.region=self.region+polygon
            return self
        raise TypeError('Invalid input')
    def conflict(self,other):
        if isinstance(other,Collision):
            return self.region.interacting(other.region)
        if isinstance(other,pya.DPoint):
            region=pya.Region(pya.DPolygon(BasicPainter.arc(other,self.pointRadius,8,0,360)))
            return self.region.interacting(region)
        raise TypeError('Invalid input')
    @staticmethod
    def getRegionFromLayer(layerInfo):
        region=pya.Region()
        if type(layerInfo)==str:
            layer=IO.layout.find_layer(layerInfo)
        else:
            layer=IO.layout.find_layer(layerInfo[0],layerInfo[1])
        region.insert(IO.top.begin_shapes_rec(layer))
        region.merge()
        return region
    @staticmethod
    def getShapesFromCellAndLayer(cellList,layerList=None,box=None,layermod='not in'):
        if layerList==None:layerList=[(0,0)]
        if type(box)==type(None):box=Interactive._box_selected()
        if not box:raise RuntimeError('no box set')
        _layerlist=[]
        for ii in layerList:
            if type(ii)==str:
                _layerlist.append(IO.layout.find_layer(ii))
            else:
                _layerlist.append(IO.layout.find_layer(ii[0],ii[1]))
        layers=[index for index in IO.layout.layer_indices() if index in _layerlist] if layermod=='in' else [index for index in IO.layout.layer_indices() if index not in _layerlist]
        outregion=pya.Region(box)
        inregion=pya.Region()
        for cell in cellList:
            for layer in layers:
                s=cell.begin_shapes_rec_touching(layer,box)
                inregion.insert(s)
        inregion.merge()
        return [outregion,inregion]



class Interactive:
    '''处理交互的类'''
    #v =pya.MessageBox.warning("Dialog Title", "Something happened. Continue?", pya.MessageBox.Yes + pya.MessageBox.No)
    deltaangle=45
    maxlength=1073741824
    turningr=50000
    indent='    '
    brushlist=[]
    searchr=500000

    @staticmethod
    def show(brush):
        Interactive.brushlist.append(brush)
        polygon=BasicPainter.Electrode(brush.reversed())
        BasicPainter.Draw(IO.link,IO.layer,polygon)
        return brush
    
    @staticmethod
    def _show_path(cell, layer, brush, pathstr):
        l = {'path': None}
        exec(pathstr, None, l)
        painter = CavityPainter(brush)
        length = painter.Run(l['path'])
        painter.Draw(cell, layer)
        return length

    @staticmethod
    def _get_nearest_brush(x,y):
        bestbrush=None
        bestr=Interactive.searchr
        pt=pya.DPoint(x,y)
        for brush in Interactive.brushlist:
            r=brush.edgein.p1.distance(pt)
            if r<bestr:
                bestr=r
                bestbrush=brush
        return bestbrush

    @staticmethod
    def _pts_path_selected():
        for obj in IO.layout_view.each_object_selected():
            #只检查第一个选中的对象
            shape=obj.shape
            if not shape.is_path():break
            spts=list(shape.path.each_point())
            return spts
        pya.MessageBox.warning("paintlib.Interactive.link", "Please select a Path", pya.MessageBox.Ok)
        return False

    @staticmethod
    def _generatepath(pts,das):
        turningr=Interactive.turningr
        indent=Interactive.indent
        output=['def path(painter):','length=0']
        last=0
        for ii,da in enumerate(das):
            sda=(da>0)-(da<0)
            da*=sda
            dl=turningr*tan(da/180*pi/2)
            ll=pts[ii].distance(pts[ii+1])-last-dl
            last=dl
            if(ll<0):
                pya.MessageBox.warning("paintlib.Interactive.link", "Error : Straight less than 0", pya.MessageBox.Ok)
                return
            output.append('length+=painter.Straight({length})'.format(length=ll))
            output.append('length+=painter.Turning({radius},{angle})'.format(radius=sda*turningr,angle=da))
        output.append('length+=painter.Straight({length})'.format(length=pts[-1].distance(pts[-2])-last))
        output.append('return length')
        return ('\n'+indent).join(output)
    
    @staticmethod
    def link(brush1=None, brush2=None, spts=None, print_=True):
        '''
        输入两个CavityBrush作为参数, 并点击图中的一个路径, 生成一个连接两个brush的路径的函数  
        缺省时会在Interactive.searchr内搜索最近的brush
        第二个brush可为None, 此时取path的终点作为路径终点
        '''
        deltaangle = Interactive.deltaangle
        maxlength = Interactive.maxlength

        def boundAngle(angle):
            '''
            (-180,180]
            '''
            while angle<=-180:
                angle+=360
            while angle>180:
                angle-=360
            return angle
        def gridAngle(angle):
            return boundAngle(round(angle/deltaangle)*deltaangle)

        if spts == None:
            spts = Interactive._pts_path_selected()
        if spts == False:
            return
        if brush1 == None:
            brush1 = Interactive._get_nearest_brush(spts[0].x, spts[0].y)
        if brush2 == None:
            brush2 = Interactive._get_nearest_brush(spts[-1].x, spts[-1].y)

        if not isinstance(brush1, CavityBrush):
            pya.MessageBox.warning("paintlib.Interactive.link",
                                "Argument 1 must be CavityBrush", pya.MessageBox.Ok)
            return
        if not isinstance(brush2, CavityBrush) and brush2 != None:
            pya.MessageBox.warning("paintlib.Interactive.link",
                                "Argument 2 must be CavityBrush or None", pya.MessageBox.Ok)
            return
        angles = [boundAngle(brush1.angle)]
        pts = [pya.DPoint(brush1.centerx, brush1.centery)]
        edges = [pya.DEdge(pts[0].x, pts[0].y, pts[0].x+maxlength *
                        cos(angles[0]/180*pi), pts[0].y+maxlength*sin(angles[0]/180*pi))]
        das = []
        lastpt = None

        for ii in range(1, len(spts)):
            pt = spts[ii]
            pt0 = spts[ii-1]
            angle0 = angles[-1]
            edge0 = edges[-1]
            angle = gridAngle(atan2(pt.y-pt0.y, pt.x-pt0.x)/pi*180)
            da=boundAngle(angle0 - angle)
            if(da == 0):
                continue
            if(da == 180):
                pya.MessageBox.warning(
                    "paintlib.Interactive.link", "Error : Turn 180 degrees", pya.MessageBox.Ok)
                return
            edge = pya.DEdge(pt.x+maxlength*cos(angle/180*pi), pt.y+maxlength*sin(angle/180*pi),
                            pt.x-maxlength*cos(angle/180*pi), pt.y-maxlength*sin(angle/180*pi))
            if not edge.crossed_by(edge0):
                if len(das)==0:
                    continue
                print('point ', ii)
                print(angle)
                print(angle0)
                pya.MessageBox.warning(
                    "paintlib.Interactive.link", "Error : Invalid path leads to no crossing point", pya.MessageBox.Ok)
                return
            lastpt = [pt.x, pt.y]
            angles.append(angle)
            das.append(da)
            pts.append(edge.crossing_point(edge0))
            edges.append(edge)

        if(brush2 != None):
            angle0 = angles[-1]
            edge0 = edges[-1]
            angle = boundAngle(brush2.angle+180)
            pt = pya.DPoint(brush2.centerx, brush2.centery)
            _angle = gridAngle(angle)
            if(_angle == angle0 and len(das)>0):
                # 规整化后与终点平行, 放弃最后一个点, 从而不再平行
                angles.pop()
                das.pop()
                pts.pop()
                edges.pop()
                angle0 = angles[-1]
                edge0 = edges[-1]
            da = boundAngle(angle0 - angle)
            _da = boundAngle(angle0 - _angle)
            if(_da == 180):
                pya.MessageBox.warning(
                    "paintlib.Interactive.link", "Error : Turn 180 degrees", pya.MessageBox.Ok)
                return
            lastpt = [pt.x, pt.y]
            edge = pya.DEdge(pt.x, pt.y, pt.x-maxlength *
                            cos(angle/180*pi), pt.y-maxlength*sin(angle/180*pi))
            if(angle == angle0 and len(das)==0):
                # 只有起点和终点且平行
                dis=edge0.distance(pt)
                if abs(dis)<10:
                    # 直连无需转弯
                    pass
                else:
                    # 需转弯, 此处多生成两个点和两个角度, 如果dis小于2-sqrt(2)的转弯半径, 生成路径时会报错
                    pt0=pts[-1]
                    dse=pt0.distance(pt)
                    dp=sqrt(dse**2-dis**2)
                    l1=(dp-dis)/2
                    if dis<0:
                        das.extend([-45,45])
                        angles.extend([angle+45,angle])
                    else:
                        das.extend([45,-45])
                        angles.extend([angle-45,angle])
                    pt1=pya.DPoint(pt0.x+l1*cos(angle/180*pi),pt0.y+l1*sin(angle/180*pi))
                    pt2=pya.DPoint(pt.x-l1*cos(angle/180*pi),pt.y-l1*sin(angle/180*pi))
                    pts.extend([pt1,pt2])
                    edges.extend([pya.DEdge(pt1,pt2),edge])
            else:
                angles.append(angle)
                das.append(da)
                if not edge.crossed_by(edge0):
                    print('brush2')
                    print(angle)
                    print(angle0)
                    pya.MessageBox.warning(
                        "paintlib.Interactive.link", "Error : Invalid path leads to no crossing point", pya.MessageBox.Ok)
                    return
                pts.append(edge.crossing_point(edge0))
                edges.append(edge)
        pts.append(pya.DPoint(lastpt[0], lastpt[1]))
        ss = Interactive._generatepath(pts, das)
        if print_:
            print('##################################')
            print(ss)
            print('##################################')
            Interactive._show_path(IO.link, IO.layer, brush1, ss)
        return ss
    
    @staticmethod
    def _box_selected():
        for obj in IO.layout_view.each_object_selected():
            #只检查第一个选中的对象
            shape=obj.shape
            if not shape.is_box():break
            return shape.box
        pya.MessageBox.warning("paintlib.Interactive.cut", "Please select a Box", pya.MessageBox.Ok)
        return False

    @staticmethod
    def _merge_and_draw(outregion,inregion,tr_to=None,cell=None,cutbool=True):
        if cutbool:
            region=outregion-inregion
        else:
            region=outregion & inregion
        #
        if type(cell)==type(None):
            if type(tr_to)==type(None):
                center=outregion.bbox().center()
                region.transform(pya.Trans(-center.x,-center.y))
                tr=pya.Trans(center.x,center.y)
            else:
                tr=tr_to
            cut = IO.layout.create_cell("cut")
            IO.auxiliary.insert(pya.CellInstArray(cut.cell_index(),tr))
        else:
            cut = cell
        BasicPainter.Draw(cut,IO.layer,region)
        return region,cut

    @staticmethod
    def cut(layerlist=None,layermod='not in',box=None,mergeanddraw=True):

        outregion,inregion=Collision.getShapesFromCellAndLayer(cellList=[IO.top],layerList=layerlist,box=box,layermod=layermod)

        if not mergeanddraw:
            return outregion,inregion

        return Interactive._merge_and_draw(outregion,inregion)[0]
    
    @staticmethod
    def scanBoxes(cellList=None,layerList=None,layermod='in'):
        if cellList==None:cellList=[IO.top]
        if layerList==None:layerList=[(0,1)]
        _layerlist=[]
        for ii in layerList:
            if type(ii)==str:
                _layerlist.append(IO.layout.find_layer(ii))
            else:
                _layerlist.append(IO.layout.find_layer(ii[0],ii[1]))
        layers=[index for index in IO.layout.layer_indices() if index in _layerlist] if layermod=='in' else [index for index in IO.layout.layer_indices() if index not in _layerlist]

        region=pya.Region()
        for cell in cellList:
            for layer in layers:
                s=cell.begin_shapes_rec(layer)
                region.insert(s)
        region.merge()
        pts=[]
        for polygon in region.each():
            print(polygon)
            try:
                polygon=polygon.bbox()
            finally:
                pass
            print(polygon)
            pt=polygon.p1
            pts.append(pt)
        output=[]
        layer=IO.layout.layer(0, 2)
        cell=IO.layout.create_cell("boxMarks")
        IO.auxiliary.insert(pya.CellInstArray(cell.cell_index(),pya.Trans()))
        painter=PcellPainter()
        for index,pt in enumerate(pts,1):
            name="M"+str(index)
            painter.DrawText(cell,layer,name,pya.DCplxTrans(100,0,False,pt.x,pt.y))
            output.append([name,{"x":pt.x,"y":pt.y}])
        return output

    
