import os
import shutil
path=input("Enter the path of your directory: ")
ci=0
cv=0
ca=0
co=0

with os.scandir(path) as entries:
    if not os.path.exists(f"{path}/IMAGES"):
          os.makedirs(f"{path}/IMAGES")
    if not os.path.exists(f"{path}/VIDEOS"):
         os.makedirs(f"{path}/VIDEOS")
    if not os.path.exists(f"{path}/AUDIO"):
        os.makedirs(f"{path}/AUDIO")
    if not os.path.exists(f"{path}/OTHERS"):
     os.makedirs(f"{path}/OTHERS")
    for entry in entries:
        if entry.is_file():
            name, ext = os.path.splitext(entry.name)
            if ext.upper()==".JPEG" or ext.upper()==".JPG" or ext.upper()==".PNG":
                shutil.move(f"{path}/{name}{ext}", f"{path}/IMAGES/{name}{ext}")
                ci=ci+1
            elif ext.upper()==".MP4":
                shutil.move(f"{path}/{name}{ext}", f"{path}/VIDEOS/{name}{ext}")
                cv=cv+1
            elif ext.upper()==".WAV" or ext.upper()==".MP3":
                shutil.move(f"{path}/{name}{ext}", f"{path}/AUDIO/{name}{ext}")
                ca=ca+1
            else:
                shutil.move(f"{path}/{name}{ext}", f"{path}/OTHERS/{name}{ext}")
                co=co+1
    print(f"IMAGES TRANSFERRED :{ci}")
    print(f"VIDEOS TRANSFERRED :{cv}")
    print(f"AUDIO TRANSFERRED :{ca}")
    print(f"OTHERS TRANSFERRED :{co}")

