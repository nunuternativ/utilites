import os
import sys
import subprocess
import base64
import tempfile
import time
import filecmp
from textwrap import dedent
dedentString = lambda s : dedent(s[1:])[:-1]

import rf_config as config
# reload(config)
from rf_utils.context import context_info
# reload(context_info)

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)

COMPUTERNAME = r'\\{computer}'.format(computer=os.environ['computername'])
USER = base64.b64decode('VEhcQWRtaW5pc3RyYXRvcg==')
PASSWORD = base64.b64decode('UmlmZkAyMDE4')
PSEXEC = config.Software.psexec
SHARE_TEMP_DIR = '{shared_drive}\\logs\\temp\\remote_psexec'.format(shared_drive=config.Env.pipelineGlobal)
PYTHONW_PATH = config.Software.pythonwPath
LOCAL_PYTHONW_PATH = config.Software.localPythonw
SILENTCMD_PATH = config.Software.silentCmd

si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

if os.path.exists(config.Env.pipelineGlobal):
    if not os.path.exists(SHARE_TEMP_DIR):
        os.makedirs(SHARE_TEMP_DIR)

def isRemote():
    if COMPUTERNAME != '\\\\{}'.format(os.environ['computername']):
        return True
    else:
        return False

def run_cmd(cmd, wait=True):
    ADMIN_EXEC = [PSEXEC,
            COMPUTERNAME,
            '-u',
            USER,
            '-p',
            PASSWORD,
            '-accepteula']

    kwargs = {'suffix':'.bat'}

    # use shared location if it's not the local machine that's running the script
    exe_path = ["{}".format(to_unc_path(SILENTCMD_PATH))]
    remote = False
    if isRemote():
        kwargs['dir'] = SHARE_TEMP_DIR
        # in remote, we want to copy over the bat and just let windows run it silently
        # also with -d, we dont' need to wait for the process to finish
        exe_path = ['-d', '-c']
        remote = True

    # create bat
    bat_fh, temp_bat = tempfile.mkstemp(**kwargs)
    logger.debug('Temp .bat created: {temp_bat}'.format(temp_bat=temp_bat))
    with open(temp_bat, 'w') as tb:
        tb.write(cmd)
    os.close(bat_fh)

    # add the bat
    temp_bat = "{}".format(to_unc_path(temp_bat))
    exe_path.append(temp_bat)

    cmd_list = ADMIN_EXEC + exe_path
    logger.debug('Run cmd {computer}: {cmd_list}'.format(computer=COMPUTERNAME, cmd_list=cmd_list))
    if wait:
        process = subprocess.Popen(cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=si)
        stdout, stderr = process.communicate()
        logger.debug('Process stdout: {stdout}'.format(stdout=stdout))
        logger.debug('Process stderr: {stderr}'.format(stderr=stderr))

        # remove temp file
        os.remove(temp_bat)
        logger.debug('Temp .bat removed')
    else:
        process = subprocess.Popen(cmd_list,
                stdin=None,
                stdout=None,
                stderr=None,
                startupinfo=si)
        logger.info('Command is running on: {computer}...'.format(computer=COMPUTERNAME))

def run_python(cmd, wait=True):
    ADMIN_EXEC = [PSEXEC,
            COMPUTERNAME,
            '-u',
            USER,
            '-p',
            PASSWORD,
            '-accepteula']

    # create temp py file
    kwargs = {'suffix':'.py'}
    exe_path = to_unc_path(PYTHONW_PATH)

    # use shared location if it's not the local machine that's running the script
    if isRemote():
        kwargs['dir'] = SHARE_TEMP_DIR
        exe_path = to_unc_path(LOCAL_PYTHONW_PATH)  # running python remotely only supports local exe path

    fh, temp_py = tempfile.mkstemp(**kwargs)
    logger.debug('Temp .py created: {temp_py}'.format(temp_py=temp_py))
    with open(temp_py, 'w') as tf:
        tf.write(cmd)
    os.close(fh)

    cmd_list = ADMIN_EXEC + ["{}".format(exe_path), "{}".format(to_unc_path(temp_py))]
    logger.debug('Run python {computer}: {cmd_list}'.format(computer=COMPUTERNAME, cmd_list=cmd_list))
    if wait:
        process = subprocess.Popen(cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=si)
        stdout, stderr = process.communicate()
        logger.debug('Process stdout: {stdout}'.format(stdout=stdout))
        logger.debug('Process stderr: {stderr}'.format(stderr=stderr))

        # remove temp
        os.remove(temp_py)
        logger.debug('Temp .py removed')
    else:
        process = subprocess.Popen(cmd_list,
                stdin=None,
                stdout=None,
                stderr=None,
                startupinfo=si)
        logger.info('Python is running on: {computer}...'.format(computer=COMPUTERNAME))

