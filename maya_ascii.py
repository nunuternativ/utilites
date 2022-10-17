import os
import collections
import re
import time
from collections import defaultdict
from ast import literal_eval
from timeit import repeat
from functools import cache

def invalidate_cache(func):
    def wrapper(*arg, **kwArgs):
        res = func(*arg, **kwArgs)
        if res:
            MayaAscii.ls.cache_clear()
        return res
    return wrapper

class MayaAscii(object):
    ''' Maya's ascii text editor class. Supports operation like open, save, query and some basic modification'''
    def __init__(self, path):
        self.path = path
        self._data = None
        
        self._joiner = '**_JOINER_**'

    def read(self):
        ''' Read and parse scene data. Must be called manually on every instance. '''
        data = collections.OrderedDict()
        with open(self.path, 'r') as f:
            ascii_lines = f.readlines()

            # collect line chunks
            line_chunk = []
            curr_cmd = ''

            # get the title comment from the begining of file
            data['title_comment'] = []

            for line in ascii_lines:
                if line.startswith('//'):
                    data['title_comment'].append(line)
                else:
                    break            

            # looping from the end of file to get end comment lines
            end_chunks = []  # need to be a list in case end comment contains multiple lines
            for line in reversed(ascii_lines):
                if line.startswith('//'):
                    end_chunks.append(line)
                else:
                    break

            # get actual lines to loop over
            if end_chunks:
                lines_to_loop = ascii_lines[len(data['title_comment']):(len(end_chunks)*-1)]
            else:
                lines_to_loop = ascii_lines[len(data['title_comment']):]

            for line in lines_to_loop:
                if line == '\n':
                    continue

                is_tabbed = line.startswith('\t')
                if line_chunk:
                    this_line_ends = line.endswith(';\n')
                    last_line_ends = line_chunk[-1].endswith(';\n')

                    # if the current line is tabbed
                    if is_tabbed:
                        if this_line_ends and last_line_ends:
                            line_chunk.append(line)
                        elif not this_line_ends and last_line_ends:
                            line_chunk.append(line)
                        else:
                            line_chunk[-1] += line 
                            
                    else:  # the current line isn't tabbed
                        data[curr_cmd].append(line_chunk)

                # it's the start of a chunk, ie requires, setAttr, ...
                if not is_tabbed:
                    try:
                        curr_cmd = line.split()[0]
                    except IndexError:
                        curr_cmd = line
                    if curr_cmd not in data:
                        data[curr_cmd] = []
                    line_chunk = [line]
                    
            data[curr_cmd].append(line_chunk)  # need to add the last line

            # add end comment
            data['end_comment'] = [end_chunks] if end_chunks else []

        self.data = data
        return data

    def write(self, path):
        ''' Save (write out) file

        Keyword arguments:
            path -- output path to save(str)
        '''
        with open(path, 'w') as f:
            for cmd, cmd_chunk in self.data.iteritems():
                for chunk in cmd_chunk:
                    for line in chunk:
                        f.write(line)

    # FIXME: would be good to cache this result for speed.  
    # see functools.cache
    @cache
    def frame_range(self):
        ''' Query the file's minimum, maximum, animation start and animation end frame

        Return: 
            dict -- {'min':frame, 'max':frame, 'ast':frame, 'aet':frame}
        '''
        result = {'min':None, 'max':None, 'ast':None, 'aet':None}
        if not self.data or not self.data.get('createNode'):
            return result

        for chunk in self.data['createNode']:
            if 'sceneConfigurationScriptNode' in chunk[0]:
                for line in chunk:
                    if 'playbackOptions' in line:
                        for flag in ('min', 'max', 'ast', 'aet'):
                            found = re.search('-%s [0-9]*' %flag, line)
                            if found:
                                frame = found.group().split()[-1]
                                result[flag] = float(frame)

        return result

    # FIXME: would be good to cache this result for speed, but you will need
    #  to invalidate the cache after modifying self.data 
    # see functools.cache
    @cache
    def ls(self, search='', types=tuple(), fullPath=True):
        '''List objects of types in the scene

        Keyword arguments:
            search -- regular expression for name search (str)
            types -- the types of objects to list (tuple[str])
            fullPath -- to return full path to the object or not

        Return:
            list[ tuple(chunk_number(int), name(str)) ]
        '''
        result = []
        if not self.data or not self.data.get('createNode'):
            return result
        if not isinstance(types, (list, tuple)):
            types = [types]
        if search:
            search = re.compile('^%s$' %search)

        dagTypes = ('transform', 'joint')
        for i, chunk in enumerate(self.data['createNode']):
            cmd_line = chunk[0]
            line_splits = cmd_line.split()
            curr_type = line_splits[1]
            if types and curr_type not in types:
                continue

            name = flag_string_value(line=cmd_line, flag='-n')
            if search:
                match = search.match(name)
                if not match:
                    continue

            if fullPath:
                parent = flag_string_value(line=cmd_line, flag='-p')
                if parent:
                    name = '%s|%s' %(parent, name)
                else:
                    if curr_type in dagTypes:
                        name = '|%s' %name
            result.append((i, name))

        return result

    @invalidate_cache
    def delete_node(self, search, types=tuple()):
        ''' Remove node from scene

        Keyword arguments:
            search -- regular expression for name search (str)
            types -- the types of objects to list (list[str])
        Return:
            list[int] -- line no. of deleted lines on success
        '''
        ls_results = self.ls(search=search, types=types)
        if not ls_results:
            return

        indices = [i[0] for i in ls_results]
        new_data = []
        for ci, chunk in enumerate(self.data['createNode']):
            if ci not in indices:
                new_data.append(chunk)

        self.data['createNode'] = new_data
        return indices

    @invalidate_cache
    def createNode(self, nodeType, name, parent=None, shared=False):
        ''' Create new node
        
        Keyword arguments:
            nodeType -- type of new node (str)
            name -- name of new node (str)
            parent -- name of parent of new node (str)
            shared -- new node being shared node or not (bool)
        Return:
            str -- the new lines used for createNode
        '''
        if not self.data:
            return

        new_lines = ['createNode %s -n "%s"' %(nodeType, name)]
        if shared:
            shared_str = '-s'
            new_lines.append(shared_str)
        if parent:
            parent_str = '-p "%s"' %(parent)
            new_lines.append(parent_str)
        new_line = ' '.join(new_lines)
        new_line += ';\n'
        if 'createNode' not in self.data:
            self.data['createNode'] = []

        self.data['createNode'].append([new_line])
        return new_line

    def addAttr(self, obj, shortName, attrType, longName='', niceName='', value=None, dv=None, miv=None, mxv=None, lock=False, keyable=True):
        ''' Add attribute to a node in the scene
        
        Keyword arguments:
            obj -- name of node to hold new attribute (str)
            shortName -- short name of the new attribute (str)
            attrType -- type of the new attribute (str)
            longName -- long name of the new attribute (str)
            niceName -- nice name of the new attribute (str)
            value -- value of the new attribute (dynamic types)
            dv -- default value (dynamic types)
            miv -- minimum value (dynamic types)
            mxv -- maximum value (dynamic types)
            lock -- lock the new attribute (bool)
            keyable -- new attribute is keyable (bool)
        Return:
            bool
        '''
        result = False
        if not self.data or not self.data.get('createNode'):
            return result

        simple_attr_types = ('short', 'long', 'float', 'double')
        new_chunk = []
        new_chunk_index = None
        line_index = 1
        for i, chunk in enumerate(self.data['createNode']):
            cmd_line = chunk[0]
            name = flag_string_value(line=cmd_line, flag='-n')
            if name == obj:
                for l, line in enumerate(chunk):
                    if line.startswith('\tsetAttr'):
                        line_index = l
                        break

                new_chunk = list(chunk)
                new_lines = ['\taddAttr -ci true -sn "%s"' %shortName]
                if not longName:
                    longName = shortName
                ln_str = '-ln "%s"' %longName
                new_lines.append(ln_str)

                if niceName:
                    nc_str = '-nn "%s"' %(niceName)
                    new_lines.append(nc_str)

                if dv != None:
                    dv_str = '-dv %s' %(dv)
                    new_lines.append(dv_str)
                if miv != None:
                    miv_str = '-min %s' %(miv)
                    new_lines.append(miv_str)
                if mxv != None:
                    mxv_str = '-max %s' %(mxv)
                    new_lines.append(mxv_str)

                if attrType in simple_attr_types:
                    type_str = '-at "%s"' %(attrType)
                else:
                    type_str = '-dt "%s"' %(attrType)
                new_lines.append(type_str)

                new_line_str = ' '.join(new_lines)
                new_line_str += ';\n'
                new_chunk.insert(line_index, new_line_str)
                new_chunk_index = i
                break

        if new_chunk:
            self.data['createNode'][new_chunk_index] = new_chunk
            # if value, 
            if value or lock or keyable:
                kw_args = {}
                if value:
                    kw_args['value'] = value
                if attrType and attrType not in simple_attr_types:
                    kw_args['attrType'] = attrType
                if lock:
                    kw_args['lock'] = lock
                if keyable:
                    kw_args['keyable'] = keyable
                self.setAttr(obj, shortName, **kw_args)
            return True
        else:
            return False

    def setAttr(self, obj, attr, value=None, attrType=None, lock=None, keyable=None):
        ''' Set attribute of a node to a new value
        
        Keyword arguments:
            obj -- name of node (str)
            attr -- name of the attribute (str)
            value -- value to set (dynamic types)
            attrType -- type of the attribute (str)
            lock -- lock the new attribute (bool)
            keyable -- new attribute is keyable (bool)
        Return:
            bool
        '''
        result = False
        if not self.data or not self.data.get('createNode'):
            return result

        bool_dict = {True: 'on', False: 'off'}
        new_chunk = []
        new_chunk_index = None
        for i, chunk in enumerate(self.data['createNode']):
            cmd_line = chunk[0]
            name = flag_string_value(line=cmd_line, flag='-n')
            if name == obj:
                new_chunk = list(chunk)
                new_lines = ['\tsetAttr']
                if lock != None:
                    lock_str = '-l %s' %(bool_dict[lock])
                    new_lines.append(lock_str)
                if keyable != None:
                    k_str = '-k %s' %(bool_dict[keyable])
                    new_lines.append(k_str)

                attr_str = '".%s"' %(attr)
                new_lines.append(attr_str)

                if attrType != None:
                    type_str = '-type "%s"' %(attrType)
                    new_lines.append(type_str)

                if value != None:
                    if isinstance(value, (str, unicode)):
                        value = '"%s"' %(value)
                    elif isinstance(value, (list, tuple)):
                        value = ' '.join([str(v) for v in value])
                    elif isinstance(value, bool):
                        value = bool_dict[value]
                    else:
                        value = str(value)
                    new_lines.append(value)
                new_line_str = ' '.join(new_lines)
                new_line_str += ';\n'

                # replace old setAttr line if exists
                for l, line in enumerate(chunk):
                    if line.startswith('\tsetAttr') and attr_str in line:
                        new_chunk[l] = new_line_str
                        break
                else:
                    new_chunk.append(new_line_str)
                new_chunk_index = i
                break

        if new_chunk:
            self.data['createNode'][new_chunk_index] = new_chunk
            return True
        else:
            return False

    def getAttr(self, obj, attr):
        ''' Get value of an attribute in a node
        
        Keyword arguments:
            obj -- name of node (str)
            attr -- name of the attribute (str)
        Return:
            bool
        '''
        result = None
        if not self.data or not self.data.get('createNode'):
            return result

        isSliced = bool(re.search('[[0-9]+:.*]', attr))
        for chunk in self.data['createNode']:
            cmd_line = chunk[0]
            name = flag_string_value(line=cmd_line, flag='-n')
            if name != obj:
                continue

            for line in chunk[1:]:
                if not line.startswith('\tsetAttr'):
                    continue

                line_splits = line.split(' ')
                attr_str = '".%s"' %attr
                if attr_str not in line:
                    continue
                    
                # get attribute type
                attr_type = flag_string_value(line, '-type')

                # it's a simple numeric type
                if not attr_type:
                    value = line_splits[-1]
                    value = value.replace('\n', '')
                    value = value.replace('\t', '')
                    value = value.replace(';', '')
                    value = value.replace('"', '')
                    # in case no value to set - setAttr -l on -k off ".tx";
                    if value != attr_str[1:-1]: 
                        value = eval_data_type(value)
                        return value
                else:
                    index = line_splits.index('"%s"' %attr_type)
                    raw_values = line_splits[(index+1):]
                    values = []

                    # strip unneccessary strings
                    for v in raw_values:
                        v = v.replace('\n', '')
                        v = v.replace('\t', '')
                        v = v.replace(';', '')
                        v = v.replace('"', '')
                        v = v.replace(' ', '')
                        if not v:
                            continue
                        values.append(v)

                    # convert data to python object
                    converted = []
                    for v in values:
                        vt = eval_data_type(v, attr_type)
                        converted.append(vt)

                    # strip the list if it's type string
                    if attr_type == 'string':
                        return ''.join(converted)
                    # int type
                    elif attr_type in ('short2', 'long2', 'float2', 'double2'):
                        result = []
                        pairs = []
                        for i, v in enumerate(converted):
                            pairs.append(v)
                            if i % 2:  # if it's equal number
                                result.append(pairs)
                                pairs = []
                        if not isSliced:
                            result = result[0]
                        return result
                    # float types
                    elif attr_type in ('short3', 'long3', 'float3', 'double3'):
                        result = []
                        coords = []
                        for i, v in enumerate(converted):
                            coords.append(v)
                            if (i+1)%3 == 0:  
                                result.append(coords)
                                coords = []
                        if not isSliced:
                            result = result[0]
                        return result
                    # 4 by 4 matrix type
                    elif attr_type == 'matrix' and len(converted) == 16:
                        return [converted[:3], converted[4:8], converted[8:12], converted[12:]]

                    return converted

    def nodeTypes(self):
        ''' Get a list of node types created in the scene '''
        result = set()
        if not self.data or not self.data.get('createNode'):
            return result

        for chunk in self.data['createNode']:
            cmd_line = chunk[0]
            line_splits = cmd_line.split()
            result.add(line_splits[1])

        return result

    def requires(self):
        ''' Get the list of plugins required by the scene 
        
        Return:
            list[tuple[plugin_name, plugin_version]]
        '''
        result = []
        if not self.data or not self.data.get('requires'):
            return result

        for chunk in self.data['requires']:
            cmd_line = chunk[0]
            line_splits = cmd_line.split()
            plugin_name = line_splits[-2]
            plugin_version = line_splits[-1]

            result.append((plugin_name, plugin_version))

        return result

    def listReferences(self):
        ''' List references created in the scene
        
        Return:
            dict[str, str] -- keys are: namespace, refNode, path
        '''
        result = []
        if not self.data or not self.data.get('file'):
            return result

        for i, chunk in enumerate(self.data['file']):
            combined_line = ''.join(chunk)
            if ' -r ' in combined_line:
                namespace = flag_string_value(line=combined_line, flag='-ns')
                refNode = flag_string_value(line=combined_line, flag='-rfn')

                splits = combined_line.split()
                path = splits[-1].replace(';', '')
                path = path.replace('\n', '')
                path = path.replace('"', '')
                result.append({'namespace': namespace, 
                                'refNode': refNode,
                                'path': path})

        return result

    def find_node(self, name):
        ''' Find chunk of data containing the node
        
        Keyword Arguments:
            name -- name of the node to find (str)
        Return:
            dict[str, str] -- key=cmd of the chunk, value=chunk
        '''
        result = collections.defaultdict(list)
        if not self.data:
            return result

        for cmd, chunks in self.data.iteritems():
            if cmd == 'createNode':
                for chunk in chunks:
                    combined_line = self._joiner.join(chunk)
                    node_name = flag_string_value(line=combined_line, flag='-n')
                    if node_name == name:
                        result[cmd].append(chunk)
            elif cmd in ('select', 'connectAttr', 'relationship'):
                for chunk in chunks:
                    combined_line = self._joiner.join(chunk)
                    if ' "%s"' %name in combined_line or '|%s"' %name in combined_line\
                     or ' "%s.' %name in combined_line or '|%s.' %name in combined_line:
                        result[cmd].append(chunk)

        return result

    def replaceReference(self, node, path):
        ''' Remap reference to new path
        
        Keyword Arguments:
            node -- name of the reference node (str)
            path -- new path (str)
        Return:
            list[str] -- list of data chunks of the replaced ref node
        '''
        result = []
        if not self.data or not self.data.get('file'):
            return result

        typ_dict = {'.abc': 'Alembic', '.ma': 'mayaAscii', '.mb': 'mayaBinary'}
        for i, chunk in enumerate(self.data['file']):
            # namespace = ''
            refNode = ''
            # for line in chunk:
            combined_line = ''.join(chunk)
            combined_line = combined_line.replace('\n', '')
            combined_line = combined_line.replace('\t', '')
            if ' -r ' in combined_line or ' -rdi ' in combined_line:
                refNode = flag_string_value(line=combined_line, flag='-rfn')

            if refNode == node:
                last_line = chunk[-1]
                splits = last_line.split()
                old_path = splits[-1].replace(';', '')
                old_path = old_path.replace('\n', '')
                old_path = old_path.replace('"', '')
                chunk[-1] = last_line.replace(old_path, path)

                # set file type
                op, op_ext = os.path.splitext(old_path)
                np, np_ext = os.path.splitext(path)
                curr_typ = flag_string_value(line=combined_line, flag='-typ')
                if curr_typ != typ_dict[np_ext]:
                    split_line = self._joiner.join(chunk)
                    split_line = split_line.replace(' "%s"' %curr_typ, ' "%s"' %typ_dict[np_ext])
                    chunk = split_line.split(self._joiner)

                self.data['file'][i] = chunk
                result.append(chunk)

        return result

    def editRefNamespace(self, node, new_namespace):
        ''' Edit namespace for a reference node
        
        Keyword Arguments:
            node -- name of the reference node (str)
            new_namespace -- new namespace (str)
        Return:
            list[str] -- list of data chunks of the replaced ref node
        '''
        result = []
        if not self.data or not self.data.get('file') or not self.data.get('createNode'):
            return result

        typ_dict = {'.abc': 'Alembic', '.ma': 'mayaAscii', '.mb': 'mayaBinary'}
        repalced_refs = {}
        for i, chunk in enumerate(self.data['file']):
            # namespace = ''
            refNode = ''
            # for line in chunk:
            combined_line = ''.join(chunk)
            combined_line = combined_line.replace('\n', '')
            combined_line = combined_line.replace('\t', '')
            if ' -r ' in combined_line or ' -rdi ' in combined_line:
                # namespace = flag_string_value(line=line, flag='-ns')
                refNode = flag_string_value(line=combined_line, flag='-rfn')

            if refNode == node:
                curr_ns = flag_string_value(line=combined_line, flag='-ns')
                split_line = self._joiner.join(chunk)
                split_line = split_line.replace(' "%s"' %curr_ns, ' "%s"' %new_namespace)
                chunk = split_line.split(self._joiner)

                self.data['file'][i] = chunk
                result.append(chunk)
                repalced_refs[refNode] = curr_ns

        for i, chunk in enumerate(self.data['createNode']):
            objName = ''
            combined_line = ''.join(chunk)
            combined_line = combined_line.replace('\n', '')
            combined_line = combined_line.replace('\t', '')
            if ' -n ' in combined_line:
                objName = flag_string_value(line=combined_line, flag='-n')

            if objName in repalced_refs:
                split_line = self._joiner.join(chunk)
                split_line = split_line.replace('%s:' %repalced_refs[objName], '%s:' %new_namespace)
                chunk = split_line.split(self._joiner)

                self.data['createNode'][i] = chunk
                result.append(chunk)

        return result

    @invalidate_cache
    def removeNaN(self):
        ''' Remove chunk of data with NaN (not a number) values
        
        Return:
            list[str] -- chunks of data that has NaN in it
        '''
        if not self.data.get('createNode'):
            return

        new_data = collections.OrderedDict()
        infected = []
        names_to_removes = []

        for cmd, chunks in self.data.iteritems():
            clean_chunks = []
            if cmd == 'createNode':
                for chunk in chunks:
                    combined_line = self._joiner.join(chunk)
                    if ' -nan(ind) ' in combined_line or ' nan ' in combined_line:
                        infected.append(chunk)
                        node_name = flag_string_value(line=combined_line, flag='-n')
                        if node_name:
                            names_to_removes.append(node_name)
                    else:
                        clean_chunks.append(chunk)
            else:
                for chunk in chunks:
                    combined_line = self._joiner.join(chunk)
                    for name in names_to_removes:
                        if ' "%s"' %name in combined_line or '|%s"' %name in combined_line\
                         or ' "%s.' %name in combined_line or '|%s.' %name in combined_line:
                            infected.append(chunk)
                            break
                    else:
                        clean_chunks.append(chunk)

            if clean_chunks:
                new_data[cmd] = clean_chunks

        self.data = new_data
        return infected

