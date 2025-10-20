#version_1

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

# 串口配置
uart = UART(UART.UART3, baudrate=115200, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)
# 按钮配置
button = Pin(53, Pin.IN, Pin.PULL_DOWN)  # 使用下拉电阻
button_last_state = 0  # 上次按键状态

# 定义全局变量
img0 = None  # 图像变量
img1 = None

# 形状识别相关全局变量
solidity_sum = 0
density_sum = 0
roundness_sum = 0
count = 0
avg_solidity = 0
avg_density = 0
avg_roundness = 0


# 定义传感器变量
sensor0 = None
sensor1 = None
# 显示模式选择
DISPLAY_MODE = "LCD"

picture_width = 800
picture_height = 480

if DISPLAY_MODE == "LCD":
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480

# 阈值调整相关全局变量
# 按钮文本
textL = ["back", "LL-", "LH-", "AL-", "AH-", "BL-", "BH-", "prev"]
textR = ["next", "LL+", "LH+", "AL+", "AH+", "BL+", "BH+", "save"]
isLabFlag = True  # 是否是LAB
isInvertFlag = False  # 是否反转
#串口相关全局变量
uart_flag = b'' #全局变量uart_flag
new_command_received = False  # 用于标记是否收到新指令
# 虚拟按钮范围，用于触摸点判断
buttonsL = [
    (0, 5, 100, 50),  # 按钮"back"
    (0, 65, 100, 50),  # 按钮"LL-"
    (0, 125, 100, 50),  # 按钮"LH-"
    (0, 185, 100, 50),  # 按钮"AL-"
    (0, 245, 100, 50),  # 按钮"AH-"
    (0, 305, 100, 50),  # 按钮"BL-"
    (0, 365, 100, 50),  # 按钮"BH-"
    (0, 425, 100, 50)  # 按钮"prev"（切换到上一个颜色）
]
buttonsR = [
    (700, 5, 100, 50),  # 按钮"next"（切换到下一个颜色）
    (700, 65, 100, 50),  # 按钮"LL+"（与左侧"LL-"对称）
    (700, 125, 100, 50),  # 按钮"LH+"（与左侧"LH-"对称）
    (700, 185, 100, 50),  # 按钮"AL+"（与左侧"AL-"对称）
    (700, 245, 100, 50),  # 按钮"AH+"（与左侧"AH-"对称）
    (700, 305, 100, 50),  # 按钮"BL+"（与左侧"BL-"对称）
    (700, 365, 100, 50),  # 按钮"BH+"（与左侧"BH-"对称）
    (700, 425, 100, 50)  # 按钮"save"（保存阈值）
]
buttonsS = [
    (390, 5, 100, 50)
]

# 标准LAB范围初始化
L_MIN, L_MAX = 0, 52  # L亮度范围0-100
A_MIN, A_MAX = 31, 90  # a轴范围-128~127
B_MIN, B_MAX = -38, 109  # b轴范围-128~127
GL, GH = 0, 255  # 灰度范围0~255
step = 1  # 脱机阈值步进
flag = False  # 页面标志，True表示阈值调整模式

LAB_thresholds = [(0, 52, 31, 90, -38, 109)]  # LAB阈值列表
Gray_thresholds = [(int(GL), int(GH))]  # 灰度阈值列表
debounce_delay = 20  # 毫秒
last_press_time = 0  # 上次按键按下的时间，单位为毫秒
timeTouch = 0
tp = TOUCH(0)

# 当前使用的阈值变量
yellow_threshold = (36, 100, -24, 1, 15, 64)  # 黄色阈值
gray_threshold = (11, 65, -16, 15, -28, 26)  # 灰色阈值
white_threshold = (89, 100, -13, 10, -14, 16)  # 白色阈值
red_threshold = (40, 8, 8, 50, 11, 42)  # 红色阈值
green_threshold = (76, 21, -46, -21, 12, 40)  # 绿色阈值
blue_threshold = (0, 50, -20, 20, -60, -10)  # 蓝色阈值

# 添加颜色选择变量和颜色列表
current_color_index = 0
color_names = ["red", "green", "blue", "yellow", "gray", "white"]
color_thresholds = [
    red_threshold,
    green_threshold,
    blue_threshold,
    yellow_threshold,
    gray_threshold,
    white_threshold
]
current_color = color_names[current_color_index]
save_success_message = ""  # 保存成功提示消息
save_message_timer = 0  # 保存消息显示计时器

