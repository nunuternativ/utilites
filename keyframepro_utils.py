# built-in modules
import sys
import os
import StringIO
import subprocess
import argparse
import time
import shutil

# installed modules
import psutil
import configparser

# config
script_root = '{}/core'.format(os.environ['RFSCRIPT'])
if script_root not in sys.path:
    sys.path.append(script_root)
import rf_config as config
reload(config)

# keyframe Pro module
if config.Env.keyframePro not in sys.path:
    sys.path.append(config.Env.keyframePro) 
from keyframe_pro import keyframe_pro_client

KEYFRAMEPRO_PATH = config.Software.keyframePro
GLOBAL_DIR = '{global_drive}/Pipeline/softwares/Keyframe Pro'.format(global_drive=config.Env.pipelineGlobal)
GLOBAL_LICENSE_PATH = '{global_dir}/keyframepro_riff_studio.lic'.format(global_dir=GLOBAL_DIR)
LOCAL_CONFIG_DIR = '{userprofile}/Documents/keyframe_pro/config'.format(userprofile=os.environ['userprofile'].replace('\\', '/'))
LOCAL_CONFIG_PATH = '{config_dir}/keyframe_pro.ini'.format(config_dir=LOCAL_CONFIG_DIR)
PROCESS_NAME = "KeyframePro.exe"
DEFAULT_PORT = 18181

client = keyframe_pro_client.KeyframeProClient()

def setup_license():
    if not os.path.exists(LOCAL_CONFIG_PATH):
        default_config_dir = '{global_dir}/config'.format(global_dir=GLOBAL_DIR)
        default_config_path = '{}/keyframe_pro.ini'.format(default_config_dir)
        default_binding_path = '{}/keyframe_pro_bindings.ini'.format(default_config_dir)
        if not os.path.exists(LOCAL_CONFIG_DIR):
            os.makedirs(LOCAL_CONFIG_DIR)
        shutil.copyfile(default_config_path, LOCAL_CONFIG_PATH)
        shutil.copyfile(default_binding_path, '{}/keyframe_pro_bindings.ini'.format(LOCAL_CONFIG_DIR))

        print('New config copied from: {}'.format(default_config_dir))
    else:
        config = configparser.ConfigParser()
        config.read(LOCAL_CONFIG_PATH)
        if config['main']['license'] != GLOBAL_LICENSE_PATH:
            config.set('main', 'license', str(GLOBAL_LICENSE_PATH))
            with open(LOCAL_CONFIG_PATH, 'w') as configFile:
                config.write(configFile)
            print('Resetting license config to: {}'.format(GLOBAL_LICENSE_PATH))
        else:
            print('License config is already set.')

class KeyFrameProConfig():
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = None
        self.old_config = None
        if os.path.exists(self.config_path):
            self.config = configparser.ConfigParser()
            self.config.read(self.config_path)

            # create a copy of the original config
            config_string = StringIO.StringIO()
            self.config.write(config_string)
            config_string.seek(0) 
            self.old_config = configparser.ConfigParser()
            self.old_config.read_file(config_string)

    def override(self, section, option, value):
        if not self.config:
            return
        self.config.set(section, option, str(value))

    def __enter__(self):
        if not self.config:
            return
        with open(self.config_path, 'w') as configFile:
            self.config.write(configFile)

    def __exit__(self, *kw, **kwargs):
        if not self.config:
            return
        with open(self.config_path, 'w') as configFile:
            self.old_config.write(configFile)

