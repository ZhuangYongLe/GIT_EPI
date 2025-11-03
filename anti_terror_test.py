# 反恐区识别测试代码（从Counter terrorism robot_V2.py提取）
from media.sensor import *
from media.display import *
import time

green_threshold = (76, 21, -46, -21, 12, 40)
blue_threshold = (6, 51, -7, 19, -56, -17)

CAM_CHN_ID_1 = 1

DISPLAY_MODE = "LCD"

picture_width = 800
picture_height = 480

if DISPLAY_MODE == "LCD":
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
# 最小圆查找

def find_min_circle(circles):
    min_size = 10000
    min_circle = None
    for circle in circles:
        if circle.r() < min_size:
            min_circle = circle
            min_size = circle.r()
    return min_circle
try:
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    if DISPLAY_MODE == "LCD":
        Display.init(Display.LT9611, width=640,  height=480, to_ide=True)
    sensor1 = Sensor(id=1)
    sensor1.reset()
    sensor1.set_framesize(width=320, height=160, chn=CAM_CHN_ID_1)
    sensor1.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_1)
    sensor1.set_hmirror(False)
    sensor1.set_vflip(False)
    MediaManager.init()

    sensor1.run()


    clock = time.clock()

    while True:
        clock.tick()
        os.exitpoint()
        img1 = sensor1.snapshot(chn=CAM_CHN_ID_1)

        Display.show_image(img1, x=int((DISPLAY_WIDTH - 320) / 2), y=int((DISPLAY_HEIGHT - 160) / 2))
        time.sleep(0.1)
except KeyboardInterrupt:
    print("用户终止")
finally:
    Display.deinit()
