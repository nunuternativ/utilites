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

    parser.add_argument('-s', dest='srcs', nargs='+', help='The path to the input image', required=True)
    parser.add_argument('-d', dest='dsts', nargs='+', help='The path for the output image', required=True)

    parser.add_argument('-fc', dest='fromColorspace', type=str, help='The original colorspace', required=True)
    parser.add_argument('-tc', dest='toColorspace', type=str, help='The expected colorspace', required=True)
    parser.add_argument('-cc', dest='colorConfig', type=str, help='The path to ocio config file', required=True)

    return parser

def main(srcs, dsts, fromColorspace, toColorspace, colorConfig):
    for src, dst in zip(srcs, dsts):
        src_img = oiio.ImageBuf(src)
        dst_img = oiio.ImageBufAlgo.colorconvert(src_img, 
                                            fromColorspace, 
                                            toColorspace, 
                                            unpremult=True, 
                                            colorconfig=colorConfig)
        dst_img.write(dst)
    return dsts

if __name__ == "__main__":
    parser = setup_parser('Convert Image Colorspace')
    params = parser.parse_args()
    main(srcs=params.srcs, 
        dsts=params.dsts, 
        fromColorspace=params.fromColorspace,
        toColorspace=params.toColorspace,
        colorConfig=params.colorConfig)

'''
"D:/dev/core/rf_lib/OpenImageIO-1.5.0-OCIO/bin/oiiotool.exe" "D:/__playground/test_colorspace_aces/textures/Ayumi_Diffuse_All_1001.png" --colorconvert "Utility - sRGB - Texture" "ACES - ACEScg" -o "D:/__playground/test_colorspace_aces/textures/Ayumi_Diffuse_All_1001_test.exr"

'''



