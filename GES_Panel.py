#    Copyright (c) 2020 imagiscope

#    Permission is hereby granted, free of charge, to any person obtaining a copy
#    of this software and associated documentation files (the "Software"), to deal
#    in the Software without restriction, including without limitation the rights
#    to use the Software, and to permit persons to whom the Software is
#    furnished to do so, subject to the following conditions:

#    1. Not for resale (use of software tools for revenue generation excluded).
#    2. Credit to: "https://www.youtube.com/c/ImagiscopeTech"
#    3. Notification of commercial use to author.

#    The above copyright notice and this permission notice shall be included in all
#    copies or substantial portions of the Software.

#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#    SOFTWARE.

bl_info = {
    "name": "Earth Studio",
    "author": "Rob Jolly - Imagiscope",
    "description": "Earth Studio Tools Addon",
    "blender": (2, 80, 0),
    "version": (1, 0, 0),
    "location": "View3D",
    "warning": "",
    "category": "Import-Export"
}

import bpy, json, mathutils, math, bmesh
from mathutils import *
from bpy.props import EnumProperty
from xml.dom.minidom import parse
from xml.dom.minidom import Node
from xml.etree import cElementTree as ElementTree



                
class GES_OT_Path(bpy.types.PropertyGroup):
    p_data: bpy.props.StringProperty(name="0000",subtype='FILE_PATH',default=r"")
    p_movie: bpy.props.StringProperty(name="data",subtype='FILE_PATH',default=r"")
    p_kml: bpy.props.StringProperty(name="kml",subtype='FILE_PATH',default=r"")
    p_refdata: bpy.props.StringProperty(name="refdata",subtype='FILE_PATH',default=r"")
    
    p_expfolder: bpy.props.StringProperty(name="expdata",subtype='DIR_PATH',default=r"//")
    p_exp: bpy.props.StringProperty(name="expdata",subtype='FILE_NAME',default=r"ModifiedKML")
    
    v_curve: bpy.props.EnumProperty(name="Curve",items=[('POLY',"Poly",""),('NURBS',"Nurbs","")])
    
    def trackitems(self,context):
        t_trks = []
        objects = bpy.context.scene.objects
        for obj in objects:
            if obj.type == "MESH":
                if  obj.data.name[0:5] == "Plane":
                    t_trks.append(( obj.name, obj.name,""))
        return t_trks
    v_snapto: bpy.props.EnumProperty(
        name = "Snap to",
        description = "Snap to TrackPoint in _GES_WORLD",
        items =  trackitems 
    )
    
    v_terrain: bpy.props.BoolProperty(name="Follow Terrain",description="Align the KML route with supplied JSON TrackPoints.", default = True) 
    v_pwidth: bpy.props.BoolProperty(name="Physical Width",description="Fixed width (or variable based on camera).", default = True) 
  
    
    v_elevation: bpy.props.IntProperty(name="Add Elevation (m)", default=0, min=-100, max=10000, 
        description="Add elevation to Route (0 is none, 1000 = 1km, 100000 = 10km)" )
        
    v_reduce: bpy.props.IntProperty(name="Point Reduction", default=2, min=0, max=100, 
        description="Reduce KML points based on clustering (1 is less reduction, 100 is more reduction)" )
    v_prox: bpy.props.IntProperty(name="Match Proximity (m)", default=1, min=1, max=1000,
        description="Set altitude based on meters (approx) to trackpoint (1 is closer, 100 more forgiving)")
    
    v_bevel: bpy.props.FloatProperty(name="Bevel Depth", default=0, min=0, max=5, 
        description="Starting Route Bevel (0 = none)" )
            
    v_xwidth: bpy.props.IntProperty(name="Line Width (m)", default=20, min=1, max=100, 
        description="Exact width of line, in meters (will not resize)" )
    v_xheight: bpy.props.IntProperty(name="Line Elevation (m)", default=5, min=0, max=50, 
        description="Exact width of line, in meters (will not resize)" )
        
    v_xcolor: bpy.props.FloatVectorProperty(name="Line/Fill Color", subtype='COLOR', default=[0.0,1.0,0.0])
    
    #reduce KML points based on closeness - default 10 (1 is closer (less reduction), 100 further away (more reduction))"
