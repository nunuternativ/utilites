import sys
import os
import re

def rename(input_paths, pattern, start_num=None):
    if not start_num:
        start_num = 1

    m = re.findall('(\*+)', pattern)
    if not m:
        pattern += '_*'
        m = ['*']
        padding = 1
    else:
        padding = len(m[0])
    hash_str = m[0]
    name_start, name_end = pattern.split(hash_str)
    print('hash = {}'.format(hash_str))
    print('padding = {}'.format(padding))

    n = start_num
    for path in input_paths:
        dir_name = os.path.dirname(path)
        base_name = os.path.basename(path)
        fn, ext = os.path.splitext(base_name)

        new_name = '{}{}{}{}'.format(name_start, str(n).zfill(padding), name_end, ext)
        new_fp = '{}/{}'.format(dir_name, new_name)
        os.rename(path, new_fp)
        print('{} --> {}'.format(path, new_fp))

        n += 1
    return True
        