# 阈值文件路径
THRESHOLDS_FILE = "/sdcard/color_thresholds.json"

# 文件操作函数
# 保存所有颜色阈值到文件
def save_thresholds_to_sd():
    global save_success_message, save_message_timer, red_threshold, green_threshold, blue_threshold, yellow_threshold, gray_threshold, white_threshold, color_thresholds
    try:
        # 首先确保全局阈值变量与color_thresholds数组同步
        red_threshold = color_thresholds[0]
        green_threshold = color_thresholds[1]
        blue_threshold = color_thresholds[2]
        yellow_threshold = color_thresholds[3]
        gray_threshold = color_thresholds[4]
        white_threshold = color_thresholds[5]

        # 准备保存的数据
        thresholds_data = {
            "red": red_threshold,
            "green": green_threshold,
            "blue": blue_threshold,
            "yellow": yellow_threshold,
            "gray": gray_threshold,
            "white": white_threshold
        }

        # 打开文件并写入数据
        with open(THRESHOLDS_FILE, 'w') as f:
            json.dump(thresholds_data, f)

        # 设置保存成功消息
        save_success_message = "保存成功!"
        save_message_timer = 100
        print(f"阈值已保存: {thresholds_data}")  # 调试信息
    except Exception as e:
        save_success_message = f"保存失败: {str(e)}"
        save_message_timer = 300
        print(f"保存错误: {str(e)}")

# 从文件加载颜色阈值

def load_thresholds_from_sd():
    global red_threshold, green_threshold, blue_threshold, yellow_threshold, gray_threshold, white_threshold, color_thresholds, L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX
    try:

        try:
            with open(THRESHOLDS_FILE, 'r') as f:
                thresholds_data = json.load(f)
        except OSError:
            print("阈值文件不存在")
            return False

        # 更新各个颜色阈值
        red_threshold = tuple(thresholds_data.get("red", red_threshold))
        green_threshold = tuple(thresholds_data.get("green", green_threshold))
        blue_threshold = tuple(thresholds_data.get("blue", blue_threshold))
        yellow_threshold = tuple(thresholds_data.get("yellow", yellow_threshold))
        gray_threshold = tuple(thresholds_data.get("gray", gray_threshold))
        white_threshold = tuple(thresholds_data.get("white", white_threshold))

        # 更新阈值列表
        color_thresholds = [
            red_threshold,
            green_threshold,
            blue_threshold,
            yellow_threshold,
            gray_threshold,
            white_threshold
        ]

        # 更新当前选择颜色的LAB值
        if current_color_index < len(color_thresholds):
            L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX = color_thresholds[current_color_index]

        print(f"阈值已加载: {thresholds_data}")  # 调试信息
        return True
    except Exception as e:
        print(f"加载阈值失败: {str(e)}")
        return False
"""
                坐标拆分函数（高低字节）

"""
def split_coordinates(value):
    """
    将一个16位数值拆分为高字节和低字节
    value: 要拆分的16位整数值
    return: (high_byte, low_byte) 元组
    """
    high_byte = (value >> 8) & 0xFF  # 右移8位获取高字节
    low_byte = value & 0xFF          # 与0xFF按位与获取低字节
    return high_byte, low_byte
    """
                    任务循环退出函数（通过给他发送下一个任务的指令让他退出当前的任务循环）

    """
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
"""
                    找最大色块函数

"""
def find_max(blobs):
    max_blob = None
    max_size = 0
    for blob in blobs:
        if blob[2] * blob[3] > max_size:
            max_blob = blob
            max_size = blob[2] * blob[3]
    return max_blob
"""
                    识别圆环函数（反恐区）
"""
def find_min_circle(circles):
    min_size = 10000
    min_circle = None
    for circle in circles:
        if circle.r() < min_size:
            min_circle = circle
            min_size = circle.r()
    return min_circle
