from icoextract import IconExtractor
import os

# 这是原版的 exe (确认你已经把它改名为 scrcpy-core.exe 了)
source_exe = "scrcpy-core.exe"

if not os.path.exists(source_exe):
    print(f"错误：找不到 {source_exe}，请确认文件名正确！")
else:
    extractor = IconExtractor(source_exe)
    # 直接提取出原汁原味的 ico
    extractor.export_icon("icon.ico")
    print("成功！已从原版程序提取出完美画质的 icon.ico")