# Earth Studio import panel
class GES_PT_ImportPanel(bpy.types.Panel):
    bl_label = "Earth Studio Import"
    bl_idname = "GES_PT_ImportPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Earth Studio'
    
    def draw(self,context):
        layout = self.layout
        row = layout.row()
        row.label(text="Footage (mp4 or first jpeg):")
        row = layout.row()
        row.prop(bpy.context.scene.GES_OT_Path, "p_movie", text="",icon="IMAGE_DATA")
        row = layout.row()
        row.label(text="Earth Studio JSON File:")
        row = layout.row()
        row.prop(bpy.context.scene.GES_OT_Path, "p_data", text="",icon="VIEW_CAMERA")
        row = layout.row()
        fa = bpy.context.scene.GES_OT_Path.p_movie
        fb  = bpy.context.scene.GES_OT_Path.p_data
        if fa != '' and fb != '': # ensure both selections have 'text' (simple validation)
            row.operator("scene.pre_ges", text="Import Earth Studio" )
        if fa == '' or fb == '':
            row.operator("scene.is_void", text="Select Files" , icon="LOCKED")

# KML import panel               
class GES_PT_KMLPanel(bpy.types.Panel):
    bl_label = "KML Route Import/Export"
    bl_idname = "GES_PT_KMLPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI' 
    bl_category = 'Earth Studio'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self,context):
        objects = bpy.context.scene.objects
        hasGES = 0
        for obj in objects:
           
            if obj.name == "_GES_WORLD":
                hasGES=1
           
                    
        if hasGES == 1: # enabled
           
            context.area.tag_redraw()
            layout = self.layout
            row = layout.row()
            row.label(text="KML File (route):")
            row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "p_kml", text="", icon="WORLD")
            row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_snapto")
            row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_curve")
            row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_bevel")
            row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_elevation")
            row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_terrain")
            if str(bpy.context.scene.GES_OT_Path.v_terrain) == "True":
                row = layout.box()
                row.label(text="Reference JSON File:")
                row.prop(bpy.context.scene.GES_OT_Path, "p_refdata", text="", icon="LIBRARY_DATA_DIRECT")
                row.prop(bpy.context.scene.GES_OT_Path, "v_reduce")
                row.prop(bpy.context.scene.GES_OT_Path, "v_prox")
            row = layout.row()
            
            fa = bpy.context.scene.GES_OT_Path.p_kml
            fb  = bpy.context.scene.GES_OT_Path.p_refdata
            if fa != '': #(simple validation)
                row.operator("scene.pre_kml", text="Import KML Route" ).action = "pri"
               
            if fa == '':
                row.operator("scene.is_void", text="Select Files" , icon="LOCKED")
        if hasGES == 0: # 'disable' section if there is no imported project
            layout = self.layout
            row = layout.row()
            row.label(text="Import Earth Studio first", icon="LOCKED")
            row = layout.row()
            
class GES_PT_SubKML(bpy.types.Panel):
    bl_parent_id = "GES_PT_KMLPanel"
    
    bl_label = "Modified KML Export"
    bl_idname = "GES_PT_SubKML"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI' 
    bl_category = 'Earth Studio'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self,context):
        fa = bpy.context.scene.GES_OT_Path.p_kml
        layout = self.layout
        row = layout.row()
        if fa != '':
            row = layout.box()
            row.label(text="For 'Green Screen' application",icon = "INFO")
            #row = layout.row()
            #row = layout.row()
            row.label(text="Destination Folder:")
            #row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "p_expfolder", text="")
            #row = layout.row()
            row.label(text="Route Name (filename):" )
            #row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "p_exp", text="")
            #row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_xwidth")
            row.prop(bpy.context.scene.GES_OT_Path, "v_pwidth")
            #row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_xheight")
            #row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_xcolor")
            #row = layout.row()
            fb  = bpy.context.scene.GES_OT_Path.p_exp
            if fb == "":
                row.operator("scene.is_void", text="Assign Export Filename" , icon="LOCKED")
            elif fb != "":
                row.operator("scene.pre_kml", text="Export Modified KML Route" ).action = "sec"
        if fa == '':
            row.label(text="Import KML first", icon="LOCKED")
        #row = layout.row()
        
            
