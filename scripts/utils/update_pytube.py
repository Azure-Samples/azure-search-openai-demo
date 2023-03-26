import re


if __name__ == '__main__':
    with open('/home/sindre/anaconda3/envs/whisper/lib/python3.9/site-packages/pytube/cipher.py', 'r') as file:
        filedata = file.read()

    filedata = filedata.replace('transform_plan_raw = find_object_from_startpoint(raw_code, match.span()[1] - 1)', 'transform_plan_raw = js')

    with open('/home/sindre/anaconda3/envs/whisper/lib/python3.9/site-packages/pytube/cipher.py', 'w') as file:
        file.write(filedata)
    
    print(filedata)