import logging 
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def make_retries(func_req, args, retries_count=5):
    while retries_count > 0:
        try:
            result = func_req(*args)
            return result
        except Exception as e:
            print("retries:", e)
            retries_count = retries_count - 1
    return False


def get_connection(local_name):
    import ctypes
    from ctypes import wintypes

    mpr = ctypes.WinDLL('mpr')

    ERROR_SUCCESS   = 0x0000
    ERROR_MORE_DATA = 0x00EA

    wintypes.LPDWORD = ctypes.POINTER(wintypes.DWORD)
    mpr.WNetGetConnectionW.restype = wintypes.DWORD
    mpr.WNetGetConnectionW.argtypes = (wintypes.LPCWSTR,
                                       wintypes.LPWSTR,
                                       wintypes.LPDWORD)

    # check it the drive is a network drive
    length = (wintypes.DWORD * 1)()
    result = mpr.WNetGetConnectionW(local_name, None, length)
    if result != ERROR_MORE_DATA:
        logger.debug('%s is not a network drive.' %local_name)
        return
        # raise ctypes.WinError(result)

    # get remote name
    remote_name = (wintypes.WCHAR * length[0])()
    result = mpr.WNetGetConnectionW(local_name, remote_name, length)
    if result != ERROR_SUCCESS:
        raise ctypes.WinError(result)
    return remote_name.value

def is_local_drive(drive):
    remote_name = get_connection(drive)
    print('remote_name: %s' %remote_name)
    logger.debug('remote_name: %s' %remote_name)

    if not remote_name or remote_name.startswith('\\\\localhost'):
        return True
    else:
        return False

def is_network_drive(drive): 
    return not is_local_drive(drive)
    