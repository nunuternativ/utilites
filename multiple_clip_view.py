import sys
import os

root = '{}/core'.format(os.environ['RFSCRIPT'])
if root not in sys.path:
    sys.path.append(root)

import shutil
import tempfile
import cv2
import numpy as np
import subprocess
import argparse

import rf_config as config
from rf_utils.pipeline import convert_lib
# reload(convert_lib)
from rf_utils import audio_utils

VID_EXT = ('.mov', '.mp4', '.mpeg')

si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

def setup_parser(title):
    # create the parser
    parser = argparse.ArgumentParser(description=title, formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-i', dest='input_path', nargs='+', help='The input paths, the first one is the main clip', required=True)
    parser.add_argument('-o', dest='output_path', type=str, help='The output path', required=True)
    parser.add_argument('-f', dest='fps', help='Framerate per second', default=24)
    parser.add_argument('-r', dest='main_clip_ratio', type=float, help='The scale ratio for main clip', default=0.75)
    parser.add_argument('-t', dest='texts', nargs='+', help='The texts to display under subclips', default=[])
    parser.add_argument('-bc', dest='background_color', nargs='+', type=int, help='The color of background', default=(0, 0, 0))
    parser.add_argument('-ss', dest='sub_clip_spacing', type=str, help='The spacing of sub clips', default='top')
    return parser

def make_video(image_path, wav_path, output_path, fps):
    argList = [config.Software.ffmpeg,
            '-y', '-r',
            '{framerate}'.format(framerate=fps),
            '-start_number', '0001',
            '-i', image_path]
    if wav_path:
        argList += ['-ss', '00:00:00.00',
            '-i', '{wav_path}'.format(wav_path=wav_path)]
    argList += ['-vcodec',
            'libx264',
            '-vprofile',
            'baseline',
            '-crf',
            '10',
            '-bf',
            '0',
            '-pix_fmt',
            'yuv420p',
            '-f',
            'mov',
            output_path]
    ps = subprocess.Popen(argList, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=si)
    output = ps.communicate()[0]
    if ps.returncode == 0 and os.path.exists(output_path):
        return output_path

def resize_keep_aspect_ratio(img, frame_w, frame_h):
    height, width, channels = img.shape
    ratio = min(frame_w/float(width), frame_h/float(height))

    dim = (int(width*ratio), int(height*ratio))
    final_img = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
    return final_img

def main(input_paths, output_path, fps=24, main_clip_ratio=0.75, texts=[], background_color=(0.0, 0.0, 0.0), sub_clip_spacing='top'):
    if len(input_paths) < 2 or os.path.splitext(input_paths[0])[1].lower() not in VID_EXT or main_clip_ratio >= 1.0:
        print 'Error: Invalid inputs'
        return input_paths[0]

    main_clip = input_paths[0]
    sub_clips = input_paths[1:]
    num_subclips = len(sub_clips)

    # take audio from the main clip
    wav_path = audio_utils.extract_wav_from_video(input_path=main_clip)

    # convert main clip to img
    main_img_frames = convert_lib.read_media_frames(main_clip)

    # convert all subclips to image sequence
    sub_images = []
    for sc in sub_clips:
        sub_img_frames = convert_lib.read_media_frames(sc)
        if sub_img_frames:
            sub_images.append(sub_img_frames)
    if not sub_images:
        print 'Error: Cannot encode any subclips'
        return input_paths[0]

    # the final size is equal to the size of the main clip
    canvas_h, canvas_w, canvas_ch = main_img_frames[0].shape
    gap = 24

    # calculate the scale of main clip according to the main_clip_ratio
    main_w, main_h = (int(canvas_w * main_clip_ratio), int(canvas_h * main_clip_ratio)) 

    # calculate coordinates of the main clip
    main_x, main_y = ((canvas_w - main_w + gap), (canvas_h - main_h)/2)

    # place each image onto the frame
    final_tmp_dir = tempfile.mkdtemp().replace('\\', '/')

    # calculate subclip frame sizes
    sub_frame_w = canvas_w - main_w
    average_h = canvas_h / num_subclips
    # sub_frame_h = canvas_h

    final_output_name = os.path.splitext(os.path.basename(output_path))[0]
    final_imgs = []
    # font settings
    font = cv2.FONT_HERSHEY_DUPLEX
    fontColor = (255, 255, 255)
    fontSize = 0.7
    thickness = 1
    lineType = 16
    for i, frame in enumerate(main_img_frames):
        # create black frame
        canvas_im = np.zeros((canvas_h, canvas_w, 3), np.uint8)
        canvas_im[:] = background_color
        # place main clip
        scaled_main_img = cv2.resize(frame, (main_w-(gap), main_h), interpolation=cv2.INTER_AREA)
        scaled_main_h, scaled_main_w, scaled_main_ch = scaled_main_img.shape
        canvas_im[main_y: main_y+scaled_main_h, main_x: main_x+scaled_main_w] = scaled_main_img

        # scale sub clip
        scaled_sub_imgs = []  # 
        sub_img_total_height = 0
        for s in range(num_subclips):
            try:
                sub_img = sub_images[s][i]
            except IndexError:
                sub_img = sub_images[s][-1]  # use last frame in case subclip is shorter than main clip

            # scale sub image
            scaled_sub_img = resize_keep_aspect_ratio(sub_img, sub_frame_w-gap, ((canvas_h-(gap*2))/num_subclips) - gap)
            scale_sub_h, scale_sub_w, scale_sub_ch = scaled_sub_img.shape
            scaled_sub_imgs.append(scaled_sub_img)
            sub_img_total_height += scale_sub_h

        avg_gap = (canvas_h - sub_img_total_height) / (num_subclips+1)
        # place sub clips
        y = 0
        for si, ss in enumerate(scaled_sub_imgs):
            scale_sub_h, scale_sub_w, scale_sub_ch = ss.shape
            # space bottom area
            if sub_clip_spacing == 'top':
                canvas_im[y+gap: y+gap+scale_sub_h, gap: gap+scale_sub_w] = ss
                y += gap + scale_sub_h
            elif sub_clip_spacing == 'bottom':
                if si == 0:
                    y = canvas_h - (sub_img_total_height + (gap*num_subclips)+gap)
                canvas_im[y+gap: y+gap+scale_sub_h, gap: gap+scale_sub_w] = ss
                y += gap + scale_sub_h
            elif sub_clip_spacing == 'center':
                if si == 0:
                    y = (canvas_h - (sub_img_total_height + (gap*(num_subclips-1))))/2
                canvas_im[y: y+scale_sub_h, gap: gap+scale_sub_w] = ss
                y += gap + scale_sub_h
            else:  # spread image vertically
                if si == 0:
                    y = avg_gap
                canvas_im[y: y+scale_sub_h, gap: gap+scale_sub_w] = ss
                y += scale_sub_h + avg_gap

            if texts and len(texts)==num_subclips:
                text = texts[si]
                textsize = cv2.getTextSize(text, font, fontSize, lineType)[0]
                tposX = ((scale_sub_w - textsize[0])/2) + gap
                tposY = y
                cv2.putText(canvas_im, text, (tposX, tposY), font, fontSize, fontColor, thickness, lineType)
        # write images
        final_im_path = '{}/{}.{}.png'.format(final_tmp_dir, final_output_name, str(i+1).zfill(4))
        cv2.imwrite(final_im_path, canvas_im)
        final_imgs.append(final_im_path)

    # recompose audio
    image_path = '{directory}/{filename}.%04d.png'.format(directory=final_tmp_dir, filename=final_output_name),
    output_path = make_video(image_path, wav_path, output_path, fps)
    # delete temp files
    if wav_path:
        os.remove(wav_path)
    shutil.rmtree(final_tmp_dir)

    return output_path

def test():
    clips = ['D:/__playground/test_pnp/anim.mov', 
            'D:/__playground/test_pnp/still.jpg',
            'D:/__playground/test_pnp/animatic.mov',
            'D:/__playground/test_pnp/tech.mov',
            'D:/__playground/test_pnp/comp.mov'
            ]
    res = main(input_paths=clips, 
            output_path='{}/output.mov'.format(os.path.expanduser('~').replace('\\', '/')),
            texts=['test1', 'test2', 'test3', 'test4'])
    return res

if __name__ == "__main__" :
    parser = setup_parser('Make multiple video view')
    params = parser.parse_args()
    
    main(input_paths=params.input_path, 
        output_path=params.output_path, 
        fps=params.fps,
        main_clip_ratio=params.main_clip_ratio,
        texts=params.texts,
        background_color=params.background_color, 
        sub_clip_spacing=params.sub_clip_spacing)

'''
python D:\dev\core\rf_utils\pipeline\multiple_clip_view.py -i D:/__playground/test_pnp/anim.mov D:/__playground/test_pnp/tech.mov D:/__playground/test_pnp/still.jpg D:/__playground/test_pnp/animatic.mov  D:/__playground/test_pnp/comp.mov -o D:/__playground/test_pnp/output.mov -r 0.75 -ss top
'''