def eval_data_type(value, attr_type=None):
    ''' Convert Maya data types to Python types '''
    if attr_type in ('string', 'stringArray'):
        return value

    # try simple numeric type
    try: 
        value = literal_eval(value)
        if attr_type in ('short2', 'long2', 'short3', 'long3'):
            value = int(value)
        elif attr_type in ('float2', 'float3', 'double2', 'double3', 'matrix'):
            value = float(value)
        return value
    except ValueError:
        pass

    # try bool type
    if value in ('yes', 'no'):
        try:
            value = True if 'yes' else False
            return value
        except RuntimeError:
            pass

    # no type found just return the input
    return value

def flag_string_value(line, flag):
    ''' Get value for a flag within a line '''
    found = re.search('(%s) ("\S*")' %flag, line)
    result = ''
    if found:
        nameStr = found.group(2)
        result = nameStr[1:-1]
    return result

''' EXAMPLE:
from rf_utils import maya_ascii

path = ''  # << input path
output_path = ''  # << output save path
search = '' # << must be a regular expression
types = [] # << file types string

maya_scene = maya_ascii.MayaAscii(path)
maya_scene.read()
maya_scene.delete_node(search=search, types=types) 
maya_scene.write(output_path)

'''

path = "C:/Users/USER/Desktop/kubon_house_v002.ma"
maya_scene = MayaAscii(path)
maya_scene.read()

# get frame range
# maya_scene.frame_range()
# maya_scene.frame_range()  # the second call took less time

# list an object
obj = 'facet_F2_08'
st = time.time()
maya_scene.ls(search=obj, types=tuple())  # slow
print(time.time() - st)

st = time.time()
maya_scene.ls(search=obj, types=tuple())  # fast (cached!)
print(time.time() - st)

# now delete it
st = time.time()
maya_scene.delete_node(search=obj, types=tuple())  # delete node also use ls(), call is faster
print(time.time() - st)