"""
                    形状识别
"""
def detect(max_blob):  # 输入的是寻找到色块中的最大色块
    global solidity_sum, density_sum, roundness_sum, count, avg_solidity, avg_density, avg_roundness
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
            img0.draw_rectangle(max_blob.rect(), color=(255, 0, 0))
            row_data[1] = 1  # 表示矩形

        elif avg_solidity > 0.8 and avg_density > 0.76 and (avg_roundness < 0.35 and avg_roundness > 0.26):
            row_data[0] = max_blob.code()
            img0.draw_rectangle(max_blob.rect(), color=(0, 255, 0))
            row_data[1] = 2  # 表示梯形

        elif avg_solidity > 0.75 and avg_density > 0.73 and avg_roundness > 0.4:
            row_data[0] = max_blob.code()
            img0.draw_rectangle(max_blob.rect(), color=(0, 0, 255))
            row_data[1] = 3  # 表示圆鼓

        return row_data  # 返回的是两个值，颜色和形状
    return None  # 如果还没有累加够50次，返回None

#人质色块寻找函数
def find_max_hostage(blobs):
    max_blob = None
    max_size = 0
    for blob in blobs:
        if blob.w() * blob.h() > max_size:
            max_blob = blob
            max_size = blob.w() * blob.h()

    return max_blob

# 脱机调整阈值界面设计
def changeScreen(img):
    global save_message_timer
    img = img0.copy()
    screen = img0.copy()

    # 绘制白色背景、阈值画面范围及原始画面
    screen.draw_rectangle(0, 0, 800, 480, (255, 255, 255), fill=True)
    screen.draw_rectangle(200, 170, 400, 240, (0, 0, 0), 2)
    screen.draw_image(img0, 120, 5, x_size=266, y_size=160)

    # 获取画面
    LabImg = img0.binary(LAB_thresholds)
    GrayImg = img0.to_grayscale().binary(Gray_thresholds)

    # 是否反转
    if isInvertFlag:
        LabImg = LabImg.invert()
        GrayImg = GrayImg.invert()

    # 是LAB或Gray，绘制相关阈值数值
    if isLabFlag:
        screen.draw_image(LabImg, 200, 180, x_size=400, y_size=240)
        screen.draw_string_advanced(150, 420, 30, f"L: [{L_MIN}  {L_MAX}]", color=(0, 0, 0))
        screen.draw_string_advanced(300, 420, 30, f"A: [{A_MIN}  {A_MAX}]", color=(0, 0, 0))
        screen.draw_string_advanced(500, 420, 30, f"B: [{B_MIN}  {B_MAX}]", color=(0, 0, 0))
    else:
        screen.draw_image(GrayImg, 200, 180, x_size=400, y_size=240)
        screen.draw_string_advanced(150, 420, 30, f"Gray: [{GL}  {GH}]", color=(0, 0, 0))

    # 绘制虚拟按钮，编写文本
    for i in range(8):
        screen.draw_rectangle(0, 5 + i * 60, 100, 50, (200, 201, 202), thickness=1, fill=True)
        screen.draw_string_advanced(30, 20 + i * 60, 20, textL[i], (0, 0, 0))
        screen.draw_rectangle(700, 5 + i * 60, 100, 50, (200, 201, 202), thickness=1, fill=True)
        screen.draw_string_advanced(730, 20 + i * 60, 20, textR[i], (0, 0, 0))
    screen.draw_rectangle(390, 5, 100, 50, (200, 201, 202), thickness=1, fill=True)
    screen.draw_string_advanced(400, 20, 20, f"step: {step}", (0, 0, 0))

    # 显示当前选择的颜色
    screen.draw_string_advanced(350, 80, 30, f"Current Color: {current_color}", color=(0, 0, 0))

    # 显示保存消息
    if save_message_timer > 0:
        screen.draw_rectangle(300, 120, 200, 40, (0, 255, 0), fill=True)
        screen.draw_string_advanced(320, 130, 20, save_success_message, (0, 0, 0))
        save_message_timer -= 1

    Display.show_image(screen if flag else img)

