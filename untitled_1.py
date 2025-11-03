import time, os, sys
from media.sensor import * #导入sensor模块，使用摄像头相关接口
from media.display import * #导入display模块，使用display相关接口
from media.media import * #导入media模块，使用meida相关接口
from machine import Pin


DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
DISPLAY_MODE = "LCD"
usr=Pin(53,Pin.IN,Pin.PULL_DOWN) #按键启动
photo_count = 301  # 全局照片计数器，起始编号改为301
try:
    # 显示初始化
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    if DISPLAY_MODE == "LCD":
        Display.init(Display.LT9611, width=800,  height=480, to_ide=True)

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


    # 创建一个FPS计时器，用于实时计算每秒帧数
    clock = time.clock()
    while True:
        clock.tick()
        os.exitpoint()

        img = sensor1.snapshot(chn=CAM_CHN_ID_1)
        Display.show_image(img, x=int((DISPLAY_WIDTH - 320) / 2), y=int((DISPLAY_HEIGHT - 160) / 2))
        if usr.value()==0:
            pass
        else:            # 每次按键拍10张，累计拍满150张
            if photo_count <= 450:
                for j in range(10):
                    if photo_count > 450:
                        break
                    img = sensor1.snapshot(chn=CAM_CHN_ID_1)
                    img.save(f'/sdcard/photo_{photo_count}.jpg')
                    print(f"保存第{photo_count}张照片到SD卡")
                    photo_count += 1
                    time.sleep(0.2)
                print(f"已完成第{photo_count-10}~{photo_count-1}张连拍")
                time.sleep(1)
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