# Help Panel
class GES_PT_InfoPanel(bpy.types.Panel):
    bl_label = "Help"
    bl_idname = "GES_PT_InfoPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI' 
    bl_category = 'Earth Studio'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self,context):
        layout = self.layout
       
        row = layout.row()
        row.label(text="Tutorials")
        row = layout.row()
        op = row.operator('wm.url_open', text="View on YouTube")
        op.url = "https://www.youtube.com/c/ImagiscopeTech"
       
        row = layout.row()

# Void class - returns nothing
class isvoid(bpy.types.Operator):
    bl_idname = "scene.is_void"
    bl_label = "GES is void"
    
    def execute(self, context): 
        return {'FINISHED'}

# check files   
class preKML(bpy.types.Operator):
    bl_idname = "scene.pre_kml"
    bl_label = "GES PRE KML"
    
    action: EnumProperty(items=[('pri','pri','pri'),('sec','sec','sec')])
        
    def execute(self, context):
        if self.action == "pri":
            importkml()
        elif self.action == "sec":
            newkml()
        return {'FINISHED'}


class preGES(bpy.types.Operator):
    bl_idname = "scene.pre_ges"
    bl_label = "GES PRE GES"
    
    def execute(self, context):
        fa = bpy.context.scene.GES_OT_Path.p_movie
        fb  = bpy.context.scene.GES_OT_Path.p_data
        if fa != '' and fb != '':
            importges()
            t_trks = []
            objects = bpy.context.scene.objects
            for obj in objects:
                if obj.type == "MESH":
                    if  obj.data.name[0:5] == "Plane":
                        t_trks.append(( obj.name, obj.name,""))
            v_snapto = bpy.props.EnumProperty(
                 name = "Snap to",description = "Snap to TrackPoint in _GES_WORLD",items = t_trks  )
        return {'FINISHED'}
    