def are_dir_trees_equal(dir1, dir2):
    dirs_cmp = filecmp.dircmp(dir1, dir2)
    if len(dirs_cmp.left_only)>0 or len(dirs_cmp.right_only)>0 or \
        len(dirs_cmp.funny_files)>0:
        return False
    (_, mismatch, errors) =  filecmp.cmpfiles(
        dir1, dir2, dirs_cmp.common_files, shallow=False)
    if len(mismatch)>0 or len(errors)>0:
        return False
    for common_dir in dirs_cmp.common_dirs:
        new_dir1 = os.path.join(dir1, common_dir)
        new_dir2 = os.path.join(dir2, common_dir)
        if not are_dir_trees_equal(new_dir1, new_dir2):
            return False
    return True

def to_unc_path(path):
    ''' convert any path to UNC '''
    obj = context_info.RootPath(path)
    path = obj.unc_path()
    path = path.replace('/', '\\')
    return path

def remove(path, check_result=True, **kwargs):
    path = to_unc_path(path)

    cmd = '''
    import os
    os.remove(r"{path}")
    '''.format(path=path)

    cmd = dedentString(cmd)
    run_python(cmd=cmd, **kwargs)

    if check_result:
        try:
            if not os.path.exists(path):
                return True
            else:
                return False
        except Exception as e:
            logger.error(e)

def makedirs(path, check_result=True, **kwargs):
    path = to_unc_path(path)
    # print path
    cmd = '''
    import os
    os.makedirs(r"{path}")
    '''.format(path=path)

    cmd = dedentString(cmd)
    # print cmd
    run_python(cmd=cmd, **kwargs)

    if check_result:
        try:
            # check result
            if os.path.exists(path):
                return True
            else:
                return False
        except Exception as e:
            logger.error(e)

def rmtree(path, check_result=True, **kwargs):
    path = to_unc_path(path)

    cmd = '''
    import shutil
    shutil.rmtree(r"{path}")
    '''.format(path=path)

    cmd = dedentString(cmd)
    run_python(cmd=cmd, **kwargs)

    if check_result:
        try:
            # check result
            if not os.path.exists(path):
                return True
            else:
                return False
        except Exception as e:
            logger.error(e)

def rename(old_name, new_name, check_result=True, **kwargs):
    old_name = to_unc_path(old_name)
    new_name = to_unc_path(new_name)

    cmd = '''
    import os
    os.rename(r"{old_name}", r"{new_name}")
    '''.format(old_name=old_name, new_name=new_name)

    cmd = dedentString(cmd)
    run_python(cmd=cmd, **kwargs)

    if check_result:
        try:
            # check result
            if os.path.exists(new_name) and not os.path.exists(old_name):
                return True
            else:
                return False
        except Exception as e:
            logger.error(e)

def copyfile(source, destination, check_result=True, **kwargs):
    source = to_unc_path(source)
    destination = to_unc_path(destination)

    cmd = '''
    import shutil
    shutil.copyfile(r"{source}", r"{destination}")
    '''.format(source=source, destination=destination)

    cmd = dedentString(cmd)
    run_python(cmd=cmd, **kwargs)

    if check_result:
        try:
            # check result
            if os.path.exists(destination) and filecmp.cmp(source, destination, shallow=True):
                return True
            else:
                return False
        except Exception as e:
            logger.error(e)

def win_copy_file(source, destination, check_result=True, **kwargs):
    source = to_unc_path(source)
    destination = to_unc_path(destination)

    cmd = '''
    copy /y "{source}" "{destination}"
    exit
    '''.format(source=source, destination=destination)
    cmd = dedentString(cmd)
    run_cmd(cmd=cmd, **kwargs)

    if check_result:
        try:
            # check result
            if os.path.exists(destination) and filecmp.cmp(source, destination, shallow=True):
                return True
            else:
                return False
        except Exception as e:
            logger.error(e)

def win_copy_files(sources, destinations, check_result=False, **kwargs):
    cmd_list = []
    for source, destination in zip(sources, destinations):
        source = to_unc_path(source)
        destination = to_unc_path(destination)
        cmd = 'copy /y "{source}" "{destination}"'.format(source=source, destination=destination)
        cmd_list.append(cmd)
    cmd_list.append('exit')
    cmd_str = '\n'.join(cmd_list)
    run_cmd(cmd=cmd_str, **kwargs)

    if check_result:
        try:
            for destination in destinations:
                if not os.path.exists(destination) or not filecmp.cmp(source, destination, shallow=True):
                    return False
            return True
        except Exception as e:
            logger.error(e)