def setup_parser(title):
    ''' create the parser '''
    parser = argparse.ArgumentParser(description=title, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', dest='inputs', nargs='+', help='Input video paths', default=[])
    parser.add_argument('-ci', dest='cutin', nargs='+', help='Cut-in for each video', default=[])
    parser.add_argument('-co', dest='cutout', nargs='+', help='Cut-out for each video', default=[])
    return parser

def get_available_port():
    ''' Get the next port available for keyframePro '''
    result_port = DEFAULT_PORT
    used_ports = []
    for proc in psutil.process_iter(): 
        process = psutil.Process(proc.pid)
        pname = process.name()
        if pname == PROCESS_NAME:
            connections = process.connections()
            for con in connections:
                port = con.laddr[1]
                used_ports.append(port)
    if used_ports:
        sorted_ports = sorted(used_ports)
        result_port = sorted_ports[-1] + 1
    print('Available port for keyframePro: {}'.format(result_port))
    return result_port

def launch_keyframe_pro(inputs=[], cutin=[], cutout=[], timeline_name='My Timeline'):
    ''' Launch keyframe Pro with new port config '''
    kfpConfig = KeyFrameProConfig(config_path=LOCAL_CONFIG_PATH)
    port = get_available_port()
    # override the connection port
    kfpConfig.override(section='preferences', option='cmdPort', value=port)
    # make sure to open new instance
    kfpConfig.override(section='preferences', option='openmediainnewplayers', value='true')
    # add ffmpeg path
    kfpConfig.override(section='preferences', option='ffmpegexepath', value=config.Software.ffmpeg)
    # turn of autoplay cuz the player will try to play new source immediately when added
    kfpConfig.override(section='playback', option='autoplay', value='false')
    # turn annotation visible when play
    kfpConfig.override(section='video', option='annotationDisplayType', value='0')

    # if inputs is a .txt file
    file_inputs = []
    temp_path = ''
    if len(inputs) == 1 and inputs[0].endswith('.txt'):
        with open(inputs[0], 'r') as fi:
            file_inputs = [f.replace('\n', '') for f in fi.readlines()]
        temp_path = inputs[0]
    else:
        file_inputs = inputs 
    file_inputs = [i.replace('\\', '/') for i in file_inputs]
    print('Number of file(s): {}'.format(len(file_inputs)))

    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    with kfpConfig:
        kfp_process = subprocess.Popen(KEYFRAMEPRO_PATH, shell=True)
        time.sleep(1)
        
    print('New Keyframe Pro using port: {}'.format(port))
    # construct a time line
    client = keyframe_pro_client.KeyframeProClient(timeout=10)
    if client.connect(port=port) and client.initialize():
        client.new_project(empty=True)

        # generate ranges
        import_ranges = [[-1, -1]] * len(file_inputs)

        # overrides ranges with cut-in from arg
        if cutin:
            cit = iter(cutin)
            for ci in cit:
                index = int(ci)
                value = int(next(cit))
                import_ranges[index][0] = value
        # overrides ranges with cut-out from arg
        if cutout:
            cot = iter(cutout)
            for co in cot:
                index = int(co)
                value = int(next(cot))
                import_ranges[index][1] = value

        # Create a new timeline
        timeline = client.add_timeline(timeline_name)
        add_to_timeline(port=port, timeline=timeline, inputs=file_inputs, import_ranges=import_ranges)
    print('PORT={}'.format(port))

    if temp_path:
        try:
            os.remove(temp_path)
        except:
            pass
    return port

def add_to_timeline(port, timeline, inputs, import_ranges=[]):
    if not import_ranges:
        import_ranges = [[-1, -1]] * len(inputs)

    # Import sources
    sources = []
    for path, r in zip(inputs, import_ranges):
        sources.append(client.import_file(path, range_start=r[0], range_end=r[1]))

    
    for source in sources:
        client.insert_element_in_timeline(source['id'], timeline['id'])

    # Make the timeline active in viewer A
    client.set_active_in_viewer(timeline['id'], 0)
    # client.disconnect()

if __name__ == "__main__":
    print('=== Setting up license...')
    setup_license()

    print('=== Starting Keyframe Pro...')
    parser = setup_parser('Keyframe Pro port setup')
    params = parser.parse_args()    
    launch_keyframe_pro(inputs=params.inputs, cutin=params.cutin, cutout=params.cutout)
    
'''
python D:/dev/core/rf_utils/keyframepro_utils.py -i D:/__playground/test_keyframepro/src1.mov D:/__playground/test_keyframepro/src2.mov

from rf_utils import keyframepro_utils as kfpu
reload(kfpu)
kfpu.launch_keyframe_pro(inputs=['D:/__playground/test_keyframepro/src1.mov', 'D:/__playground/test_keyframepro/src2.mov', 'D:/__playground/test_keyframepro/src3.mov', 'D:/__playground/test_keyframepro/src4.mov'], cutin=[0, 10, 2, 5], cutout=[2,10,3,15])
'''