def importges():
    cam = bpy.context.scene.camera

    scene = bpy.context.scene
    # load the GES render files as background for camera
    # Sample format: ifiles = "D:/Local/Project/Beach/beach/footage/beach_0000.jpeg"
    ifiles = bpy.path.abspath(bpy.context.scene.GES_OT_Path.p_movie)

    img = bpy.data.movieclips.load(ifiles)
    cam.data.show_background_images = True
    bg = cam.data.background_images.new()
    bg.clip = img
    bg.alpha = 1
    bg.source = "MOVIE_CLIP"
 
    # load JSON file for evaluation
    # Sample format: jfilename = "D:/Local/Project/Beach/beach/beach.json"
    jfilename = bpy.path.abspath(bpy.context.scene.GES_OT_Path.p_data)

    jfile = open(jfilename,'r')
    camdata = json.load(jfile)
    jfile.close

    # evaluate number of frames
    s_end = camdata["numFrames"]

    # set scene duration
    scene.frame_start = 1
    scene.frame_end = s_end 
    scene.frame_set(1)

    # function for alignment scaling
    def scale_from_vector(v):
        mat = Matrix.Identity(4)
        for i in range(3):
            mat[i][i] = v[i]
        return mat   
            
    # set coords for positioning data starting at center of Blender global coordinates
    psx = 0
    psy = 0
    psz = 0 

    # load trackpoints
    for f in range (0,len(camdata["trackPoints"])):
        
        px = camdata["trackPoints"][f]["position"]["x"]
        py = camdata["trackPoints"][f]["position"]["y"]
        pz = camdata["trackPoints"][f]["position"]["z"]
        
        rlat = camdata["trackPoints"][f]["coordinate"]["position"]["attributes"][0]["value"]["relative"]
        rlng = camdata["trackPoints"][f]["coordinate"]["position"]["attributes"][1]["value"]["relative"]
        
        if f==0:
            psx = px
            psy = py
            psz = pz
            
        rlat = 360 * (rlat) - 180
        rlng = 180 * (rlng ) - 90
        
        bpy.ops.mesh.primitive_plane_add()
        trk = bpy.context.selected_objects[0]
        trk.name = str(f + 1) + ". " + camdata["trackPoints"][f]["name"]
      
        trk.location.x = (px-psx) / 100
        trk.location.y = (py-psy) / 100
        trk.location.z = (pz-psz) / 100
        
        trk.rotation_euler[1] = math.radians(90-rlng)
        trk.rotation_euler[2] = math.radians(rlat)
        trk.scale = (0.1,0.1,0.1)
        
        calt = camdata["trackPoints"][f]["coordinate"]["position"]["attributes"][2]["value"]["relative"]
        trk['ALT'] = 65117481 * (calt) + 1 
        
        if f==0:
            # create parent object - parent used to align position on earth with Blender global coordinates
            bpy.ops.object.empty_add(type='SINGLE_ARROW', location=(0,0,0))
            ges_parent = bpy.context.selected_objects[0]
            ges_parent.name = "_GES_WORLD"
            
            # align parent perpendicular to first track point
            loc_src, rot_src, scale_src = trk.matrix_world.decompose()
            loc_dst, rot_dst, scale_dst = ges_parent.matrix_world.decompose()

            axis = Vector((0.0, 0.0, 1.0))
            z1 = rot_src @ axis
            z2 = rot_dst @ axis
            q = z2.rotation_difference(z1)

            ges_parent.matrix_world = (
                Matrix.Translation(loc_dst) @
                (q @ rot_dst).to_matrix().to_4x4() @
                scale_from_vector(scale_dst)
            )
            
            # change x,y to negative values of x,y
            ges_parent.rotation_euler[0] = -ges_parent.rotation_euler[0]
            ges_parent.rotation_euler[1] = -ges_parent.rotation_euler[1]
                  
        # move trackpoint to GES parent
        trk.parent = ges_parent
     

    # Camera Information
    cam.delta_rotation_euler.y = 180 * math.pi / 180

    for f in range (0,s_end + 1):
        px = camdata["cameraFrames"][f]["position"]["x"] 
        py = camdata["cameraFrames"][f]["position"]["y"] 
        pz = camdata["cameraFrames"][f]["position"]["z"] 
       
            
        rx = float(camdata["cameraFrames"][f]["rotation"]["x"])
        ry = camdata["cameraFrames"][f]["rotation"]["y"] 
        rz = camdata["cameraFrames"][f]["rotation"]["z"]
        
        # position set in relation to first frame - scale to 1/100
        cam.location.x = (px-psx) / 100
        cam.location.y = (py-psy) / 100
        cam.location.z = (pz-psz) / 100
     
        eul = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
        
        eul.rotate_axis('X', math.radians(-rx))
        eul.rotate_axis('Y', math.radians(ry ))
        eul.rotate_axis('Z', math.radians(-rz+180))
        
        cam.rotation_euler = eul
      
        cam.keyframe_insert(data_path="location", index=-1, frame=f + 1)
        cam.keyframe_insert(data_path="rotation_euler", index=-1, frame=f + 1)
        
        
    # camera "lens" based on 20 degree Filed of View (default value)
    cam.data.sensor_width = 35 
    cam.data.type = 'PERSP'
    cam.data.lens_unit = 'FOV'
    cam.data.angle = math.radians(34.8)

    # move camera to GES parent
    cam.parent = ges_parent

    bpy.context.scene.frame_current = 1   
    area = next(area for area in bpy.context.screen.areas if area.type == 'VIEW_3D')
    area.spaces[0].region_3d.view_perspective = 'CAMERA'

