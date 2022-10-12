import sys
import sys
from main import *

def ask_user_choices(question, choices):
    response = ''
    question_str = question + '\n  '
    question_str += '\n  '.join(['{}.{}'.format((i+1), choices[i]) for i in range(len(choices))])
    while True:
        print(question_str)
        response = input('Your answer: ')
        if isinstance(response, int) and response >= 0 and response <= len(choices):
            return choices[response-1]

def ask_user_input(question, input_type, limit):
    response = None
    while type(response) != input_type or response > limit:
        response = input(question)
    return response

def main(images): 
    print('\n===== This will tile all input images into a single image =====')
    print('INSTRUCTION: Please input the number corresponding to your answer.')

    # image per row
    image_per_row = ask_user_input(question='\n- How many images per row? (MAX = {}): '.format(len(images)), input_type=int, limit=len(images))

    # use default?
    max_size = ask_user_choices(question='\n- Size?', choices=['2K', '4K', '8K', '12K', 'Full size'])
    size_dict = {'2K': 2048, 
                '4K': 4096,
                '8K': 8192,
                '12K': 12288,
                'Full size': None}
    output_path = tile_images(images, 
                output_dir=None, 
                image_per_row=image_per_row, 
                max_size=size_dict[max_size], 
                gap=0, 
                grid_mode=False)
    
    print('Output: {}'.format(output_path))
    print('Finished.')

if __name__ == '__main__':
    images = sys.argv[1:]
    if images:
        main(images=[i.replace('\\', '/') for i in images])
