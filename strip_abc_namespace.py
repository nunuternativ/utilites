import os
import sys
import shutil
import tempfile

import pymel.core as pm
from rf_utils import cask

def main(abc_paths):
    temp_dir = os.path.join(os.environ['HOME'], 'tmp_strip_abc_namespace')
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)
    for f in os.listdir(temp_dir):
        fp = os.path.join(temp_dir, f)
        if os.path.isfile(fp) and fp.endswith('.abc'):
            try:
                os.remove(fp)
            except:
                pass

    for path in abc_paths:
        arc = cask.Archive(path)
        exit = False
        objs = [arc.top]
        result = {}
        while not exit:
            next_objs = []
            for o in objs:
                children = o.children.values()
                for c in children:
                    old_name = c.name
                    c.name = old_name.split(':')[-1]
                    if c.type() == 'Xform':
                        next_objs.append(c)

            if next_objs:
                objs = next_objs
            else:
                exit = True

        fh, temp_path = tempfile.mkstemp(suffix='.abc', dir=temp_dir)
        arc.write_to_file(temp_path)
        shutil.copyfile(temp_path, path)

if __name__ == '__main__':
    abc_paths = sys.argv[1:]
    temp_paths = main(abc_paths=abc_paths)
    