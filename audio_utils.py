import os
import tempfile
import json
import subprocess

import rf_config as config

si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

def get_audio_cutting(all_audios, seq_set):
    sound_data = []
    seq_start = min(seq_set)
    for sound in all_audios:
        fileName = pm.sound(sound, q=True, f=True)
        offset = int(round(pm.sound(sound, q=True, offset=True)))
        sourceStart = int(round(sound.sourceStart.get()))
        silence = int(round(sound.silence.get()))
        start = offset + silence 
        end = int(round(pm.sound(sound, q=True, endTime=True))) - 1
        duration = int(round(pm.sound(sound, q=True, sourceEnd=True)))
        sound_range = range(start, end+1)
        intersectionSet = seq_set.intersection(set(sound_range))
        if not intersectionSet:
            continue
        intersection_frames = list(intersectionSet)
        intersection_frames.sort()

        local_start = intersection_frames[0] - start
        local_end = intersection_frames[-1] - start - sourceStart
        global_start = intersection_frames[0] - seq_start
        # print(local_start, local_end)
        data = {'file': fileName, 
            'start': local_start + sourceStart,
            'global_start': global_start,
            'duration': duration,
            'end': local_end}
        sound_data.append(data)

    return sound_data

def generate_silent_wav(total_time, path=None):
    fh = None
    if not path:
        fh, path = tempfile.mkstemp(prefix='silent_', suffix='.wav')
    subprocess.call([
        config.Software.ffmpeg,
        '-y',
        '-f',
        'lavfi',
        '-i',
        'anullsrc=r=48000',
        '-t',
        '{total_time}'.format(total_time=total_time),
        '-q:a',
        '9',
        '-acodec',
        'pcm_s16le',
        '-ac',
        '2',
        '{path}'.format(path=path)
    ], startupinfo=si)
    if fh != None:
        os.close(fh)

    return path

def cut_wav(input_path, time_to_cut, cut_duration, output_path=None):
    # ffmpeg -ss 0.9166666666666667 -i "D:\__playground\cut_sound\hnm_mv_q0010_s0020_edit_sound.hero.wav" -t 3.458333333333333 -y "D:\__playground\cut_sound\hnm_mv_q0010_s0020_edit_sound.hero_EDITED1.wav"
    fh = None
    if not output_path: 
        fh, output_path = tempfile.mkstemp(suffix='.wav')

    subprocess.call([
        config.Software.ffmpeg,
        '-ss',
        '{time_to_cut}'.format(time_to_cut=time_to_cut),
        '-i',
        '{input_path}'.format(input_path=input_path),
        '-t',
        '{cut_duration}'.format(cut_duration=cut_duration),
        '-y',
        '{output_path}'.format(output_path=output_path)
    ], startupinfo=si)

    if fh != None:
        os.close(fh)

    return output_path

def mix_wavs(total_time, wavs, output_path=None, delete_source=True):
    '''
    ffmpeg -i D:/__playground/cut_sound/silent.wav 
    -i D:/__playground/cut_sound/back.wav 
    -i D:/__playground/cut_sound/front.wav 
    -filter_complex 
    "aevalsrc=0:d=2.75[s1];
    aevalsrc=0:d=0.0[s2];
    [s1][1:a]concat=n=2:v=0:a=1[ac1];
    [s2][2:a]concat=n=2:v=0:a=1[ac2];
    [0:a][ac1][ac2]amix=3:dropout_transition=0,volume=2[aout]" 
    -map [aout] 
    -y D:/__playground/cut_sound/mix2.wav
    '''
    fh = None
    if not output_path: 
        fh, output_path = tempfile.mkstemp(suffix='.wav')

    # generate silent wav
    # silent_path = 'D:/__playground/cut_sound/silent.wav'
    silent_path = generate_silent_wav(total_time)
    argList = [config.Software.ffmpeg, '-i', str(silent_path)]

    # add input to ffmpeg args (-i)
    path_strs = []
    shift_durs = []
    concats = []
    num_wavs = len(wavs)
    i = 1 
    for wav, st in wavs:
        path_strs.append('-i')
        path_strs.append(wav)

        shift_durs.append('aevalsrc=0:d={0}[s{1}]'.format(st, i))
        concats.append('[s{0}][{0}:a]concat=n=2:v=0:a=1[ac{0}]'.format(i))

        i += 1

    shift_durs_str = ';'.join(shift_durs)
    concats_str = ';'.join(concats)
    acs = ['[ac{}]'.format(a) for a in range(1, num_wavs+1)]
    acs_str = ''.join(acs)
    filter_complex_str = '"{0};{1};[0:a]{2}amix={3}:dropout_transition=2,volume={4}[aout]"'.format(shift_durs_str, concats_str, acs_str, num_wavs+1, num_wavs)
    argList = argList + path_strs + ['-filter_complex'] + [filter_complex_str] + ['-map', '[aout]', '-y', output_path] 
    # print(argList)
    argStr = ' '.join(argList)
    argStr = argStr.replace('\\', '/')
    # print(argStr)
    # call ffmpeg
    subprocess.call(argStr, startupinfo=si)

    if fh != None:
        os.close(fh)

    if delete_source:
        to_del = [silent_path] + [w[0] for w in wavs]
        for f in to_del:
            try:
                os.remove(f)
                print('{}: removed'.format(f))
            except:
                print('cannot delete: {}'.format(f))
                pass

    return output_path

def video_has_audio(input_path):
    argList = [config.Software.ffprobe, '-i', input_path.replace('\\', '/'), 
             '-show_streams', '-select_streams', 'a', '-of', 'json', '-loglevel', 'error']
    output = None
    try:
        ps = subprocess.Popen(argList, stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT, 
                        startupinfo=si)
        output = json.loads(ps.communicate()[0])['streams']
    except:
        pass
    return output

def extract_wav_from_video(input_path, output_path=None):
    # ffmpeg -i mpeg-4videofilename -vn -ac 2 -ar 44100 -ab 320k -f mp3 output.mp3
    if not output_path:
        # write to temp
        fh, output_path = tempfile.mkstemp(suffix='.wav')
        os.close(fh)

    argList = [config.Software.ffmpeg, '-y', '-i', str(input_path), '-vn', '-ac', '2', '-ar', '44100', '-ab', '320k', output_path]
    argStr = ' '.join(argList)
    argStr = argStr.replace('\\', '/')

    output = subprocess.call(argStr, startupinfo=si)
    if output == 0 and os.path.exists(output_path):
        return output_path