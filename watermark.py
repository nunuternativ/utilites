import os
import tempfile
import shutil
import time

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)

from rf_utils.pipeline import convert_lib
# reload(convert_lib)
from rf_utils.context import context_info
# from rf_utils import file_utils
import rf_config as config

def add_watermark_to_media(entity, input_path, key='default', opacity=0.12):
    SUPPORTED_EXT = ('.mov', '.mp4', '.jpg', '.png', '.tif', '.tiff')
    input_fn, input_ext = os.path.splitext(input_path)
    if input_ext.lower() not in SUPPORTED_EXT:
        logger.error('Unsupported media format: %s' %input_ext)
        return input_path, False

    watermark_path = entity.projectInfo.render.watermark(key=key)
    if not os.path.exists(watermark_path):
        logger.error('Cannot find watermark path: %s' %watermark_path)
        return input_path, False

    # create temp mov
    # make temp dir
    tmp_dir = tempfile.mkdtemp().replace('\\', '/')
    out_fh, out_temp = tempfile.mkstemp(suffix=input_ext, dir=tmp_dir)
    os.close(out_fh)
    temp_path = '{}/{}'.format(tmp_dir, os.path.basename(input_path))
    os.rename(out_temp, temp_path)
    logger.debug('Temp media created: {temp_path}'.format(temp_path=temp_path))
    
    # add watermark using ffmpeg
    convert_output = convert_lib.overlay_image(input_path=input_path, 
                overlay_image=watermark_path, 
                output_path=temp_path, 
                opacity=opacity, 
                blendmode='normal',
                video_quality=20, 
                video_preset='veryfast')
    

    logger.info('Watermark media path: %s' %(temp_path))
    return temp_path, True

def add_border_hud_to_mov(input_path, output_path='', frame_ext='png', frameHud=None, **kwargs):
    import cv2
    basename = os.path.basename(input_path)
    vid_name, ext = os.path.splitext(basename)
    ext = ext.lower()
    SUPPORTED_EXT = ('.mov', '.mp4', '.mpg')
    if ext not in SUPPORTED_EXT:
        logger.error('Unsupported video format: %s' %ext)
        return

    if not output_path:
        output_path = '{}\\{}'.format(os.environ['TEMP'], basename)
        logger.debug('Temp image location: {out_temp}'.format(out_temp=output_path))

    # make temp dir
    tmp_dir1 = tempfile.mkdtemp().replace('\\', '/')

    # read video frames
    capture = cv2.VideoCapture(input_path)
    read_flag, frame = capture.read()
    vid_frames = []
    i = 1
    while (read_flag):
        frame_path = "{}/{}.{:0>4d}.{}".format(tmp_dir1, vid_name, i, frame_ext)
        cv2.imwrite(frame_path, frame)
        vid_frames.append(frame_path)
        read_flag, frame = capture.read()
        i += 1
    capture.release()

    num_frames = len(vid_frames)
    # add HUD to each image
    for i, frame in enumerate(vid_frames):
        frame_arg = dict(**kwargs)
        if frameHud:
            curr_hud = []
            if frameHud in frame_arg:
                curr_hud = frame_arg[frameHud]
            frame_arg[frameHud] = curr_hud + ['Frame: {}/{}'.format(i+1, num_frames)]
        add_border_hud_to_image(input_path=frame, output_path=frame, **frame_arg)

    # convert back to mov
    convert_output = convert_lib.img_to_mov2(images=vid_frames, dst=output_path)

    # remove temp
    shutil.rmtree(tmp_dir1)

    return output_path

