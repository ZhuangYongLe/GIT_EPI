#6
import time, os, sys, urandom, gc, math, json
from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH
from machine import Pin
from machine import FPIOA
from machine import UART
fpioa = FPIOA()
fpioa.set_function(50, FPIOA.UART3_TXD)
fpioa.set_function(51, FPIOA.UART3_RXD)
fpioa.set_function(53, FPIOA.GPIO53)

# 串口配置.
uart = UART(UART.UART3, baudrate=115200, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)
# 按钮配置
button = Pin(53, Pin.IN, Pin.PULL_DOWN)  # 使用下拉电阻
button_last_state = 0  # 上次按键状态

# 定义全局变量
img0 = None  # 图像变量
img1 = None

# 形状识别相关全局变量】
solidity_sum = 0
density_sum = 0
roundness_sum = 0
count = 0
avg_solidity = 0
avg_density = 0
avg_roundness = 0


# 定义传感器变量
sensor0 = None
sensor2 = None
# 显示模式选择
DISPLAY_MODE = "LCD"

picture_width = 800
picture_height = 480

if DISPLAY_MODE == "LCD":
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480


# 当前使用的阈值变量
yellow_threshold = (36, 100, -24, 1, 15, 64)  # 黄色阈值
gray_threshold = (11, 65, -16, 15, -28, 26)  # 灰色阈值
white_threshold = (89, 100, -13, 10, -14, 16)  # 白色阈值
red_threshold = (40, 8, 8, 50, 11, 42)  # 红色阈值
green_threshold = (76, 21, -46, -21, 12, 40)  # 绿色阈值
blue_threshold = (0, 50, -20, 20, -60, -10)  # 蓝色阈值


def find_max(blobs):
    max_blob = None
    max_size = 0
    for blob in blobs:
        # 兼容w()/h()和直接下标
        if hasattr(blob, 'w') and hasattr(blob, 'h'):
            size = blob.w() * blob.h()
        else:
            size = blob[2] * blob[3]
        if size > max_size:
            max_blob = blob
            max_size = size
    return max_blob


def detect(max_blob，img):  # 输入的是寻找到色块中的最大色块
    global solidity_sum, density_sum, roundness_sum, count, avg_solidity, avg_density, avg_roundness,img0
    # 累加solidity和density值
    solidity_sum += max_blob.solidity()
    density_sum += max_blob.density()
    roundness_sum += max_blob.roundness()
    count += 1
    # 如果累加次数达到50次，计算平均值
    if count >= 50:
        avg_solidity = solidity_sum / count
        avg_density = density_sum / count
        avg_roundness = roundness_sum / count
        # 重置累加器
        solidity_sum = 0
        density_sum = 0
        roundness_sum = 0
        count = 0
        row_data = [-1, -1]  # 保存颜色和形状
        # 使用平均值进行形状判断
        if avg_solidity > 0.91 and avg_density > 0.88 and (avg_roundness < 0.4 and avg_roundness > 0.31):
            row_data[0] = max_blob.code()
            if img is not None:
                img.draw_rectangle(max_blob.rect(), color=(255, 0, 0))
            row_data[1] = 1  # 表示矩形
        elif avg_solidity > 0.8 and avg_density > 0.76 and (avg_roundness < 0.35 and avg_roundness > 0.26):
            row_data[0] = max_blob.code()
            if img is not None:
                img.draw_rectangle(max_blob.rect(), color=(0, 255, 0))
            row_data[1] = 2  # 表示梯形
        elif avg_solidity > 0.75 and avg_density > 0.73 and avg_roundness > 0.4:
            row_data[0] = max_blob.code()
            if img is not None:
                img.draw_rectangle(max_blob.rect(), color=(0, 0, 255))
            row_data[1] = 3  # 表示圆鼓
        return row_data  # 返回的是两个值，颜色和形状
    return None  # 如果还没有累加够50次，返回None


def detect_center(img1, target_threshold):
    """检测图像中的圆心，返回圆心坐标或None"""
    mask = img1.binary([target_threshold])
    circles = mask.find_circles(threshold=6000, x_margin=10, y_margin=18, r_margin=10,
                                r_min=18, r_max=40, r_step=2)
    if circles:
        best_circle = min(circles, key=lambda c: c.r())
        img1.draw_circle(best_circle.x(), best_circle.y(), best_circle.r(), color=(255,0,0))
        img1.draw_cross(best_circle.x(), best_circle.y(), color=(255,0,0))
        return best_circle.x(), best_circle.y()
    return None

def split_coordinates(value):
    """将16位坐标值分割为高低字节"""
    high_byte = (value >> 8) & 0xFF
    low_byte = value & 0xFF
    return high_byte, low_byte

# 任务循环退出函数（通过给他发送下一个任务的指令让他退出当前的任务循环）

def check_for_new_command():
    """检查是否有新的串口指令"""
    global uart_flag, new_command_received
    if uart.any():
        new_command = uart.read()
        if new_command is not None:
            uart_flag = new_command
            new_command_received = True
            print(f"接收到新指令: {uart_flag}")
            return True
    return False

