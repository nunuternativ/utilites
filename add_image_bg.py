import os
import sys
sys.path.append('{}/core'.format(os.environ['RFSCRIPT']))

import shutil
import tempfile
import subprocess

import rf_config as config
FFMPEG_PATH = config.Software.ffmpeg

si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
def main(images, color='0x808080'):
    print '===== Images to process ====='
    num_img = len(images)
    for i, image in enumerate(images):
        print 'Processing image...(%s/%s)' %(i+1, num_img)
        print '\t{}'.format(image)
        dirName = os.path.dirname(image)
        baseName = os.path.basename(image)
        name, ext = os.path.splitext(image)

        tfh, tfp = tempfile.mkstemp(suffix=ext)
        os.close(tfh)

        cmd = '"%s" -i "%s" -filter_complex "[0]split=2[bg][fg];[bg]drawbox=c=%s:replace=1:t=fill[bg];[bg][fg]overlay=format=auto" -c:a copy -y "%s"' %(FFMPEG_PATH, image, color, tfp)
        # print cmd
        # conversion = subprocess.Popen(cmd)
        # conversion.wait()
        ps = subprocess.Popen(cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                startupinfo=si)
        output = ps.communicate()[0]
        # ps.wait()
        shutil.copyfile(tfp, image)
        os.remove(tfp)
        # print '\n'

if __name__ == '__main__':
    images = sys.argv[1:]
    main(images)