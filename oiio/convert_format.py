import sys
import os 
import argparse

root = '{}/core'.format(os.environ['RFSCRIPT'])
if not root in sys.path:
    sys.path.append(root)

import rf_config as config
import OpenImageIO as oiio

def setup_parser(title):
    # create the parser
    parser = argparse.ArgumentParser(description=title, formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-s', dest='src', type=str, help='The path to the input image', required=True)
    parser.add_argument('-d', dest='dst', type=str, help='The path for the output image', required=True)

    return parser

def main(src, dst):
    src_img = oiio.ImageBuf(src)
    src_img.write(dst)
    return dst


if __name__ == "__main__":
    parser = setup_parser('Convert Image Format')
    params = parser.parse_args()
    
    main(src=params.src, 
        dst=params.dst)







