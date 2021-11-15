#    Copyright (c) 2021 imagiscope

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
    "version": (1, 2, 0),
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

import numpy
 
                
class GES_OT_Path(bpy.types.PropertyGroup):
    p_data: bpy.props.StringProperty(name="0000",subtype='FILE_PATH',default=r"")
    p_movie: bpy.props.StringProperty(name="data",subtype='FILE_PATH',default=r"")
    p_kml: bpy.props.StringProperty(name="kml",subtype='FILE_PATH',default=r"")
    p_refdata: bpy.props.StringProperty(name="refdata",subtype='FILE_PATH',default=r"")
    
    p_objexpfolder: bpy.props.StringProperty(name="expdata",subtype='DIR_PATH',default=r"//")
    p_objexp: bpy.props.StringProperty(name="expdata",subtype='FILE_NAME',default=r"ObjectKML")
    
    v_curve: bpy.props.EnumProperty(name="Curve",items=[('NURBS',"Nurbs",""),('POLY',"Poly","")])
    
    def trackitems(self,context):
        t_trks = []
        objects = bpy.data.objects["_GES_WORLD"].children
        for obj in objects:
            
            if obj.type == "MESH":
                if  obj.data.name[0:4] == "Plan": #mod for some international languages
                    t_trks.append(( obj.name, obj.name,""))
        
        return t_trks
    v_snapto: bpy.props.EnumProperty(
        name = "Snap to",
        description = "Snap to TrackPoint in _GES_WORLD",
        items =  trackitems 
    )
    
    v_terrain: bpy.props.BoolProperty(name="Follow Terrain",description="Align the KML route with supplied JSON TrackPoints.", default = True) 
    
    v_elevation: bpy.props.IntProperty(name="Add Elevation (m)", default=0, min=-100, max=10000, 
        description="Add elevation to Route (0 is none, 1000 = 1km, 100000 = 10km)" )
        
    v_reduce: bpy.props.IntProperty(name="Point Reduction", default=2, min=0, max=100, 
        description="Reduce KML points based on clustering (1 is less reduction, 100 is more reduction)" )
    v_prox: bpy.props.IntProperty(name="Match Proximity (m)", default=1, min=1, max=1000,
        description="Set altitude based on meters (approx) to trackpoint (1 is closer, 100 more forgiving)")
    
    v_bevel: bpy.props.FloatProperty(name="Bevel Depth", default=0, min=0, max=5, 
        description="Starting Route Bevel (0 = none)" )
    
    v_objlinecolor: bpy.props.FloatVectorProperty(name="Line Color", subtype='COLOR', default=[0.0,1.0,0.0])
    v_objfillcolor: bpy.props.FloatVectorProperty(name="Fill Color", subtype='COLOR', default=[1.0,1.0,1.0])
    
    v_objlinewidth: bpy.props.IntProperty(name="Line Width", default=0, min=0, max=50, 
        description="Width of line (0 = none)" )
        
   
    v_objfillopacity: bpy.props.IntProperty(name="Fill Opacity", default=100, min=1, max=100)
    
    def nontrackitems(self,context):
        t_trks = []
        objects = bpy.context.scene.objects
        for obj in objects:
            nonges = False # Only display root obects - no cameras, no lights, no GES items
            if (obj.parent) == None:
                nonges = True
            if (obj.type) == 'LIGHT' or (obj.type) == 'CAMERA':
                nonges = False
            if obj.name[0:5] != "_GES_" and nonges == True and obj.name[0:7] != "Marker_" :
                t_trks.append(( obj.name, obj.name,""))
            
        return t_trks
    v_mtemplate: bpy.props.EnumProperty(
        name = "Template",
        description = "Marker Template",
        items =  nontrackitems 
    )
    v_mlookat: bpy.props.BoolProperty(name="Face to Camera",description="Align the Marker to the Camera.", default = True) 

    
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


