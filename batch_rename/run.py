import sys
import os
import re

from main import *

def ask_user_input_str(question, input_type, limit=None, check_func=None):
    response = None
    while type(response) != input_type or response > limit:
        response = raw_input(question)
        if str(response) == '':
            print('Invalid input!')
            continue
        if check_func and check_func(response):
            break
        print type(response)
    return response

def ask_user_input(question, input_type):
    response = None
    while type(response) != input_type:
        try:
            response = input(question)
        except NameError:
            print('Please input {}'.format(input_type))
            continue
    return response

def check_hash(input_pattern):
    m = re.findall('(\*+)', input_pattern)
    if len(m) > 1:
        print('Invalid pattern: Only 1 group of * is allowed!')
        return False
    return True

def main(inputs): 
    print('\n===== Batch Renamer =====')
    images = []
    
    if len(inputs)==1 and os.path.isdir(inputs[0]):
        print('Input folder: {}'.format(inputs[0]))
        images = ['{}/{}'.format(inputs[0], p) for p in os.listdir(inputs[0])]
        print('Images:\n{}'.format('\n'.join(images)))
    else:
        print('Inputs:\n{}'.format('\n'.join(inputs)))
        images = inputs
    print('Found {} file(s). Please input renaming pattern (* = digit).'.format(len(images)))

    # sort input images by name
    images = sorted(images)
    
    # name pattern
    name_pattern = ask_user_input_str(question='\n- Name pattern: ', input_type=str, check_func=check_hash)

    # start num
    start_num = ask_user_input(question='\n- Starting number: ', input_type=int)

    try:
        status = rename(input_paths=images, pattern=name_pattern, start_num=start_num)
        print('Finished.')
    except Exception as e:
        print(e)

if __name__ == '__main__':
    images = sys.argv[1:]
    if images:
        main(inputs=[i.replace('\\', '/') for i in images])