def process_blobs(img, threshold):
    """查找色块并处理，返回是否找到目标色块"""
    blobs = img.find_blobs([threshold])
    if blobs:
        max_blob = find_max(blobs)
        if max_blob.pixels() > 1000:
            img.draw_rectangle(max_blob.rect())
            img.draw_cross(max_blob.cx(), max_blob.cy())
            adjust_x = max_blob.cx()



            result = detect_center(img, threshold)
            if result:
                x, y = result
                print(f"圆心坐标: ({x}, {y})")

            return True
    return False

#人质色块寻找函数
def find_max_hostage(blobs):
    max_blob = None
    max_size = 0
    for blob in blobs:
        if hasattr(blob, 'w') and hasattr(blob, 'h'):
            size = blob.w() * blob.h()
        else:
            size = blob[2] * blob[3]
        if size > max_size:
            max_blob = blob
            max_size = size

    return max_blob
def detect(max_blob):#输入的是寻找到色块中的最大色块
    global solidity_sum, density_sum, roundness_sum, count, avg_solidity, avg_density,avg_roundness
    # 累加solidity和density值
    solidity_sum += max_blob.solidity()
    density_sum += max_blob.density()
    roundness_sum +=  max_blob.roundness()
    count += 1
    print("count:{}".format(count))
    # 如果累加次数达到50次，计算平均值
    if count >= 50:
        avg_solidity = solidity_sum / count
        avg_density = density_sum / count
        avg_roundness = roundness_sum / count
        print("avg_solidity:", avg_solidity)
        print("avg_density:", avg_density)
        print("avg_roundness:", avg_roundness)

        # 重置累加器
        solidity_sum = 0
        density_sum = 0
        roundness_sum = 0
        count = 0
        row_data = [-1, -1]  # 保存颜色和形状
        #使用平均值进行形状判断
        if avg_solidity > 0.91 and avg_density > 0.88 and (avg_roundness<0.4 and avg_roundness >0.31):
            row_data[0] = max_blob.code()
            # img.draw_rectangle(max_blob.rect(), color=(255, 0, 0))
            row_data[1] = 1  # 表示矩形
            #print("Average solidity:", avg_solidity, "Average density:", avg_density,"Average roundnes:", avg_roundness)
        elif avg_solidity > 0.8 and avg_density > 0.76 and (avg_roundness<0.35 and avg_roundness >0.26):
            row_data[0] = max_blob.code()
            # img.draw_rectangle(max_blob.rect(), color=(0, 255, 0))
            row_data[1] = 2  # 表示梯形
            #print("Average solidity:", avg_solidity, "Average density:", avg_density,"Average roundnes:", avg_roundness)
        elif avg_solidity > 0.75 and avg_density > 0.73  and avg_roundness > 0.4:
            row_data[0] = max_blob.code()
            # img.draw_rectangle(max_blob.rect(), color=(0, 0, 255))
            row_data[1] = 3  # 表示圆鼓
            #print("Average solidity:", avg_solidity, "Average density:", avg_density,"Average roundnes:", avg_roundness)
        return row_data  # 返回的是两个值，颜色和形状
    return None  # 如果还没有累加够50次，返回None
def find_max(blobs):
    max_blob = None
    max_size = 0
    for blob in blobs:
        if blob.w() * blob.h() > max_size:
            max_blob = blob
            max_size = blob.w() * blob.h()
    return max_blob
try:
    # 显示初始化
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    #定义id号
    sensor0 = Sensor(id=0)
    sensor0.reset()
    sensor0.set_framesize(width=800, height=480, chn=CAM_CHN_ID_0)
    sensor0.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)
    sensor0.set_hmirror(False)
    sensor0.set_vflip(False)

        # 重置摄像头sensor1并配置参数
    sensor2 = Sensor(id=2)
    sensor2.reset()
    sensor2.set_framesize(width=640,  height=480, chn=CAM_CHN_ID_1)
    sensor2.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_1)
    sensor2.set_hmirror(False)
    sensor2.set_vflip(False)
    if DISPLAY_MODE == "LCD":
        Display.init(Display.LT9611, width=640,  height=480, to_ide=True)


    # 初始化媒体管理器
    MediaManager.init()


        # 启动传感器
    sensor0.run()
    sensor2.run()

    clock = time.clock()
    while True:
        clock.tick()
        os.exitpoint()
        solidity_sum = 0
        density_sum = 0
        roundness_sum = 0
        count = 0
        avg_solidity = 0
        avg_density = 0
        avg_roundness = 0




        white_threshold = (89, 100, -13, 10, -14, 16) #修改阈值
        while True:
            img0 = sensor0.snapshot(chn=CAM_CHN_ID_0)
            blobs = img0.find_blobs([white_threshold])
            # 显示当前累加计数

            if blobs:
                max_blob = find_max_hostage(blobs)  # 返回最大的色块
                img0.draw_rectangle(max_blob.rect())
                print(1)
                img0.draw_cross(max_blob.cx(), max_blob.cy())
                result = detect(max_blob)
                if result:
                    print(result[1])
                    if result[1] == 1:#矩形
                        print("矩形")
            Display.show_image(img0)

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