# Object to KML panel             
class GES_PT_ObjectKMLPanel(bpy.types.Panel):
    bl_label = "Export Object as KML"
    bl_idname = "GES_PT_ObjectKMLPanel"
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
        
        if hasGES == 1:
            selobj = bpy.context.active_object
           
            if selobj:
                
                if selobj.type == "MESH" or selobj.type == "CURVE":
                    layout = self.layout
                    
                    row = layout.row()
                    
                    row.label(text="Selected: " + selobj.name)
                    if selobj.type == "CURVE":
                        row = layout.row()
                        row.label(text="- Curve Optimized")    
                    row = layout.box()
                    row.prop(bpy.context.scene.GES_OT_Path, "v_objfillcolor")
                    row.prop(bpy.context.scene.GES_OT_Path, "v_objfillopacity")
                    row = layout.box()
                    row.prop(bpy.context.scene.GES_OT_Path, "v_objlinecolor")
                    row.prop(bpy.context.scene.GES_OT_Path, "v_objlinewidth")
                    row = layout.row()
                    row.label(text="Destination Folder:")
                    row = layout.row()
                    row.prop(bpy.context.scene.GES_OT_Path, "p_objexpfolder", text="")
                    row = layout.row()
                    row.label(text="Filename:" )
                    row = layout.row()
                    row.prop(bpy.context.scene.GES_OT_Path, "p_objexp", text="")
                    row = layout.row()
                    row.operator("scene.pre_objkml", text="Export Object as KML" ).action = "pri"
                else:
                    layout = self.layout
               
                    row = layout.row()
                    row.label(text="Invalid: Mesh or Curve Only")
                    row = layout.row()
                    row.label(text="Try Converting to Mesh")
            else:
                layout = self.layout
                row = layout.row()
                row.label(text="Select Object", icon="LOCKED")
                row = layout.row()   
           
        if hasGES == 0: # 'disable' section if there is no imported project
            layout = self.layout
            row = layout.row()
            row.label(text="Import Earth Studio first", icon="LOCKED")
            row = layout.row()      
       
    
# KML import panel               
class GES_PT_KMLPanel(bpy.types.Panel):
    bl_label = "Import KML Route" # Import/Export"
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
                  
# Marker Panel
class GES_PT_MarkerPanel(bpy.types.Panel):
    bl_label = "Trackpoint Marker Tool"
    bl_idname = "GES_PT_MarkerPanel"
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
            row.label(text="Add Marker for each Trackpoint")
            row = layout.row()
            row.label(text="1. Create Template Marker")
            row = layout.row()
            row.label(text="   - Parent all objects to object/empty")
            row = layout.row()
            row.label(text="   - Text Object will use Trackpoint name")
            row = layout.row()
            row.label(text="   - Origin of Parent is rotation point")
            row = layout.row()
            row.label(text="2. Select Template Marker")
            row = layout.row()
            row.label(text="3. Use 'Face..' to always point to Camera")
            row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_mtemplate")
            
            row = layout.row()
            row.prop(bpy.context.scene.GES_OT_Path, "v_mlookat")
           
            row = layout.row()
            
           
            row.operator("scene.pre_marker", text="Create Markers" )
               
           
        if hasGES == 0: # 'disable' section if there is no imported project
            layout = self.layout
            row = layout.row()
            row.label(text="Import Earth Studio first", icon="LOCKED")
            row = layout.row()
            
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
class preobjKML(bpy.types.Operator):
    bl_idname = "scene.pre_objkml"
    bl_label = "GES PRE KML"
    
    action: EnumProperty(items=[('pri','pri','pri'),('sec','sec','sec')])
        
    def execute(self, context):
        if self.action == "pri":
            objecttokml()
        
        return {'FINISHED'}


# check files   
class preKML(bpy.types.Operator):
    bl_idname = "scene.pre_kml"
    bl_label = "GES PRE KML"
    
    action: EnumProperty(items=[('pri','pri','pri'),('sec','sec','sec')])
        
    def execute(self, context):
        if self.action == "pri":
            importkml()
       
        return {'FINISHED'}


class preGES(bpy.types.Operator):
    bl_idname = "scene.pre_ges"
    bl_label = "GES PRE GES"
    
    def execute(self, context):
        fa = bpy.context.scene.GES_OT_Path.p_movie
        fb  = bpy.context.scene.GES_OT_Path.p_data
        if fa != '' and fb != '':
            importges()
            objects = bpy.context.scene.objects
            hasGES = 0
            for obj in objects:
                if obj.name == "_GES_WORLD":
                    hasGES=1
            if hasGES == 1:  
                t_trks = []
                objects = bpy.data.objects["_GES_WORLD"].children
                for obj in objects:
                    if obj.type == "MESH":
                        if  obj.data.name[0:4] == "Plan":
                            t_trks.append(( obj.name, obj.name,""))
                v_snapto = bpy.props.EnumProperty(
                     name = "Snap to",description = "Snap to TrackPoint in _GES_WORLD",items = t_trks  )

 
        return {'FINISHED'}

# check files   
class preMarker(bpy.types.Operator):
    bl_idname = "scene.pre_marker"
    bl_label = "GES PRE MARKER"
    
           
    def execute(self, context):
        makemarkers()
        return {'FINISHED'}
        
