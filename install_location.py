import os
import platform
import json

def get_path(program_name):
    curr_os = platform.system()
    exe_path = ''
    if curr_os == 'Windows':
        from rf_utils import win_reg_utils

        key = r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
        for sub_key in win_reg_utils.get_sub_keys(key):
            path = win_reg_utils.join(key, sub_key)
            value = win_reg_utils.get_values(path, ['DisplayName', 'InstallLocation'])

            if value and 'DisplayName' in value and value['DisplayName'] == program_name:
                if 'InstallLocation' in value and value['InstallLocation']:
                    program_location = value['InstallLocation']
                    return program_location

def get_maya_exe(program_name):
    program_location = get_path(program_name)
    if program_location:
        exe_location = os.path.join(program_location, 'bin', 'maya.exe')
        if os.path.exists(exe_location):
            return exe_location


def get_dropbox_root():
    appdata_path = os.environ['APPDATA']
    local_appdata_path = os.environ['LOCALAPPDATA']
    dropbox_paths = []
    for path in (appdata_path, local_appdata_path):
        # find dropbox info.json
        json_path = os.path.join(path, 'Dropbox', 'info.json')
        if not os.path.exists(json_path):
            continue

        # load json
        json_info = {}
        with open(json_path, 'r') as f:
            json_info = json.load(f)
        try:
            dropbox_root = json_info['personal']['path']
            return dropbox_root
        except KeyError as e:
            continue