def importkml():
    earth = 6371010.1 #earth radius, in meters
    add_elev = float(bpy.context.scene.GES_OT_Path.v_elevation)
    sn = bpy.data.objects[bpy.context.scene.GES_OT_Path.v_snapto]
    tralt = sn["ALT"]
    
    # function for alignment scaling
    def scale_from_vector(v):
        mat = Matrix.Identity(4)
        for i in range(3):
            mat[i][i] = v[i]
        return mat 

    # function to measure distance between two coordinates
    def measure(lat1, lon1, lat2, lon2):
       
        dLat = lat2 * math.pi / 180 - lat1 * math.pi / 180
        dLon = lon2 * math.pi / 180 - lon1 * math.pi / 180
        a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) * math.sin(dLon/2) * math.sin(dLon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = earth * c
        return d


    # make a new curve
    crv = bpy.data.curves.new('crv', 'CURVE')
    crv.dimensions = '3D'

    # make a new spline in that curve
    spline = crv.splines.new(type=bpy.context.scene.GES_OT_Path.v_curve)
    spline.resolution_u = 6
    spline.order_u = 12
    

    # load kml file for evaluation
    xfilename = bpy.path.abspath(bpy.context.scene.GES_OT_Path.p_kml)
    domData = parse(xfilename)
    coor = domData.getElementsByTagName("coordinates")
    
    pl = ""
    if coor.length != 0:
        for i in range (0,coor.length ):
            if coor[i].parentNode.nodeName != "Point":
                pl = coor[0].firstChild.nodeValue.strip()
                print ("coord found")
    if coor.length == 0 or pl == "": # try gx:coord method
        gxcoor = domData.getElementsByTagName("gx:coord")
        print ("xx")
        if gxcoor.length != 0:
            for i in range (0,gxcoor.length): #format like coordinates
                if i != 0:
                    pl+= " "
                pl +=  str(gxcoor[i].firstChild.nodeValue.strip()).replace(" ",",")
            print (pl)
        elif gxcoor.length == 0:
            return
    pt = pl.split(' ')
    #if add_elev != 0:
    if str(bpy.context.scene.GES_OT_Path.v_terrain) != 'True': # replace anchor value with trackpoint alt
        tt = pt[0].split(",")
        pt[0] = str(tt[0]) + "," + str(tt[1]) + "," + str(tralt)
    pl = pt[0] + " " + pl # insert start point twice (anchor)
    pt = pl.split(' ')
    
    # add placeholder end coordinate
    pt.append (str(0) + "," + str(0) + "," + str(0) )  
   
    # load JSON file for evaluation
    # Sample format: jfilename = "D:/Local/Project/Beach/beach/beach.json"
   
    if str(bpy.context.scene.GES_OT_Path.v_terrain) == 'True':
        jfilename = bpy.path.abspath(bpy.context.scene.GES_OT_Path.p_refdata)

        jfile = open(jfilename,'r')
        camdata = json.load(jfile)
        jfile.close

   
    lpt = 0   
    
    if str(bpy.context.scene.GES_OT_Path.v_terrain) == 'True':
        # calculate altitude based on track points, incline/decline from A to B
        prox = bpy.context.scene.GES_OT_Path.v_prox /10000 # set altitude base on "closeness" to trackpoint - default 0.001 (0.0001 is closer, 0.01 more forgiving)
        for i in range (0,len(pt)):
            plat = float(pt[i].split(',')[0])
            plng = float(pt[i].split(',')[1])
            fnd = 0
            for z in range (0,len(camdata["trackPoints"])):
                if fnd == 0:
                    tlat =camdata["trackPoints"][z]["coordinate"]["position"]["attributes"][0]["value"]["relative"]
                    tlng =camdata["trackPoints"][z]["coordinate"]["position"]["attributes"][1]["value"]["relative"]
                    talt =camdata["trackPoints"][z]["coordinate"]["position"]["attributes"][2]["value"]["relative"]
                   
                    tname = camdata["trackPoints"][z]["name"]
                    xlat = 360 * (tlat) - 180
                    xlng = 180 * (tlng ) - 90
                    xalt = 65117481 * (talt) + 1 # base elevation 

                    if i == 0:
                        xalt = xalt - add_elev
                        pt[i] = str(plat) + "," + str(plng) + "," + str(xalt)
                    if (xlat - (plat)  < prox and xlat - (plat)  > - prox) and (xlng - (plng)  < prox and xlng - (plng)  > -prox):
                        pt[i] = str(plat) + "," + str(plng) + "," + str(xalt)
                        fnd = 1
                        
                            
            if (fnd == 1 and i > 0) or (i == len(pt)-1 and fnd == 0):
                pplat = float(pt[lpt].split(',')[0])
                pplng = float(pt[lpt].split(',')[1])
                ppalt = float(pt[lpt].split(',')[2])
                for d in range (lpt + 1,i ):
                    if i == len(pt)-1 and fnd == 0: 
                        xlat = pplat
                        xlng = pplng
                        xalt = ppalt
                    
                    dlat = float(pt[d].split(',')[0])
                    dlng = float(pt[d].split(',')[1])      
                    d1 = measure(pplat,pplng,dlat,dlng) # distance between last alt and this
                    d2 = measure(dlat,dlng,xlat,xlng) # distance between trackpoint alt and this
                    dratio = d1/(d1+d2)
                    newalt =  ppalt + ((xalt - ppalt) * dratio)
                    
                    pt[d] = str(dlat) + "," + str(dlng) + "," + str(newalt)
                    
                lpt = i   
    
        # reset start point with elevation change
        #stln = pt[0].split(",")
        #pt[0] = str(stln[0]) + "," + str(stln[1]) + "," + str(float(stln[2]) + add_elev)
    
        
    # convert lat/lon to points in 3D space on globe
    prevx = 0
    prevy = 0
    redval =  bpy.context.scene.GES_OT_Path.v_reduce  # reduce KML points based on closeness - default 10 (1 is closer (less reduction), 100 further away (more reduction))
    pn = []
    for i in range (0,len(pt)-1): 
        lon = float(pt[i].split(',')[0])
        lat = float(pt[i].split(',')[1])
        alt = float(pt[i].split(',')[2])
        
        if str(bpy.context.scene.GES_OT_Path.v_terrain) != 'True' and i==0:
            alt = alt - (add_elev)
        phi = (90 - lat) * (math.pi / 180);
        theta = (lon + 180) * (math.pi / 180);
        ox = -((earth + alt) * math.sin(phi) * math.cos(theta));
        oy = -((earth + alt) * math.sin(phi) * math.sin(theta));
        oz = ((earth + alt) * math.cos(phi))
        
        if (prevx + redval < ox or prevx - redval > ox) and (prevy + redval < oy or prevy - redval > oy) or i<2 or redval==0:
            pn.append( pt[i] + ',' + str(ox) + ',' + str(oy) + ',' + str(oz) )
            prevx = ox
            prevy = oy
        
    # set coordinates to spline
    flat = float(pn[0].split(',')[0])
    flng = float(pn[0].split(',')[1])
    psx = float(pn[0].split(',')[3])
    psy = float(pn[0].split(',')[4])
    psz = float(pn[0].split(',')[5])

    spline.points.add(len(pn)-1)
   
    for p, new_co in zip(spline.points, pn):
        
        px = float(new_co.split(',')[3])
        py = float(new_co.split(',')[4])
        pz = float(new_co.split(',')[5])
        p.co = (float((px - psx) / 100), float((py -psy) / 100), float((pz - psz) / 100), 1.0)

    #if add_elev != 0:
    for i in range (1,len(pn)):
        spline.points[i-1].co = spline.points[i].co

    # create curve object
    obj = bpy.data.objects.new('RoutePath', crv) 
    
    
    
    # align path to surface of the globe 
    obj.rotation_euler[1] = math.radians(90-flng)
    obj.rotation_euler[2] = math.radians(flat)


    bpy.data.collections['Collection'].objects.link(obj)

    #re-align to global system
    bpy.ops.object.empty_add(type='SINGLE_ARROW', location=(0,0,0)) # create empty container
    ges_path = bpy.context.selected_objects[0]
    ges_path.name = "_GES_PATH"

    loc_src, rot_src, scale_src = obj.matrix_world.decompose()
    loc_dst, rot_dst, scale_dst = ges_path.matrix_world.decompose()

    axis = Vector((0.0, 0.0, 1.0))
    z1 = rot_src @ axis
    z2 = rot_dst @ axis
    q = z2.rotation_difference(z1)

    # set rotation based on object matrix
    ges_path.matrix_world = (
        Matrix.Translation(loc_dst) @
        (q @ rot_dst).to_matrix().to_4x4() @
        scale_from_vector(scale_dst)
    )

    # change x,y to negative values of x,y
    ges_path.rotation_euler[0] = -ges_path.rotation_euler[0]
    ges_path.rotation_euler[1] = -ges_path.rotation_euler[1]
    
#    if add_elev !=0:
    # creates anchor object - used to ensure path remains at height
    bpy.ops.object.empty_add(type='SINGLE_ARROW', location=(0,0,0)) # create empty container
    ges_start = bpy.context.selected_objects[0]
    ges_start.name = "Anchor Empty"
    ges_start.parent = ges_path
    ges_start.parent_type = 'OBJECT'
   
        
    # reset rotation on obj
    obj.rotation_euler[1] = math.radians(0)
    obj.rotation_euler[2] = math.radians(0)

    # add object to parent
    obj.parent = ges_path
    obj.parent_type = 'OBJECT'


    
    obj.data.bevel_depth = bpy.context.scene.GES_OT_Path.v_bevel
   
    ges_path.location = sn.matrix_world.to_translation()

    domData.unlink()  
    
def newkml():
    hcolor = rgb_to_hex (bpy.context.scene.GES_OT_Path.v_xcolor)
   
    
    xfilename = bpy.path.abspath(bpy.context.scene.GES_OT_Path.p_kml)
    domData = parse(xfilename)
    coor = domData.getElementsByTagName("coordinates")
    pl = coor[0].firstChild.nodeValue.strip()
    
    # get coordinates
    co = ""
    pt = pl.split(' ')
    for i in range (0,len(pt)):
        plat = float(pt[i].split(',')[0])
        plng = float(pt[i].split(',')[1])
        co += pt[i].split(',')[0] + "," + pt[i].split(',')[1] + "," + str(bpy.context.scene.GES_OT_Path.v_xheight) + " "
    
    rootNode = ElementTree.Element('Document')
    
    elementNode = ElementTree.Element('name')
    rootNode.append(elementNode)
    
    
    elementNode.text =  (bpy.context.scene.GES_OT_Path.p_exp).replace(".kml","")
    
    elementNode = ElementTree.Element('Style')
    rootNode.append(elementNode)
    elementNode.attrib['id'] = "main_style"
    
    elementNode2 = ElementTree.Element('LineStyle')
    elementNode.append(elementNode2)
    
    if str(bpy.context.scene.GES_OT_Path.v_pwidth) == "True":
        elementNode3 = ElementTree.Element('gx:physicalWidth')
        elementNode2.append(elementNode3)
        elementNode3.text =  str(bpy.context.scene.GES_OT_Path.v_xwidth)
     
    if str(bpy.context.scene.GES_OT_Path.v_pwidth) != "True":
        elementNode3 = ElementTree.Element('width')
        elementNode2.append(elementNode3)
        elementNode3.text =  str(bpy.context.scene.GES_OT_Path.v_xwidth)
    
    
    elementNode3 = ElementTree.Element('color')
    elementNode2.append(elementNode3)
    elementNode3.text = "ff" + hcolor
    
    elementNode2 = ElementTree.Element('PolyStyle')
    elementNode.append(elementNode2)
    
    elementNode3 = ElementTree.Element('outline')
    elementNode2.append(elementNode3)
    elementNode3.text = "0" #str(bpy.context.scene.GES_OT_Path.v_xwidth)
    
    elementNode3 = ElementTree.Element('color')
    elementNode2.append(elementNode3)
    elementNode3.text = "ff" + hcolor
    
    elementNode = ElementTree.Element('Placemark')
    rootNode.append(elementNode)
    
    elementNode2 = ElementTree.Element('name')
    elementNode.append(elementNode2)
    elementNode2.text = 'ModifiedRoute'
    
    elementNode2 = ElementTree.Element('styleUrl')
    elementNode.append(elementNode2)
    elementNode2.text = '#main_style'
    
    elementNode2 = ElementTree.Element('LineString')
    elementNode.append(elementNode2)
    
    elementNode3 = ElementTree.Element("extrude")
    elementNode2.append(elementNode3)
    elementNode3.text = "1"
    
    elementNode3 = ElementTree.Element("tessellate")
    elementNode2.append(elementNode3)
    elementNode3.text = "1"
    
    elementNode3 = ElementTree.Element("altitudeMode")
    elementNode2.append(elementNode3)
    if str(bpy.context.scene.GES_OT_Path.v_xheight) == "0":
        elementNode3.text = "clampToGround"
    elif str(bpy.context.scene.GES_OT_Path.v_xheight) != "0":
        elementNode3.text = "relativeToGround"
        
    elementNode3 = ElementTree.Element("coordinates")
    elementNode2.append(elementNode3)
    elementNode3.text = co
    
    prettyPrint(element=rootNode)
    xmlText = ElementTree.tostring(rootNode)
   
    addext = ""
    if ".kml" not in bpy.context.scene.GES_OT_Path.p_exp:
        addext = ".kml"
        
    outputPath = bpy.path.abspath(bpy.context.scene.GES_OT_Path.p_expfolder + bpy.context.scene.GES_OT_Path.p_exp + addext)
    
    headertext = '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">'
    fileObject = open(outputPath, 'w')
    fileObject.write(headertext + "\n" + xmlText.decode('utf8') + "</kml>") 
    fileObject.close()


def rgb_to_hex(color):

    strip_n_pad = lambda stp: str(stp[2:]).zfill(2) 
    zcol = "".join([strip_n_pad(hex(int(col * 255))) for col in color])
    rcol = zcol[4:6] + zcol[2:4] + zcol[0:2] # earth format
   
    return rcol

def prettyPrint(element, level=0):
    '''
    Printing in elementTree requires a little massaging
    Function taken from elementTree site:
    http://effbot.org/zone/element-lib.htm#prettyprint

    '''
    indent = '\n' + level * '  '
    if len(element):
        if not element.text or not element.text.strip():
            element.text = indent + '  '

        if not element.tail or not element.tail.strip():
            element.tail = indent

        for element in element:
            prettyPrint(element, level + 1)

        if not element.tail or not element.tail.strip():
            element.tail = indent

    else:
        if level and (not element.tail or not element.tail.strip()):
            element.tail = indent

    return element

    
def register():
    bpy.utils.register_class(GES_PT_ImportPanel)
    bpy.utils.register_class(GES_PT_KMLPanel)
    bpy.utils.register_class(GES_PT_SubKML)
    bpy.utils.register_class(GES_PT_InfoPanel)
    bpy.utils.register_class(GES_OT_Path)
    bpy.utils.register_class(preKML)
    bpy.utils.register_class(preGES)
    bpy.utils.register_class(isvoid)
    
    bpy.types.Scene.GES_OT_Path = bpy.props.PointerProperty(type=GES_OT_Path)
    
def unregister():
    bpy.utils.unregister_class(GES_PT_ImportPanel)
    bpy.utils.unregister_class(GES_PT_KMLPanel)
    bpy.utils.unregister_class(GES_PT_SubKML)
    bpy.utils.unregister_class(GES_PT_InfoPanel)
    bpy.utils.unregister_class(GES_OT_Path)
    bpy.utils.unregister_class(preKML)
    bpy.utils.unregister_class(preGES)
    bpy.utils.unregister_class(isvoid)
    
if __name__ == "__main__":
    register() 