# Info Popup
def ShowMessageBox(message = "", title = "Information", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text = message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)
          
def importges():
    
    cam = bpy.context.scene.camera
    if not cam: # add a camera if deleted
        
        cam_d = bpy.data.cameras.new(name='Camera')
        cam_o = bpy.data.objects.new('Camera', cam_d)
        bpy.data.collections['Collection'].objects.link(cam_o)
        cam = cam_o
        bpy.context.scene.camera = cam
        
    scene = bpy.context.scene
    
    # load JSON file for evaluation
    # Sample format: jfilename = "D:/Local/Project/Beach/beach/beach.json"
    jfilename = bpy.path.abspath(bpy.context.scene.GES_OT_Path.p_data)

    jfile = open(jfilename,'r')
    camdata = json.load(jfile)
    jfile.close
    hasTrack = False
    for cd in camdata:
        if cd == "trackPoints":
            hasTrack=True
     # check trackpoints
    if hasTrack == False:
        ShowMessageBox( "Ensure Earth Studio project has Trackpoints (min 1) and export JSON file with trackpoints.","Import Aborted - No Trackpoints Found","ERROR") 
    else:
        
        # load the GES render files as background for camera
        # Sample format: ifiles = "D:/Local/Project/Beach/beach/footage/beach_0000.jpeg"
        ifiles = bpy.path.abspath(bpy.context.scene.GES_OT_Path.p_movie)

        img = bpy.data.movieclips.load(ifiles)
        cam.data.show_background_images = True
        cam.data.clip_end = 10000

        bg = cam.data.background_images.new()
        bg.clip = img
        bg.alpha = 1
        bg.source = "MOVIE_CLIP"

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
            rlng = (89.9999*2) * (rlng ) - 89.9999
            
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
            trk['X'] = px
            trk['Y'] = py
            trk['Z'] = pz
            trk['LAT'] = rlng # real lat - mislabeled
            trk['LNG'] = rlat # real lng - mislabeled
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
    
    objects = bpy.data.objects["_GES_WORLD"].children
    v_zerotrack = "" #initial center plane
    for obj in objects:
        if obj.type == "MESH":
            if  obj.data.name[0:5] == "Plane":
                if v_zerotrack == "":
                    v_zerotrack = obj.name
                    
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
                pl = pl.replace("\n","")
                while pl.find("  ") != -1:
                    pl = pl.replace ("  "," ")
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
    print (pl)
    
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
                    xlng = (89.9999*2) * (tlng ) - 89.9999
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
    print (v_zerotrack)
    obj.rotation_euler[1] = bpy.data.objects[v_zerotrack].rotation_euler[1] #math.radians(90-flng)
    obj.rotation_euler[2] = bpy.data.objects[v_zerotrack].rotation_euler[2] #math.radians(flat)


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

def makemarkers():
    mkrcnt = 0 # Counter for information

    # Load template objects
    mk = bpy.data.objects[bpy.context.scene.GES_OT_Path.v_mtemplate]
    
    # Create new collection
    if "GESMarkers" not in bpy.data.collections:
        collection = bpy.data.collections.new("GESMarkers")
        bpy.context.scene.collection.children.link(collection)
        
    # Cycle through GES trackpoints (except hidden ones)
    objects = bpy.data.objects["_GES_WORLD"].children 

    for obj in objects:
        if obj.type == "MESH":
            if  obj.data.name[0:5] == "Plane" and obj.visible_get():
                # Trackpoint name and clean up
                newtext = obj.name
                spx = newtext.split(' ')[0].replace(".","")
                if spx.isdecimal():
                    newtext = newtext.replace(spx + ". ","")
                # create collection for marker (for easier hiding)  
                #marker_collection = bpy.data.collections.new('Marker_' + newtext)
                if mk.type == "EMPTY":
                    # Create new empth
                    mk2 = bpy.data.objects.new('Marker_' + newtext, None)
                else: 
                     # Create copy of marker
                    mk2 = bpy.data.objects.new('Marker_' + newtext, mk.data.copy())
                # Set location, scale and rotation for Parent object
                mk2.location = obj.matrix_world.translation
                mk2.scale = mk.scale
                mk2.rotation_euler = mk.rotation_euler
                
                # Add track to camera
                if str(bpy.context.scene.GES_OT_Path.v_mlookat) == "True":
                    constraint = mk2.constraints.new(type='TRACK_TO')
                    constraint.target = bpy.data.objects['Camera']
                    constraint.track_axis="TRACK_Z"
                # Move (link) to Collection
                #marker_collection.objects.link(mk2)
                # Clone children (really, we're doing that)
                kids = mk.children              
                for kid in kids:
                    
                    k2 = bpy.data.objects.new( kid.name + '_' + newtext, kid.data.copy())
                    k2.matrix_local = kid.matrix_local
                    if k2.type == 'FONT': # if a text object, set the text value to trackpoint name
                        k2.data.body = newtext
                    k2.parent = mk2  
                    # Move (link) object to marker collection 
                    #marker_collection.objects.link(k2)
                    mk2.objects.link(k2)
                # Move (link) all into main collection   
                #bpy.data.collections["GESMarkers"].children.link(marker_collection)
                bpy.data.collections["GESMarkers"].children.link(mk2)
                mkrcnt += 1
    ShowMessageBox( str(mkrcnt) + " Markers Created") 

