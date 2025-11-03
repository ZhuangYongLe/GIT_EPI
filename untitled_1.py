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

img0 = None
img1 = None
sensor0 = None
sensor1 = None
DISPLAY_MODE = "LCD"

picture_width = 800
picture_height = 480

if DISPLAY_MODE == "LCD":
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
    
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
def ensure_photos_directory():
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

def capture_15_photos():
    global photos_count
    ensure_photos_directory()
    for i in range(15):
        img = sensor0.snapshot(chn=CAM_CHN_ID_0)
        filename = f"{photos_save_path}/photo_{photos_count:04d}.bmp"
        photos_count += 1
        try:
            img.save(filename)
            print(f"已保存: {filename}")
        except Exception as e:
            print(f"保存失败: {e}")

# 拍照按钮区域（假设为屏幕下方中间，宽100高50）
PHOTO_BTN_RECT = (350, 430, 100, 50)
PHOTO_BTN_TEXT = "拍照"

def draw_photo_button(screen):
    x, y, w, h = PHOTO_BTN_RECT
    screen.draw_rectangle(x, y, w, h, (0, 200, 0), thickness=2, fill=True)
    screen.draw_string_advanced(x+20, y+15, 24, PHOTO_BTN_TEXT, color=(255,255,255))

# 检测触摸是否在拍照按钮区域

def check_touch_photo_button():
    touchP = TOUCH(0).read(2)
    if touchP:
        p = touchP[0]
        x, y = p.x, p.y
        bx, by, bw, bh = PHOTO_BTN_RECT
        if bx <= x <= bx+bw and by <= y <= by+bh:
            return True
    return False

try:
    # 显示初始化
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    if DISPLAY_MODE == "LCD":
        Display.init(Display.LT9611, width=640,  height=480, to_ide=True)

    #定义id号
    sensor0 = Sensor(id=0)
    sensor0.reset()
    sensor0.set_framesize(width=800, height=480, chn=CAM_CHN_ID_0)
    sensor0.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)
    sensor0.set_hmirror(False)
    sensor0.set_vflip(False)

    # 重置摄像头sensor1并配置参数
    sensor1 = Sensor(id=1)
    sensor1.reset()
    sensor1.set_framesize(width=320,  height=160, chn=CAM_CHN_ID_1)
    sensor1.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_1)
    sensor1.set_hmirror(False)
    sensor1.set_vflip(False)

    # 初始化媒体管理器
    MediaManager.init()


        # 启动传感器
    sensor0.run()
    sensor1.run()

    # 尝试从SD卡加载阈值
    load_thresholds_from_sd()

    # 创建一个FPS计时器，用于实时计算每秒帧数
    clock = time.clock()

    while True:
        clock.tick()
        os.exitpoint()
        img1 = sensor1.snapshot(chn=CAM_CHN_ID_0)
        screen = img1.copy()
        draw_photo_button(screen)
        if check_touch_photo_button():
            print("触摸拍照按钮，开始连拍15张...")
            capture_15_photos()
        Display.show_image(screen, x=int((DISPLAY_WIDTH - picture_width) / 2), y=int((DISPLAY_HEIGHT - picture_height) / 2))

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

