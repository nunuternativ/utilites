import sys
import os
import re
import glob

file_path = sys.argv[1]

def rename_udim_textures(file_path):
    if not os.path.isfile(file_path) or not os.path.exists(file_path):
        return

    baseName = os.path.basename(file_path)
    fileName, ext = os.path.splitext(baseName)
    dirName = os.path.dirname(file_path)

    uv_search = re.search('u[0-9]*_v[0-9]*.%s' %ext[1:], baseName)
    digit_search = re.search('[0-9][0-9][0-9][0-9].%s' %ext[1:], baseName)
    result = {}
    files = []
    if uv_search:
        found = uv_search.group() # U1_V1.jpg
        texName = baseName.split(found)[0]
        glob_text = '%s/%su*_v*%s' %(dirName, texName, ext)
        files = glob.glob(glob_text)
        if files:
            for f in files:
                fn = os.path.basename(f)
                uv_search = re.search('u[0-9]*_v[0-9]*.%s' %ext[1:], fn)
                if uv_search:
                    search = uv_search.group()
                    uvStr = search.split('.')[0]
                    u = int(uvStr.split('u')[1].split('_v')[0]) - 1
                    v = int(uvStr.split('_v')[1]) - 1
                    digit = 1000+(u+1)+(v*10)
                    result[f] = (uvStr, str(digit))

    elif digit_search:
        found = digit_search.group()  # 1001.jpg
        texName = baseName.split(found)[0]
        glob_text = '%s/%s*%s' %(dirName, texName, ext)
        files = glob.glob(glob_text)
        if files:
            for f in files:
                fn = os.path.basename(f)
                digit_search = re.search('[0-9][0-9][0-9][0-9].%s' %ext[1:], fn)
                if digit_search:
                    search = digit_search.group()
                    digit = int(search.split('.')[0])
                    v = ((digit - 1001)/10)
                    u = digit-1001-(v*10)
                    u += 1
                    v += 1
                    uvStr = 'u%s_v%s' %(u, v)
                    result[f] = (str(digit), uvStr)

    if result:
        for path, sr in result.iteritems():
            dirName = os.path.dirname(path)
            baseName = os.path.basename(path)
            newName = baseName.replace(sr[0], sr[1])
            newPath = '%s/%s' %(dirName, newName)
            print newPath
            os.rename(path, newPath)


rename_udim_textures(file_path)