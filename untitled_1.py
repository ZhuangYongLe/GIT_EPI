import time, os, sys, urandom, gc, math, json
from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH
from machine import Pin
from machine import FPIOA
from machine import UART


#全局变量
Auto_Capture_Enable = False #是否启动自动拍照
last_captrue_time = 0 #上次拍照时间
capture_interval = 2000 #ms #间隔时间
photos_per_session = 15  #每次拍照次数
current_session_count = 0 #当前拍了多少张
capture_session_time = 0 #拍照持续了多久
photos_count = 0 #拍照计数器
photos_save_path = "/sdcard/photos_save"
def auto_captrue_photos():
    global Auto_Capture_Enable,last_captrue_time,current_session_count,capture_session_time
    Auto_Capture_Enable = True
    current_session_count = 0
    capture_session_time = 0
    last_captrue_time = time.ticks_ms
    print("开始拍照模式")
def stop_auto_captrue_photos():
    global Auto_Capture_Enable
    Auto_Capture_Enable = False
    print("结束拍照模式")
ddef ensure_photos_directory():
    """确保照片目录存在 - 使用与阈值文件操作一致的错误处理"""
    try:
        os.mkdir(PHOTOS_DIR)
        print(f"创建照片目录: {PHOTOS_DIR}")
        return True
    except OSError:
        # 目录已存在，与阈值文件操作中的处理方式一致
        return True
    except Exception as e:
        print(f"创建照片目录失败: {str(e)}")
        return False

def capture_photo(img, prefix="photo"):
    
    global photo_counter
    try:
        if not ensure_photos_directory():
            return False
        
        filename = f"{PHOTOS_DIR}{prefix}_{photo_counter:04d}.bmp"
        photo_counter += 1
        
        
        with open(filename, 'wb') as f:
            img.save(filename)
        
        
        print(f"照片已保存: {filename}")
        return True
        
    except Exception as e:

        print(f"保存照片失败: {str(e)}")
        return False

def continuous_capture_handler():
    """连续拍照处理函数"""
    global continuous_capture_mode, capture_count, total_captures, capture_interval, last_capture_time
    
    if not continuous_capture_mode:
        return
    
    current_time = time.ticks_ms()
    elapsed_time = time.ticks_diff(current_time, last_capture_time) / 1000
    
    if elapsed_time >= capture_interval and capture_count < total_captures:
        # 拍摄照片
        img0 = sensor0.snapshot(chn=CAM_CHN_ID_0)
        if capture_photo(img0, "continuous"):
            capture_count += 1
            print(f"已拍摄 {capture_count}/{total_captures} 张照片")
        
        last_capture_time = current_time
        
        # 如果已完成一轮拍摄，重置计数器并等待下一轮
        if capture_count >= total_captures:
            capture_count = 0
            print(f"完成一轮拍摄，等待 {capture_interval} 秒后继续...")
try:












    while True:
    



except KeyboardInterrupt as e:
    print("用户终止：", e)  # 捕获键盘中断异常
except BaseException as e:
    print(f"异常：{e}")  # 捕获其他异常
finally:
    # 清理资源
    Display.deinit()

    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)  # 启用睡眠模式的退出点,
    time.sleep_ms(100)  # 延迟100毫秒
    MediaManager.deinit()

# 主程序入口
if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)  # 启用退出点

