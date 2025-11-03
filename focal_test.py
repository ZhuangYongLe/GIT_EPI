import time, os, sys, urandom, gc, math, json
from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH
from machine import Pin
from machine import FPIOA
from machine import UART

object_real_width_mm = 40   # 物体实际宽度（毫米）
object_distance_mm = 100    # 物体到摄像头距离（毫米）
blue_threshold = (6, 51, -7, 19, -56, -17)  # 物体颜色阈值
blue_threshold = (6, 51, -7, 19, -56, -17)

DISPLAY_MODE = "LCD"

picture_width = 800
picture_height = 480

if DISPLAY_MODE == "LCD":
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
def find_max(blobs):
    max_blob = None
    max_size = 0
    for blob in blobs:
        if blob[2] * blob[3] > max_size:
            max_blob = blob
            max_size = blob[2] * blob[3]
    return max_blob

try:
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    sensor2 = Sensor(id=2)
    sensor2.reset()
    sensor2.set_framesize(width=320, height=160, chn=CAM_CHN_ID_0)
    sensor2.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)
      # 初始化媒体管理器
    MediaManager.init()
    sensor2.run()
    while True:

        img = sensor2.snapshot(chn=CAM_CHN_ID_0)
        blobs = img.find_blobs([blue_threshold])  # 蓝
        if blobs:
            max_blob = find_max(blobs)
            if max_blob.pixels() > 1000:
                img.draw_rectangle(max_blob.rect())
                img.draw_cross(max_blob.cx(), max_blob.cy())
                object_pixel_width = max_blob.w()
                print("物体像素宽度:", object_pixel_width)
                focal_length = (object_pixel_width * object_distance_mm) / object_real_width_mm
                print("测得焦距: %.2f mm" % focal_length)
            else:
                print("未检测到目标物体")
        Display.show_image(img, x=int((DISPLAY_WIDTH - 320) / 2), y=int((DISPLAY_HEIGHT - 160) / 2))

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