# 触摸屏按钮事件动作
def buttonAction(direction, index):
    global L_MAX, L_MIN, A_MAX, A_MIN, B_MAX, B_MIN, flag, step
    global isLabFlag, textR, GL, GH, LAB_thresholds, isInvertFlag, Gray_thresholds
    global white_threshold, yellow_threshold, gray_threshold, red_threshold, green_threshold, blue_threshold
    global current_color_index, current_color, color_thresholds

    # 阈值列表重置
    LAB_thresholds = [(int(L_MIN), int(L_MAX), int(A_MIN), int(A_MAX), int(B_MIN), int(B_MAX))]
    Gray_thresholds = [(int(GL), int(GH))]

    # 按钮处理
    if direction == 'left':  # 减操作
        if index == 1:
            if isLabFlag:
                L_MIN = max(L_MIN - step, 0)  # 确保L_MIN >= 0
            else:
                GL = max(GL - step, 0)
        elif index == 2:
            if isLabFlag:
                L_MAX = max(L_MAX - step, 0)
            else:
                GH = max(GH - step, 0)
        elif index == 3:
            A_MIN = max(A_MIN - step, -128)
        elif index == 4:
            A_MAX = max(A_MAX - step, -128)
        elif index == 5:
            B_MIN = max(B_MIN - step, -128)
        elif index == 6:
            B_MAX = max(B_MAX - step, -128)
        elif index == 0:
            flag = False
        elif index == 7:  # 使用prev按钮切换到上一个颜色
            current_color_index = (current_color_index - 1) % len(color_names)
            current_color = color_names[current_color_index]
            # 加载对应颜色的阈值
            L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX = color_thresholds[current_color_index]
    elif direction == 'right':  # 加操作
        if index == 1:
            if isLabFlag:
                L_MIN = min(L_MIN + step, 100)  # 确保L_MIN <= 100
            else:
                GL = min(GL + step, 255)

        elif index == 2:
            if isLabFlag:
                L_MAX = min(L_MAX + step, 100)
            else:
                GH = min(GH + step, 255)
        elif index == 3:
            A_MIN = min(A_MIN + step, 127)
        elif index == 4:
            A_MAX = min(A_MAX + step, 127)
        elif index == 5:
            B_MIN = min(B_MIN + step, 127)
        elif index == 6:
            B_MAX = min(B_MAX + step, 127)
        elif index == 0:  # 使用next按钮切换到下一个颜色
            current_color_index = (current_color_index + 1) % len(color_names)
            current_color = color_names[current_color_index]
            # 加载对应颜色的阈值
            L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX = color_thresholds[current_color_index]
        elif index == 7:  # 使用save按钮保存所有阈值
            save_thresholds_to_sd()
    elif direction == 'step':  # 调整步进
        step += 1
        if step > 5:
            step = 1