def add_border_hud_to_image(input_path,
                            output_path='',
                            topLeft=[], 
                            topMid=[], 
                            topRight=[], 
                            bottomLeft=[], 
                            bottomMid=[], 
                            bottomRight=[], 
                            canvas=[],
                            border_size = 15, 
                            fontScale = None, 
                            fontScaleMultiplier = {}, 
                            fontColor = (255, 255, 255), 
                            thickness = 1,
                            lineType = 16):
    import cv2
    import numpy as np

    if not os.path.exists(input_path):
        logger.error('Invalid path: {}'.format(input_path))

    SUPPORTED_EXT = ('.jpg', '.png', '.tif', '.exr')
    font = cv2.FONT_HERSHEY_DUPLEX
    fn, ext = os.path.splitext(input_path)
    ext = ext.lower()
    if ext not in SUPPORTED_EXT:
        logger.error('Unsupported image format: %s' %ext)
        return False

    if not output_path:
        baseName = os.path.basename(input_path)
        output_path = '{}\\{}'.format(os.environ['TEMP'], baseName)
        logger.debug('Temp image location: {out_temp}'.format(out_temp=output_path))

    # ----- create basic watermark image
    # determine bit depth to use
    readflag = cv2.IMREAD_COLOR
    bitdepth = np.uint8
    if ext == '.exr':
        readflag = cv2.IMREAD_UNCHANGED
        bitdepth = np.float32
    # open image
    try:
        cvImg = cv2.imread(input_path, readflag)
        imgHeight, imgWidth, imgChannels = cvImg.shape
    except Exception, e:
        print e
        logger.error('Error reading: %s' %input_path)
        return False

    if imgWidth < 300:
        logger.error('Image is too small: %s' %input_path)
        return False

    if not fontScale:
        if imgWidth <= 800:
            fontScale = 0.4
        elif imgWidth in range(801, 2049):
            fontScale = 0.8
        elif imgWidth in range(2049, 4097):
            fontScale = 1.2
        elif imgWidth in range(4097, 8192):
            fontScale = 1.6
        else:
            fontScale = 2

    line_height = cv2.getTextSize('TEXT', font, fontScale, lineType)[0][1]

    top_max_hud_lines = max([len(h) for h in (topLeft, topMid, topRight)])
    bottom_max_hud_lines = max([len(h) for h in (bottomLeft, bottomMid, bottomRight)])
    text_height_top = (line_height * top_max_hud_lines)
    top_borders = (border_size * (top_max_hud_lines+1))
    text_height_bottom = (line_height * bottom_max_hud_lines)
    bottom_borders = (border_size * (bottom_max_hud_lines+1))
    line_height_border = line_height + border_size

    # calculate background image size
    if not canvas:  # automatically create black envelope
        widthOffset = 0
        top_bar = text_height_top + top_borders + border_size if top_max_hud_lines > 0 else 0
        bottom_bar = text_height_bottom + bottom_borders + border_size if bottom_max_hud_lines > 0 else 0
        canvasHeight = imgHeight + top_bar + bottom_bar
    else:
        if canvas == 'original':
            canvasWidth, canvasHeight = imgWidth, imgHeight
        else:  # canvas is specified
            canvasWidth, canvasHeight = canvas
        widthOffset = (canvasWidth - imgWidth) / 2
        top_bar = (canvasHeight - imgHeight) / 2
        bottom_bar = top_bar

    # create black image
    canvas_im = np.zeros((canvasHeight, imgWidth, 3), bitdepth)

    # paste the old image onto new image
    canvas_im[top_bar: top_bar + imgHeight, widthOffset: widthOffset + imgWidth] = cvImg

    # bottom text should starts at this pixel so all texts are covered inside frame
    bottom_start = canvasHeight - (text_height_bottom + bottom_borders)

    # font scale multiplier
    for pos in ('topLeft', 'topMid', 'topRight', 'bottomLeft', 'bottomMid', 'bottomRight'):
        if pos not in fontScaleMultiplier:
            fontScaleMultiplier[pos] = 1.0

    if topLeft:
        for i, text in enumerate(topLeft):
            textsize = cv2.getTextSize(text, font, fontScale*fontScaleMultiplier['topLeft'], lineType)[0]
            posX = border_size
            posY = border_size + (i*line_height_border) + textsize[1]
            cv2.putText(canvas_im, text, (posX, posY), font, fontScale*fontScaleMultiplier['topLeft'], fontColor, thickness, lineType)
    if topMid:
        for i, text in enumerate(topMid):
            textsize = cv2.getTextSize(text, font, fontScale*fontScaleMultiplier['topMid'], lineType)[0]
            posX = (imgWidth - textsize[0])/2
            posY = border_size + (i*line_height_border) + textsize[1]
            cv2.putText(canvas_im, text, (posX, posY), font, fontScale*fontScaleMultiplier['topMid'], fontColor, thickness, lineType)
    if topRight:
        for i, text in enumerate(topRight):
            textsize = cv2.getTextSize(text, font, fontScale*fontScaleMultiplier['topRight'], lineType)[0]
            posX = imgWidth - (textsize[0] + border_size)
            posY = border_size + (i*line_height_border) + textsize[1]
            cv2.putText(canvas_im, text, (posX, posY), font, fontScale*fontScaleMultiplier['topRight'], fontColor, thickness, lineType)
    if bottomLeft:
        for i, text in enumerate(bottomLeft):
            textsize = cv2.getTextSize(text, font, fontScale*fontScaleMultiplier['bottomLeft'], lineType)[0]
            posX = border_size
            posY = bottom_start + (line_height_border * i) + textsize[1]
            cv2.putText(canvas_im, text, (posX, posY), font, fontScale*fontScaleMultiplier['bottomLeft'], fontColor, thickness, lineType)
    if bottomMid:
        for i, text in enumerate(bottomMid):
            textsize = cv2.getTextSize(text, font, fontScale*fontScaleMultiplier['bottomMid'], lineType)[0]
            posX = (imgWidth - textsize[0])/2
            posY = bottom_start + (line_height_border * i) + textsize[1]
            cv2.putText(canvas_im, text, (posX, posY), font, fontScale*fontScaleMultiplier['bottomMid'], fontColor, thickness, lineType)
    if bottomRight:
        for i, text in enumerate(bottomRight):
            textsize = cv2.getTextSize(text, font, fontScale*fontScaleMultiplier['bottomRight'], lineType)[0]
            posX = imgWidth - (textsize[0] + border_size)
            posY = bottom_start + (line_height_border * i) + textsize[1]
            cv2.putText(canvas_im, text, (posX, posY), font, fontScale*fontScaleMultiplier['bottomRight'], fontColor, thickness, lineType)

    cv2.imwrite(output_path, canvas_im)
    logger.debug('Result path: %s' %(output_path))

    return output_path

