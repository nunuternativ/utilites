import sys
import os
import shutil
import argparse
import json
import subprocess

import pymel.core as pm
from rf_utils import cask


def setup_parser(arguments, title):
    parser = argparse.ArgumentParser(description=title,formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    for key,value in arguments.items():
        parser.add_argument('-%s' % key, dest=value['dest'],type=type(value["default"]), help = value["help"], default = value["default"] )
    return parser

def parse(arguments=None,title=None):
    if arguments is None:
        return None
    if type(arguments) is not type({}):
        if arguments.endswith('.json'):
            with open(arguments) as data_file:
                arguments = json.load(data_file)
    parser = setup_parser(arguments, title)
    return parser

def getABCGeo(abcArc):
    exit = False
    objs = [abcArc.top]
    result = {}  # {path: object}
    while not exit:
        next_objs = []
        for o in objs:
            children = o.children.values()
            for c in children:
                if c.type() == 'PolyMesh':
                    xform = c.parent
                    fullPath = xform.path()
                    result[fullPath] = xform
                else:
                    next_objs.append(c)
        if next_objs:
            objs = next_objs
        else:
            exit = True 

    return result

def stipNamespace(geos):
    newDict = {}
    for key, value in geos.iteritems():
        pathSplits = key.split('/')
        fullPath = '/'.join([p.split(':')[-1] for p in pathSplits])
        newDict[fullPath] = value
    return newDict

def checkGeos(srcGeos, desGeos):
    # check for same number of geos
    if len(srcGeos) != len(desGeos):
        print 'Different number of objects'
        return False

    # strip namespace
    srcGeos = stipNamespace(srcGeos)
    desGeos = stipNamespace(desGeos)

    result = True
    for s_path, s_tr in srcGeos.iteritems():
        # print s_path
        if s_path not in desGeos:
            print 'Missing geo: %s' %s_path
            result = False
            continue
        d_tr = desGeos[s_path]

        # get the shape
        s_geo = s_tr.children.values()[0]
        d_geo = d_tr.children.values()[0]

        s_meshInds = list(s_geo.properties['.geom/.faceIndices'].get_value())
        d_meshInds = list(d_geo.properties['.geom/.faceIndices'].get_value())

        s_fCounts = list(s_geo.properties['.geom/.faceCounts'].get_value())
        d_fCounts = list(d_geo.properties['.geom/.faceCounts'].get_value())

        if s_meshInds !=  d_meshInds or s_fCounts !=  d_fCounts:
            print 'Different topology: %s' %s_path
            result = False
            continue

    return result

def getGeoGrpFromArc(arc):
    for path, obj in zip(arc.top.children.keys(), arc.top.children.values()):
        if path.endswith('Geo_Grp') and isinstance(obj, cask.Xform):
            return arc.top.children[path]

def toLocal(path):
    homePath = os.environ['HOME']
    baseName = os.path.basename(path)
    return os.path.join(homePath, baseName)

def main(source, destination):
    destination = destination.replace('\\', '/')
    if not os.path.exists(destination):
        print 'Destination path does not exists: %s' %destination
        return

    local_des = toLocal(destination)
    shutil.copyfile(destination, local_des)
    desArc = cask.Archive(local_des)

    # get the source abc path(asset GEO) from destination abc's memeName attr
    desGeoGrp = getGeoGrpFromArc(desArc)
    if not desGeoGrp:
        print 'Cannot find Geo_Grp in %s' %destination
        return

    srcArc = cask.Archive(source)

    # get the source geos
    src_geos = getABCGeo(srcArc)

    # get the destination geos
    des_geos = getABCGeo(desArc)

    # geo checks
    check_result = checkGeos(src_geos, des_geos)
    print 'Geo check result: %s' %check_result


    if check_result:
        print 'Geos are matching between ABCs, merging with Cask...'
        # do transfer from abc to abc 
        for s_path, d_path in zip(sorted(src_geos.keys()), sorted(des_geos.keys())):
            try:
                src_mesh = srcArc.top.children[s_path].children.values()[0]
                des_mesh = desArc.top.children[d_path].children.values()[0]
            except:
                continue
            # get UV values from source abc file
            uv_props = None
            try:  # has to be safe in case the src geo has no UV
                uv_props = src_mesh.properties['.geom/uv']
            except: 
                pass

            des_geom = des_mesh.properties['.geom']
            if uv_props:
                if 'uv' not in des_geom.properties:  # if there's no UV property in this geom, add one
                    des_geom.add_property(cask.Property(name='uv'))
                # set the UV
                des_geom.properties['uv'] = uv_props 
            else: # remove uv if the source geo doesn't have UV
                if 'uv' in des_geom.properties:
                    des_geom.properties['uv'].clear_properties()
                    des_geom.properties['uv'].close()
        
        # write to local
        print 'Writing ABC to Local: %s' %destination
        desArc.write_to_file(destination)
        srcArc.close()
        desArc.close()


if __name__ == "__main__":
    print ':::::: Transfer ABC UVs ::::::'
    arguments = {
                 's': {'dest': 'source', 'help': 'The source ABC file path (model abc)', 'default': ''},
                 'd': {'dest': 'destination', 'help': 'The destination ABC file path (shot abc)', 'default': ''}
                 }
    parser = parse(arguments,'Transfer ABC UVs')
    params = parser.parse_args()
    main(params.source, params.destination)

'''

"C:\\Program Files\\Autodesk\\Maya2017\\bin\\mayapy.exe" "D:\\dev\\core\\rf_utils\\transferAbcUV.py" -s "D:\\__playground\\abc\\src.abc" -d "D:\\__playground\\abc\\des.abc"

'''