# 触摸屏事件
def touchAction():
    global timeTouch
    touchP = tp.read(2)

    # 每3次计为1次，减少sleep时间，确保摄像头画面流畅
    if touchP:
        timeTouch += 1
        if timeTouch >= 3:
            p = touchP
            timeTouch = 0
            if p:
                x, y = p[0].x, p[0].y
                # 通过触摸坐标与按钮覆盖位置确定触摸按钮
                if x < 200:
                    for i, (rect_x, rect_y, rect_w, rect_h) in enumerate(buttonsL):
                        if (rect_x <= x <= rect_x + rect_w) and (rect_y <= y <= rect_y + rect_h):
                            print(f"操作: {textL[i]}")
                            buttonAction('left', i)
                elif x > 600:
                    for i, (rect_x, rect_y, rect_w, rect_h) in enumerate(buttonsR):
                        if (rect_x <= x <= rect_x + rect_w) and (rect_y <= y <= rect_y + rect_h):
                            print(f"操作: {textR[i]}")
                            buttonAction('right', i)
                else:
                    for i, (rect_x, rect_y, rect_w, rect_h) in enumerate(buttonsS):
                        if (rect_x <= x <= rect_x + rect_w) and (rect_y <= y <= rect_y + rect_h):
                            print(f"操作: step")
                            buttonAction('step', 1)
    time.sleep(0.01)

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
    sensor1 = Sensor(id=1)
    sensor1.reset()
    sensor1.set_framesize(width=800,  height=480, chn=CAM_CHN_ID_1)
    sensor1.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_1)
    sensor1.set_hmirror(False)
    sensor1.set_vflip(False)
    if DISPLAY_MODE == "LCD":
        Display.init(Display.ST7701, width=800, height=480, to_ide=True)


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

        img0 = sensor0.snapshot(chn=CAM_CHN_ID_0)


        # 检测按键状态用于切换阈值调整模式
        button_state = button.value()  # 获取当前按键状态
        current_time = time.ticks_ms()  # 获取当前时间（单位：毫秒）

        # 检测按键从未按下(0)到按下(1)的变化（上升沿）
        if button_state == 1 and button_last_state == 0:
            # 检查按键是否在消抖时间外
            if current_time - last_press_time > debounce_delay:
                if button.value() == 1:
                    if not flag:
                        # 进入阈值调整模式时，加载当前选择颜色的阈值
                        L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX = color_thresholds[current_color_index]
                    flag = not flag
                last_press_time = current_time  # 更新按键按下时间
        # 更新上次按键状态
        button_last_state = button_state

        # 如果处于阈值调整模式，显示阈值调整界面并处理触摸事件
        if flag:
            changeScreen(img0)
            touchAction()
            # 实时更新当前颜色的阈值
            if current_color == "red":
                red_threshold = (L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)
                color_thresholds[0] = red_threshold
            elif current_color == "green":
                green_threshold = (L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)
                color_thresholds[1] = green_threshold
            elif current_color == "blue":
                blue_threshold = (L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)
                color_thresholds[2] = blue_threshold
            elif current_color == "yellow":
                yellow_threshold = (L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)
                color_thresholds[3] = yellow_threshold
            elif current_color == "gray":
                gray_threshold = (L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)
                color_thresholds[4] = gray_threshold
            elif current_color == "white":
                white_threshold = (L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)
                color_thresholds[5] = white_threshold
            continue

        # 姿态调整 - 颜色触发模式

        img1 = sensor1.snapshot(chn=CAM_CHN_ID_1)
        blobs_yellow = img1.find_blobs([yellow_threshold])
        blobs_gray = img1.find_blobs([gray_threshold])

        if blobs_yellow and blobs_gray:
            max_blob_yellow = find_max(blobs_yellow)  # 返回最大的色块
            max_blob_gray = find_max(blobs_gray)  # 返回最大的色块

            # 当两个色块都足够大时触发姿态调整
            if max_blob_yellow and max_blob_gray and max_blob_yellow.pixels() > 10000 and max_blob_gray.pixels() > 10000:
                img1.draw_cross(max_blob_yellow.cx(), max_blob_yellow.cy(), color=(255, 255, 0), size=20)
                img1.draw_cross(max_blob_gray.cx(), max_blob_gray.cy(), color=(128, 128, 128), size=20)

                My = (max_blob_yellow.cy() + max_blob_gray.cy()) // 2
                high_byte_y, low_byte_y = split_coordinates(My)

                # 发送姿态调整指令 通过调节4这个数字可以控制精度）
                if abs(My - 240) < 4: #调整到位
                    img1.draw_line(max_blob_yellow.cx(), max_blob_yellow.cy(),
                                  max_blob_gray.cx(), max_blob_gray.cy(), color=(0, 255, 0))
                    MA = bytearray([0x05, high_byte_y, low_byte_y, 0x00, 0x00, 0x00, 0x00, 0x6B])
                    uart.write(MA)
                else:#调整不到位
                    img1.draw_line(max_blob_yellow.cx(), max_blob_yellow.cy(),
                                  max_blob_gray.cx(), max_blob_gray.cy(), color=(255, 0, 0))
                    MA = bytearray([0x05, high_byte_y, low_byte_y, 0x01, 0x00, 0x00, 0x00, 0x6B])
                    uart.write(MA)

        # 串口数据接收处理
        uart_flag = b''  # 默认无指令
        if uart.any():
            list_flag = uart.read()
            if list_flag is None:
                continue
            uart_flag = list_flag
            print(f"接收到数据: {uart_flag}")
        # 遍历捕获到的所有条形码
        if uart_flag == b'\x01\x00\x00\x00\x00\x00\x00\x00':  # 扫码
            while True:
                img0 = sensor0.snapshot(chn=CAM_CHN_ID_0)
                if check_for_new_command():
                    break
                for code in img0.find_qrcodes():

                    # 在图像上绘制条形码矩形框
                    rect = code.rect()
                    img0.draw_rectangle([v for v in rect], color=(255, 0, 0), thickness = 5)
                    # 打印条形码信息
                    img0.draw_string_advanced(rect[0], rect[1], 32, code.payload())
                    print(code[4][0],code[4][1],code[4][2])

                    MA = bytearray([0x01, int(code[4][0]), int(code[4][1]), int(code[4][2]), 0x00, 0x00, 0x00, 0x6B])
                    uart.write(MA)
                Display.show_image(img0, x=int((DISPLAY_WIDTH - picture_width) / 2), y=int((DISPLAY_HEIGHT - picture_height) / 2))

        # 排爆区
        elif (uart_flag == b'\x02\x01\x00\x00\x00\x00\x00\x00') or (uart_flag == b'\x02\x02\x00\x00\x00\x00\x00\x00') or (uart_flag == b'\x02\x03\x00\x00\x00\x00\x00\x00') or (uart_flag == b'\x02\x04\x00\x00\x00\x00\x00\x00'):

            if uart_flag == b'\x02\x01\x00\x00\x00\x00\x00\x00':  ##识别三个颜色与排爆桶
                img0 = sensor0.snapshot(chn=CAM_CHN_ID_0)
                if check_for_new_command():
                    break
                blobs = img0.find_blobs([red_threshold])  # 红
                if blobs:
                    max_blob = find_max(blobs)  # 返回最大的色块
                    if max_blob.pixels() > 1000:
                        img0.draw_rectangle(max_blob.rect())
                        img0.draw_cross(max_blob.cx(), max_blob.cy())
                        center_x = max_blob.cx()
                        center_y = max_blob.cy()
                        # 使用独立函数拆分坐标为高低字节
                        high_byte_x, low_byte_x = split_coordinates(center_x)
                        high_byte_y, low_byte_y = split_coordinates(center_y)
                        MA = bytearray([0x02, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                        uart.write(MA)

                        Display.show_image(img0, x=int((DISPLAY_WIDTH - picture_width) / 2),
                                          y=int((DISPLAY_HEIGHT - picture_height) / 2))

            elif uart_flag == b'\x02\x02\x00\x00\x00\x00\x00\x00':
                img0 = sensor0.snapshot(chn=CAM_CHN_ID_0)
                if check_for_new_command():
                    break
                blobs = img0.find_blobs([green_threshold])  # 绿
                if blobs:
                    max_blob = find_max(blobs)
                    if max_blob.pixels() > 1000:
                        img0.draw_rectangle(max_blob.rect())
                        img0.draw_cross(max_blob.cx(), max_blob.cy())
                        center_x = max_blob.cx()
                        center_y = max_blob.cy()
                        # 使用独立函数拆分坐标为高低字节
                        high_byte_x, low_byte_x = split_coordinates(center_x)
                        high_byte_y, low_byte_y = split_coordinates(center_y)
                        MA = bytearray([0x02, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                        uart.write(MA)

                        Display.show_image(img0, x=int((DISPLAY_WIDTH - picture_width) / 2),
                                          y=int((DISPLAY_HEIGHT - picture_height) / 2))

            elif uart_flag == b'\x02\x03\x00\x00\x00\x00\x00\x00':
                img0 = sensor0.snapshot(chn=CAM_CHN_ID_0)
                if check_for_new_command():
                    break
                blobs = img0.find_blobs([blue_threshold])  # 蓝
                if blobs:
                    max_blob = find_max(blobs)
                    if max_blob.pixels() > 1000:
                        img0.draw_rectangle(max_blob.rect())
                        img0.draw_cross(max_blob.cx(), max_blob.cy())
                        center_x = max_blob.cx()
                        center_y = max_blob.cy()
                        # 使用独立函数拆分坐标为高低字节
                        high_byte_x, low_byte_x = split_coordinates(center_x)
                        high_byte_y, low_byte_y = split_coordinates(center_y)
                        MA = bytearray([0x02, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                        uart.write(MA)

                        Display.show_image(img0, x=int((DISPLAY_WIDTH - picture_width) / 2),
                                          y=int((DISPLAY_HEIGHT - picture_height) / 2))
            elif uart_flag == b'\x02\x04\x00\x00\x00\x00\x00\x00':
                img0 = sensor0.snapshot(chn=CAM_CHN_ID_0)
                if check_for_new_command():
                    break
                blobs = img0.find_blobs([0, 0, 0, 30, 0, 50])  # 黑色防爆桶
                if blobs:
                    max_blob = find_max(blobs)
                    if max_blob.pixels() > 1000:
                        img0.draw_rectangle(max_blob.rect())
                        img0.draw_cross(max_blob.cx(), max_blob.cy())
                        center_x = max_blob.cx()
                        center_y = max_blob.cy()
                        # 使用独立函数拆分坐标为高低字节
                        high_byte_x, low_byte_x = split_coordinates(center_x)
                        high_byte_y, low_byte_y = split_coordinates(center_y)
                        MA = bytearray([0x02, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                        uart.write(MA)

                        Display.show_image(img0, x=int((DISPLAY_WIDTH - picture_width) / 2),
                                            y=int((DISPLAY_HEIGHT - picture_height) / 2))

        # 反恐区
        elif (uart_flag == b'\x03\x01\x00\x00\x00\x00\x00\x00') or (uart_flag == b'\x03\x02\x00\x00\x00\x00\x00\x00') or (uart_flag == b'\x03\x03\x00\x00\x00\x00\x00\x00'):
            # 红色靶子
            if uart_flag == b'\x03\x01\x00\x00\x00\x00\x00\x00':
                img1 = sensor1.snapshot(chn=CAM_CHN_ID_1)
                if check_for_new_command():
                    break
                img1 = img1.binary([(red_threshold)]).gaussian(3)

                circles = img1.find_circles(threshold=5000, x_margin=20, y_margin=20, r_margin=20,
                                           r_min=20, r_max=50, r_step=2)
                if circles:
                    min_circle = find_min_circle(circles)  # 找到最小的圆
                    img1.draw_circle(min_circle.x() - min_circle.r() + min_circle.r(),
                                    min_circle.y() - min_circle.r() + min_circle.r(), min_circle.r(), color=(250, 0, 0))
                    img1.draw_cross(min_circle.x(), min_circle.y(), color=(250, 0, 0))
                    center_x = min_circle.x()
                    center_y = min_circle.y()
                    print(min_circle.r())
                    # 使用独立函数拆分坐标为高低字节
                    high_byte_x, low_byte_x = split_coordinates(center_x)
                    high_byte_y, low_byte_y = split_coordinates(center_y)
                    MA = bytearray([0x03, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                    uart.write(MA)

                # 显示捕获的图像，中心对齐，居中显示
                Display.show_image(img1, x=int((DISPLAY_WIDTH - picture_width) / 2),
                                   y=int((DISPLAY_HEIGHT - picture_height) / 2))

            # 绿色靶子
            elif uart_flag == b'\x03\x02\x00\x00\x00\x00\x00\x00':
                img1 = sensor1.snapshot(chn=CAM_CHN_ID_1)
                if check_for_new_command():
                    break
                img1 = img1.binary([(green_threshold)]).gaussian(3)

                circles = img1.find_circles(threshold=5000, x_margin=20, y_margin=20, r_margin=20,
                                           r_min=20, r_max=50, r_step=2)

                if circles:
                    min_circle = find_min_circle(circles)  # 找到最小的圆
                    img1.draw_circle(min_circle.x() - min_circle.r() + min_circle.r(),
                                    min_circle.y() - min_circle.r() + min_circle.r(), min_circle.r(), color=(250, 0, 0))
                    img1.draw_cross(min_circle.x(), min_circle.y(), color=(250, 0, 0))
                    center_x = min_circle.x()
                    center_y = min_circle.y()
                    print(min_circle.r())
                    # 使用独立函数拆分坐标为高低字节
                    high_byte_x, low_byte_x = split_coordinates(center_x)
                    high_byte_y, low_byte_y = split_coordinates(center_y)
                    MA = bytearray([0x03, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                    uart.write(MA)

                # 显示捕获的图像，中心对齐，居中显示
                Display.show_image(img1, x=int((DISPLAY_WIDTH - picture_width) / 2),
                                   y=int((DISPLAY_HEIGHT - picture_height) / 2))
            # 蓝色靶子
            elif uart_flag == b'\x03\x03\x00\x00\x00\x00\x00\x00':
                img1 = sensor1.snapshot(chn=CAM_CHN_ID_1)
                if check_for_new_command():
                    break
                img1 = img1.binary([(blue_threshold)]).gaussian(3)

                circles = img1.find_circles(threshold=5000, x_margin=20, y_margin=20, r_margin=20,
                                           r_min=20, r_max=50, r_step=2)

                if circles:
                    min_circle = find_min_circle(circles)  # 找到最小的圆
                    img1.draw_circle(min_circle.x() - min_circle.r() + min_circle.r(),
                                    min_circle.y() - min_circle.r() + min_circle.r(), min_circle.r(), color=(250, 0, 0))
                    img1.draw_cross(min_circle.x(), min_circle.y(), color=(250, 0, 0))
                    center_x = min_circle.x()
                    center_y = min_circle.y()
                    print(min_circle.r())
                    # 使用独立函数拆分坐标为高低字节
                    high_byte_x, low_byte_x = split_coordinates(center_x)
                    high_byte_y, low_byte_y = split_coordinates(center_y)
                    MA = bytearray([0x03, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                    uart.write(MA)
                # 显示捕获的图像，中心对齐，居中显示
                Display.show_image(img1, x=int((DISPLAY_WIDTH - picture_width) / 2),
                                   y=int((DISPLAY_HEIGHT - picture_height) / 2))

        # 救援区
        elif (uart_flag == b'\x04\x01\x00\x00\x00\x00\x00\x00') or (uart_flag == b'\x04\x02\x00\x00\x00\x00\x00\x00') or (
                    uart_flag == b'\x04\x03\x00\x00\x00\x00\x00\x00'):  ##识别三个形状
            if uart_flag == b'\x04\x01\x00\x00\x00\x00\x00\x00':
                solidity_sum = 0
                density_sum = 0
                roundness_sum = 0
                count = 0
                avg_solidity = 0
                avg_density = 0
                avg_roundness = 0

                while True:
                    img0 = sensor0.snapshot()
                    if check_for_new_command():
                        break
                    blobs = img0.find_blobs([white_threshold])
                    # 显示当前累加计数
                    img0.draw_string_advanced(5, 5, "Count: {}/50".format(count), color=(255, 0, 0))

                    if blobs:
                        max_blob = find_max_hostage(blobs)
                        center_x = max_blob.cx()
                        center_y = max_blob.cy()
                        # 使用独立函数拆分坐标为高低字节
                        high_byte_x, low_byte_x = split_coordinates(center_x)
                        high_byte_y, low_byte_y = split_coordinates(center_y)
                        # 返回最大的色块
                        result = detect(max_blob)
                        if result:
                            print(result[1])
                            if result[1] == 1:  # 矩形
                                MA = bytearray([0x04, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                                uart.write(MA)
            elif uart_flag == b'\x04\x02\x00\x00\x00\x00\x00\x00':
                solidity_sum = 0
                density_sum = 0
                roundness_sum = 0
                count = 0
                avg_solidity = 0
                avg_density = 0
                avg_roundness = 0

                while True:
                    img0 = sensor0.snapshot()
                    if check_for_new_command():
                        break
                    blobs = img0.find_blobs([white_threshold])
                    # 显示当前累加计数
                    img0.draw_string_advanced(5, 5, "Count: {}/50".format(count), color=(255, 0, 0))

                    if blobs:
                        max_blob = find_max_hostage(blobs)
                        center_x = max_blob.cx()
                        center_y = max_blob.cy()
                        # 使用独立函数拆分坐标为高低字节
                        high_byte_x, low_byte_x = split_coordinates(center_x)
                        high_byte_y, low_byte_y = split_coordinates(center_y)
                        # 返回最大的色块
                        result = detect(max_blob)
                        if result:
                            print(result[1])
                            if result[1] == 2:  # 梯形
                                MA = bytearray(
                                    [0x04, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                                uart.write(MA)
            elif uart_flag == b'\x04\x03\x00\x00\x00\x00\x00\x00':
                solidity_sum = 0
                density_sum = 0
                roundness_sum = 0
                count = 0
                avg_solidity = 0
                avg_density = 0
                avg_roundness = 0

                while True:
                    img0 = sensor0.snapshot()
                    if check_for_new_command():
                        break
                    blobs = img0.find_blobs([white_threshold])
                    # 显示当前累加计数
                    img0.draw_string_advanced(5, 5, "Count: {}/50".format(count), color=(255, 0, 0))

                    if blobs:
                        max_blob = find_max_hostage(blobs)
                        center_x = max_blob.cx()
                        center_y = max_blob.cy()
                        # 使用独立函数拆分坐标为高低字节
                        high_byte_x, low_byte_x = split_coordinates(center_x)
                        high_byte_y, low_byte_y = split_coordinates(center_y)
                        # 返回最大的色块
                        result = detect(max_blob)
                        if result:
                            print(result[1])
                            if result[1] == 3:  # 腰鼓
                                MA = bytearray(
                                    [0x04, high_byte_x, low_byte_x, high_byte_y, low_byte_y, 0x00, 0x00, 0x6B])
                                uart.write(MA)

        # 显示捕获的图像，中心对齐，居中显示
        Display.show_image(img1 if 'img1' in locals() else img0, x=int((DISPLAY_WIDTH - picture_width) / 2), y=int((DISPLAY_HEIGHT - picture_height) / 2))
        # 短暂延时，避免cpu占用过高
        time.sleep_ms(100)

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
