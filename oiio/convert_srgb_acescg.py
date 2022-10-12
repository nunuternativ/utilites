import sys
import os 

root = '{}/core'.format(os.environ['RFSCRIPT'])
if not root in sys.path:
    sys.path.append(root)

import rf_config as config
from rf_utils.oiio import run_oiio

def main(input_paths):
    output_paths = []
    for path in input_paths:
        fn, ext = os.path.splitext(path)
        output_path = '{}.exr'.format(fn)
        output_paths.append(output_path)
    output_paths = run_oiio.convert_colorspace(input_paths, output_paths, 'Utility - sRGB - Texture', 'ACES - ACEScg')
    return output_paths


if __name__ == '__main__':
    images = sys.argv[1:]
    main(images)