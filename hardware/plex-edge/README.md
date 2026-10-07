# PLEX Edge 智能学习终端

PLEX Edge 是 PLEX Universe 的课堂与自习空间硬件扩展方案，用于签到、任务提醒、理解度反馈和匿名求助。首版坚持低隐私设计：默认不配摄像头和麦克风，不在设备长期保存个人身份或学习明细。

## 当前状态

这是可评审的工程设计候选版，包含物料清单、接线表、接口协议、固件骨架和验证计划。截至 2026-08-31，尚未完成 PCB、机壳、实物打样、EMC/电气安全或连续运行测试，不得描述为“已完成硬件产品”。

## 主要能力

- NFC 或课程二维码绑定当次课堂会话。
- 四个实体按键上报“理解”“需要帮助”“任务完成”“匿名求助”。
- 屏幕显示今日委托、课堂倒计时和教师广播。
- RGB 状态灯提示联网、待办和故障状态。
- Wi-Fi + HTTPS 与 PLEX 后端交互。
- 设备注册、令牌轮换、固件版本和在线状态管理。

## 目录

```text
plex-edge/
├── README.md
├── STATUS.md
├── docs/
│   ├── BOM.csv
│   ├── 系统设计.md
│   ├── 接口协议.md
│   ├── 接线表.csv
│   └── 测试与安全清单.md
└── firmware/
    ├── platformio.ini
    ├── include/secrets.example.h
    └── src/main.cpp
```

## 构建固件

1. 安装 VS Code 与 PlatformIO。
2. 复制 `firmware/include/secrets.example.h` 为 `secrets.h`。
3. 填写测试 Wi-Fi、设备编号、后端地址和测试令牌。
4. 在 `firmware/` 中执行 `pio run`。

真实项目应通过设备注册接口领取短期凭证，不能把生产密码或长期令牌写入固件。

