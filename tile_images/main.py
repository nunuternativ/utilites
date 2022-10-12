#Import python modules
import sys
import os
import cv2
from datetime import datetime
import numpy as np


def resize_keep_aspect_ratio(img, max_size):
    height, width, channels = img.shape
    if width >= height:
        scale_ratio = float(max_size)/width
    else:
        scale_ratio = float(max_size)/height
    dim = (int(width*scale_ratio), int(height*scale_ratio))
    final_img = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
    print 'Resized to: {}'.format(dim)
    return final_img

def tile_images(images, output_dir=None, image_per_row=4, max_size=8192, gap=20, grid_mode=False, grid_size=1024):
    num_images = len(images)
    cvImages = []
    for path in images:
        # open image
        cvImg = None
        try:
            cvImg = cv2.imread(path, cv2.IMREAD_COLOR)
        except Exception, e:
            print e
            print 'Error reading: {}'.format(path)
            continue
        
        if grid_mode and grid_size > 0:
            resizedImg = resize_keep_aspect_ratio(cvImg, grid_size)
            reized_height, resized_width, resized_channels = resizedImg.shape

            cvImg = np.zeros((grid_size, grid_size, 3), np.uint8)
            grid_height, grid_width, grid_channels = cvImg.shape
            x = abs(grid_width - resized_width)/2
            y = abs(grid_height - reized_height)/2
            cvImg[y: y+reized_height, x: x+resized_width] = resizedImg
        
        imgHeight, imgWidth, imgChannels = cvImg.shape
        cvImages.append([cvImg, imgWidth, imgHeight, imgChannels])

    # group image into rows
    rowImages = [cvImages[i:i+image_per_row] for i in range(0, len(cvImages), image_per_row)] 

    # calculate width, height
    canvas_width, canvas_height = 0, 0
    row_heights = []
    for row in rowImages:
        row_width = 0
        row_height = 0
        for img in row:
            row_width += img[1]
            if img[2] > row_height:
                row_height = img[2]

        if row_width > canvas_width:
            canvas_width = row_width
        canvas_height += row_height
        row_heights.append(row_height)
    canvas_width += gap + (image_per_row * gap)
    canvas_height += gap + (len(rowImages) * gap)
            
    # create black image
    canvas_im = np.zeros((canvas_height, canvas_width, 3), np.uint8)

    # paste the old image onto new image
    x = gap
    y = gap
    for i, row_imgs in enumerate(rowImages):
        for img_data in row_imgs:
            cvImg, imgWidth, imgHeight, imgChannels = img_data
            canvas_im[y: y+imgHeight, x: x+imgWidth] = cvImg
            x += imgWidth+gap
        y += row_heights[i] + gap
        x = gap

    # resize
    if max_size != None:
        final_img = resize_keep_aspect_ratio(canvas_im, max_size)
    else:
        final_img = canvas_im

    # write to file
    if not output_dir:
        output_dir = '{}/Desktop'.format(os.path.expanduser('~').replace('\\', '/'))
    output_path = '{}/tileimages_{}.png'.format(output_dir, datetime.strftime(datetime.now(), '%y%m%d%H%M%S'))
    cv2.imwrite(output_path, final_img)
    return output_path
    