def objecttokml():

    wobj = bpy.data.objects['_GES_WORLD']
    anc = wobj.children[0] #load first trackpoint
    ancp = wobj

    src_obj = bpy.context.active_object 
    C = bpy.context
    
    # create a copy of object to modify for export
    obj = src_obj.copy()
    obj.data = src_obj.data.copy()
    obj.animation_data_clear()
    C.collection.objects.link(obj)

    src_obj.select_set(False)
    obj.select_set(True) #select the text obj
    bpy.context.view_layer.objects.active = obj
    bpy.context.view_layer.update()
    rmode = False
    
    # if object is a curve (a path) then covert the curve to a mesh
    if obj.parent:
        if obj.parent.name[0:9] == "_GES_PATH":
            obj.data.splines[0].resolution_u = 2

            override = bpy.context.copy()
            bpy.ops.object.convert(override,target='MESH')  
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            rmode = True
                       
    bpy.data.objects[src_obj.name].select_set(False)
    bpy.data.objects[obj.name].select_set(True)

    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    
    # apply world transformation (#1) - using 1/100 scale and lat/long euler
    bpy.ops.transform.resize(value=(.10, .10, .10))
    obj.rotation_euler[2] = anc.rotation_euler[2]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
  
    earth = 6371010.1 #earth radius, in meters
    t_location = wobj.matrix_world.inverted() @ obj.location
    # get object starting location in world space
    tx = t_location.x 
    ty = t_location.y 
    tz = t_location.z 

    pn = []
    fn = []

    bpy.context.view_layer.update()
  
    # create inverted matrix for world and anchor
    winvert =  wobj.matrix_world.inverted() 
    ainvert = anc.matrix_world.inverted()

    # cycle faces and extract vertices data with world and anchor matrix mutiplied
    for f in obj.data.polygons:
        pn.append("face")
        for v in f.vertices: 
            if rmode == True:
                t_vertex = winvert @ ainvert @ obj.data.vertices[v].co 
            else:
                t_vertex = winvert @ ainvert @ obj.data.vertices[v].co 
            pn.append(str(tx + t_vertex.x ) + "," + str(ty + t_vertex.y ) + "," + str(tz + t_vertex.z ))
         
    firstface=True
    startagain ="0"
  
    # create kml header
    fn.append ("<?xml version='1.0' encoding='UTF-8'?><kml xmlns='http://www.opengis.net/kml/2.2'>")
    fn.append ("<Document>")
    fn.append ("<name>Exported from Blender</name>")
    fn.append ('<Style id="xstyle">')
    fn.append ("<PolyStyle>")
    fopacity = "00"
    if bpy.context.scene.GES_OT_Path.v_objfillopacity != 0:
        v = int(bpy.context.scene.GES_OT_Path.v_objfillopacity * 255 / 100)
        fopacity = hex(v)[2:]
    
    fcolor = str(rgb_to_hex (bpy.context.scene.GES_OT_Path.v_objfillcolor))
    
    fn.append ("<color>" + fopacity + fcolor +"</color>")
    ol = "1"
    if str(bpy.context.scene.GES_OT_Path.v_objlinewidth) == "0":
        ol = "0"
    fn.append ("<outline>" + ol +"</outline>")
    fn.append ("<fill>1</fill>")
    fn.append ("</PolyStyle>")
    fn.append ("<LineStyle>")

    lncolor = str(rgb_to_hex (bpy.context.scene.GES_OT_Path.v_objlinecolor))

    fn.append ("<color>FF" + lncolor +"</color>")
    fn.append ("<width>" + str(bpy.context.scene.GES_OT_Path.v_objlinewidth) +"</width>")
    fn.append ("</LineStyle>")
    fn.append ("</Style>")
    fn.append ("<Placemark><name>" + str(obj.name) + "</name><visibility>1</visibility>")
    fn.append("<styleUrl>#xstyle</styleUrl>") 
    fn.append ("<MultiGeometry>")

    # write point parameters (lat/long/alt) for each face
    for f in pn:
        if f == "face":
            # for each face, start a new polygon
            if startagain != "0":
                fn.append (startagain)
                startagain = "0"
            if firstface == False: 
                fn.append ("</coordinates></LinearRing></outerBoundaryIs>")
                fn.append ("</Polygon>")
            fn.append ("<Polygon><extrude>0</extrude><altitudeMode>absolute</altitudeMode>")
            fn.append ("<outerBoundaryIs><LinearRing><coordinates>")
            firstface = False
            
        else:
            xoff = (float(f.split(',')[0]) * 100) + float(anc['X'])
            yoff = (float(f.split(',')[1]) * 100) + float(anc['Y'])
            zoff = (float(f.split(',')[2]) * 100) + float(anc['Z']) 
            
            lat = float(anc['LAT'])
            lon = float(anc['LNG'])

            edia2= earth + .00001 # used for non-spherical calculations - setting to small difference as GES uses globe
            
            # reverse blender coordinate infomation into lat/long/alt - fancy math (thanks google)
            f = (earth - edia2) / earth
            e_sq = f * (2 - f)                       
            eps = e_sq / (1.0 - e_sq)
            p = math.sqrt(xoff * xoff + yoff * yoff)
            q = math.atan2((zoff * earth), (p * edia2))
            sin_q = math.sin(q)
            cos_q = math.cos(q)
            sin_q_3 = sin_q * sin_q * sin_q
            cos_q_3 = cos_q * cos_q * cos_q
            phi = math.atan2((zoff + eps * edia2 * sin_q_3), (p - e_sq * earth * cos_q_3))
            lam = math.atan2(yoff, xoff)
            v = earth / math.sqrt(1.0 - e_sq * math.sin(phi) * math.sin(phi))
            h   = (p / math.cos(phi)) - v

            ylat = math.degrees(phi)
            ylon = math.degrees(lam)

            fn.append(str(ylon) + "," + str(ylat) + "," + str(h))
            if startagain == "0":
                startagain = str(ylon) + "," + str(ylat) + "," + str(h)

    if startagain != "0":
        fn.append (startagain)  
    # kml footer       
    fn.append ("</coordinates></LinearRing></outerBoundaryIs>")
    fn.append ("</Polygon>")
    fn.append ("</MultiGeometry></Placemark></Document></kml>")

    strout = ""
    # spit out array into string
    for f in fn:
        strout += (str(f) + " ")

    # save the file
    outputPath = bpy.path.abspath(bpy.context.scene.GES_OT_Path.p_objexpfolder + bpy.context.scene.GES_OT_Path.p_objexp + ".kml")
    fileObject = open(outputPath, 'w')
    fileObject.write(strout) 
    fileObject.close()
    
    # remove copied object
    bpy.ops.object.delete()

    # set focus back to original object
    bpy.data.objects[src_obj.name].select_set(True)
    ShowMessageBox( str(bpy.context.scene.GES_OT_Path.p_objexp) + ".kml saved.") 
    
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
    bpy.utils.register_class(GES_PT_ObjectKMLPanel)
    bpy.utils.register_class(GES_PT_MarkerPanel)
    bpy.utils.register_class(GES_PT_InfoPanel)
    bpy.utils.register_class(GES_OT_Path)
    bpy.utils.register_class(preobjKML)
    bpy.utils.register_class(preKML)
    bpy.utils.register_class(preGES)
    bpy.utils.register_class(preMarker)
    bpy.utils.register_class(isvoid)
    
    bpy.types.Scene.GES_OT_Path = bpy.props.PointerProperty(type=GES_OT_Path)
    
def unregister():
    bpy.utils.unregister_class(GES_PT_ImportPanel)
    bpy.utils.unregister_class(GES_PT_KMLPanel)
    bpy.utils.unregister_class(GES_PT_ObjectKMLPanel)
    bpy.utils.unregister_class(GES_PT_MarkerPanel)
    bpy.utils.unregister_class(GES_PT_InfoPanel)
    bpy.utils.unregister_class(GES_OT_Path)
    bpy.utils.unregister_class(preobjKML)
    bpy.utils.unregister_class(preKML)
    bpy.utils.unregister_class(preGES)
    bpy.utils.unregister_class(preMarker)
    bpy.utils.unregister_class(isvoid)
    
if __name__ == "__main__":
    register() 