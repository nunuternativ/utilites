import sys
import os 
import subprocess

root = '{}/core'.format(os.environ['RFSCRIPT'])
if not root in sys.path:
    sys.path.append(root)

modulePath = os.path.dirname(sys.modules[__name__].__file__).replace('//', '/')

import rf_config as config

si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

def convert_colorspace(srcs, dsts, src_colorspace, dst_colorspace):
    cmd = [config.Software.python3Path, 
            '{}/convert_colorspace.py'.format(modulePath),
            '-s {}'.format(' '.join([s.replace('\\', '/') for s in srcs])), 
            '-d {}'.format(' '.join([d.replace('\\', '/') for d in dsts])),
            '-fc', '"{}"'.format(src_colorspace),
            '-tc', '"{}"'.format(dst_colorspace),
            '-cc', config.Software.ocio]
    result = subprocess.call(' '.join(cmd), startupinfo=si)
    if result == 0:  # success
        return dsts
    else:
        return

def convert_colorspace_oiio(src, dst, src_colorspace, dst_colorspace):
    cmd = [config.Software.oiioTool, 
            '"{}"'.format(src.replace('\\', '/')),
            '--colorconvert "{}" "{}"'.format(src_colorspace, dst_colorspace),
            '-o', 
            '"{}"'.format(dst.replace('\\', '/'))]
    env = os.environ.copy()
    env['OCIO'] = config.Software.ocio
    result = subprocess.call(' '.join(cmd), startupinfo=si, env=env)
    if result == 0:  # success
        return dst
    else:
        return

def convert_format(src, dst):
    cmd = [config.Software.python3Path, 
            '{}/convert_format.py'.format(modulePath),
            '-s', src, 
            '-d', dst]
    result = subprocess.call(cmd, startupinfo=si)
    if result == 0:  # success
        return dst
    else:
        return


'''
from rf_utils.oiio import subprocess_call
# reload(subprocess_call)
subprocess_call.convert_sRGB_ACEScg("D:/__playground/test_aces/src1.png", 
                        "D:/__playground/test_aces/output3.exr")

 '''