def win_copy_directory(source, destination, check_result=False, **kwargs):
    source = to_unc_path(source)
    destination = to_unc_path(destination)

    cmd = '''
    robocopy "{source}" "{destination}" /S /E /Z /ZB /R:2 /W:5 /TBD /NP /V /MT:32
    exit
    '''.format(source=source, destination=destination)
    cmd = dedentString(cmd)
    run_cmd(cmd=cmd, **kwargs)

    if check_result:
        try:
            if are_dir_trees_equal(source, destination):
                return True
            else:
                return False
        except Exception as e:
            logger.error(e)

def test():
    user = os.environ['RFUSER']

    test_root = 'P:/Project/test'.replace('/', '\\')
    logger.info('===== {}'.format(test_root))

    # create user folder
    user_dir = '{test_root}\\{user}'.format(test_root=test_root, user=user)
    logger.info('Making dir: {}'.format(user_dir))
    result = makedirs(user_dir)
    if not result:
        raise Exception('Unable to Make dir: {}'.format(user_dir))
    logger.info('Make dir done: {}'.format(user_dir))

    logger.info('Creating temp files...')
    # create files
    fh1, f1 = tempfile.mkstemp(suffix='_write')
    fh2, f2 = tempfile.mkstemp(suffix='_rename')
    fh3, f3 = tempfile.mkstemp(suffix='_remove')
    fh4, f4 = tempfile.mkstemp(suffix='_tree')

    f1_name = os.path.basename(f1)
    f2_name = os.path.basename(f2)
    f3_name = os.path.basename(f3)
    f4_name = os.path.basename(f4)
    logger.info('Temp file create done: {}'.format([f1, f2, f3, f4]))

    # copy files to folder
    f1_destination = os.path.join(user_dir, f1_name)
    logger.info('Copying file with xcopy: {} ---> {}'.format(f1, f1_destination))
    win_copy_file(f1, f1_destination)
    logger.info('File copied with xcopy: {}'.format(f1_destination))

    destinations = [os.path.join(user_dir, os.path.basename(f)) for f in [f2, f3]]
    logger.info('Copying multiple files with win copy: {}'.format(destinations))
    result = win_copy_files(sources=[f2, f3],
        destinations=destinations, check_result=True)
    if not result:
        raise Exception('Unable to copy multiple files with win copy: %s' %[f2, f3])
    logger.info('Multiple files copied: {}'.format(destinations))

    # rename
    old_name = os.path.join(user_dir, f2_name)
    new_name = os.path.join(user_dir, 'renamed_success')
    logger.info('Renaming: {} ---> {}'.format(old_name, new_name))
    result = rename(old_name, new_name)
    if not result:
        raise Exception('Unable to rename: {} ---> {}'.format(old_name, new_name))
    logger.info('Rename success.')

    # remove file
    file_to_remove = os.path.join(user_dir, f3_name)
    logger.info('Removing file: {}'.format(file_to_remove))
    result = remove(file_to_remove)
    if not result:
        raise Exception('Unable to remove: {}'.format(file_to_remove))
    logger.info('File removed: {}'.format(file_to_remove))

    # create sub dir
    sub_dir = '{user_dir}\\tree'.format(user_dir=user_dir)
    logger.info('Making sub-dir: {}'.format(sub_dir))
    result = makedirs(sub_dir)
    if not result:
        raise Exception('Unable to make sub-dir: {}'.format(sub_dir))
    logger.info('Making sub-dir done: {}'.format(sub_dir))

    # move f4 to sub dir
    destination = os.path.join(sub_dir, f4_name)
    logger.info('Copying file with shutil: {} ---> {}'.format(f4, destination))
    result = copyfile(f4, destination)
    if not result:
        raise Exception('Unable to copyfile with shutil: {}'.format(destination))
    logger.info('File copied with shutil: {}'.format(destination))

    # copytree with win copy
    logger.info('Tree copying: {}'.format(sub_dir))
    dir_des = '{user_dir}\\tree_copied'.format(user_dir=user_dir)
    result = win_copy_directory(sub_dir, dir_des, check_result=True)
    if not result:
        raise Exception('Unable to win_copy_directory: {}'.format(dir_des))
    logger.info('Tree copied: {}'.format(dir_des))

    # remove tree
    logger.info('Removing_tree: {}'.format(sub_dir))
    result = rmtree(sub_dir)
    if not result:
        raise Exception('Unable to rmtree: {}'.format(sub_dir))
    logger.info('Tree removed: {}'.format(sub_dir))
