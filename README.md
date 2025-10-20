实际上就是清屏+重新显示
我们一般会使用按键来控制oled的菜单切换。
一：按键

键盘扫描原理
为了检测哪个按键被按下，通常采用行列式的扫描方法。在这种方法中，首先会遍历每一行，将每一行都设为低电平。然后所有的列线会被逐一设置为高电平，而其余未选中的列则保持低电平。随后，程序会读取各条行线的状态。如果某一行线处于高电平，则说明该行与此刻激活的列线之间存在闭合电路，从而可以推断出具体的按键位置。
2.行列的作用以及关系
行线的主要内容是向列线发送扫描信号。 3。代码示例 按键扫描： void KeyScan(void) {
uint8_t row, col;

for (row = 0; row < ROW_COUNT; row++) { // 遍历每行
SetRow(row); // 设置当前行为低电平

 for (col = 0; col < COL_COUNT; col++) { // 检查每列
     if (!ReadCol(col)) {               // 如果列被拉低
         HandleKeyPress(row, col);      // 处理按键事件
     }
 }
 
 ResetRows();                          // 还原所有行为高电平
}
}`
按键消抖：
#define DEBOUNCE_DELAY_MS 20 // 定义去抖延迟时间(毫秒)

static bool IsDebounced(uint8_t keyState) {
static uint8_t debounceCounter = 0;

if (keyState != previousKeyState) {       // 发生了状态切换
    debounceCounter++;
    if (debounceCounter >= MAX_DEBOUNCE_COUNT) { // 达到最大尝试次数
        previousKeyState = keyState;             // 更新稳定后的状态
        return true;
    } else {
        Delay(DEBOUNCE_DELAY_MS);
        return false;
    }
}
//疑问：
如果把行和列的操作换过来，能否识别出按下的是那个按钮？
二.OLED
内容：
1.菜单个数
2.滚动条长度（就是比如如果选用16的字体的话，一页最多显示四行，这样长度0，因为不需要滚动，如果需要显示大于4行，比如5行，这样菜单就需要滚动一下才能看到下面的一行，这样滚动条长度就是1了。）
3.菜单的名称等
4.菜单的功能函数
5.父级菜单
6.子菜单