def add_watermark_with_text(input_path, 
                        overlay_path, 
                        text, 
                        output_path='', 
                        opacity=0.12, 
                        callback_func=None):
    ''' add watermark with customizable text to image/video '''
    import cv2
    import numpy as np
    from rf_utils.pipeline import pdf_utils

    # if no output path, write to temp
    basename = os.path.basename(input_path)
    fn, ext = os.path.splitext(basename)
    if not output_path:
        out_fh, output_path = tempfile.mkstemp(suffix=ext)
        os.close(out_fh)

    # check if it's a pdf
    is_pdf = True if ext == '.pdf' else False

    # ----- prepare watermark overlay
    # temp file for text compositing
    overlay_fn, overlay_ext = os.path.splitext(overlay_path)
    wm_fh, wm_output_path = tempfile.mkstemp(prefix='{}_'.format(fn), suffix=overlay_ext)
    os.close(wm_fh)
    # composite new watermark with text
    watermark_bg = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)
    bgHeight, bgWidth, bgChannels = watermark_bg.shape
    # font settings
    font = cv2.FONT_HERSHEY_DUPLEX 
    fontColor = (255, 255, 255, 255)  # solid white color for text
    fontLineColor = (0, 0, 0, 255)  # solid black color for font line
    fontScale = 1.0
    thickness = 2
    lineThickness = 8
    lineType = cv2.LINE_AA
    
    # try to find proper fontScale
    if text and text != '':
        while True:
            if fontScale < 0.1:
                break
            textsize = cv2.getTextSize(text, font, fontScale, lineType)[0]
            posX = (bgWidth - textsize[0])/2
            posY = (bgHeight/5) + textsize[1] + 20
            if posX < 0:  # decrese font scale if text starts less than 1/12 of image width
                fontScale -=0.1
            elif posX > (bgWidth/12):  # increse font scale if text starts greather than 1/8 of image width
                fontScale +=0.1
            else:
                break

        # put in the text line and then text
        cv2.putText(watermark_bg, text, (posX, posY), font, fontScale, fontLineColor, lineThickness, lineType)
        cv2.putText(watermark_bg, text, (posX, posY), font, fontScale, fontColor, thickness, lineType)
    # write composited watermark to temp
    cv2.imwrite(wm_output_path, watermark_bg)

    
    # PDF file need image to be transparent before overlaying
    if is_pdf:
        twm_fh, twm_output_path = tempfile.mkstemp(prefix='{}_'.format(fn), suffix=overlay_ext)
        os.close(twm_fh)

        if isinstance(opacity, (list, tuple)):
            opacity = max(opacity)

        # apply opacity to watermark with Numpy indexing, B=0, G=1, R=2, A=3
        watermark_opaque_img = cv2.imread(wm_output_path, cv2.IMREAD_UNCHANGED)
        watermark_opaque_img = cv2.cvtColor(watermark_opaque_img, cv2.COLOR_BGR2BGRA) 
        watermark_opaque_img = np.array(watermark_opaque_img, dtype=np.float)
        watermark_opaque_img[..., 3] *= opacity

        cv2.imwrite(twm_output_path, watermark_opaque_img)

        # overlay to pdf
        convert_output = pdf_utils.overlay_all_pages(input_path=input_path, 
                                    overlay_path=twm_output_path, 
                                    output_path=output_path,
                                    callback_func=callback_func)

        # remove temp
        os.remove(twm_output_path)
    else: 
        # opacity calculation
        if isinstance(opacity, (list, tuple)):
            avg_grey_value = convert_lib.get_average_image_value(input_path)
            opacity = opacity[0] + ((opacity[1] - opacity[0])*avg_grey_value)

        print('Using opacity: {}'.format(opacity))

        # ----- add watermark using ffmpeg
        convert_output = convert_lib.overlay_image(input_path=input_path, 
                                                overlay_image=wm_output_path, 
                                                output_path=output_path, 
                                                opacity=opacity,
                                                blendmode='normal', 
                                                video_quality=20, 
                                                video_preset='veryfast',
                                                callback_func=callback_func)
    # remove temp file
    os.remove(wm_output_path)

    return convert_output

