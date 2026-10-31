# Text-to-Speech → Virtual Microphone (Windows)

把任意文字变成语音，**只送进虚拟麦克风**，于是微信 / QQ / Discord / 腾讯会议里，对方听到的就是这段合成语音。
不占用你的真实麦克风，也不需要改系统默认设备。

> 场景举例：宿舍不方便开口说话时，打微信语音用打字代替发声。

## 工作原理

```
你的文字 ──edge-tts(微软在线神经语音)──▶ mp3
                                          │
                                    miniaudio 解码
                                          │
                          soundcard 定向播放到 "CABLE Input"
                                          │
                                VB-Audio Cable（虚拟声卡）
                                          │
              应用（微信/QQ/会议）把 "CABLE Output" 当麦克风 ◀──┘
```

关键点：**用 `soundcard` 定向播放到虚拟声卡**，所以不需要把系统默认播放设备改成 CABLE，换耳机/外放都不会影响。

## 依赖

| 组件 | 用途 | 安装 |
|---|---|---|
| **VB-Audio Virtual Cable** | 虚拟声卡（必需） | https://vb-audio.com/Cable/ 下载后右键 `VBCABLE_Setup_x64.exe` → 以管理员身份运行 → 重启 |
| Python 3.9+ | 运行脚本 | https://www.python.org/downloads/ |
| `edge-tts` | 微软神经语音合成（免费、需联网） | `pip install -r requirements.txt` |
| `miniaudio` `soundcard` `numpy` | 解码 / 定向播放 / 电平检测 | 同上 |

```bash
pip install -r requirements.txt
```

## 快速开始

```bash
# 1) 看看有哪些音频设备，确认能看到 CABLE In 16ch / CABLE Output
python speak-mic.py --list

# 2) 说一句（只进虚拟麦克风，自己听不到）
python speak-mic.py -t "你好，我在测试虚拟麦克风"

# 3) 同时自己也听一遍（播到默认扬声器）
python speak-mic.py -t "你好" --monitor

# 4) 端到端自测：播出去 + 从 CABLE Output 录回来，打印电平
python speak-mic.py -t "测试测试" --test

# 5) 读剪贴板里的文字
python speak-mic.py -c

# 6) 换音色 / 语速 / 音调
python speak-mic.py -t "换个声音" -v zh-CN-YunxiNeural -r +10% -p +0Hz

# 7) 同时播到多个设备（虚拟麦 + 耳机）
python speak-mic.py -t "同时输出" --monitor -a "你的耳机设备名"
```

> Windows 上如果 `python` 指向应用商店占位符，用 `py -3` 或写全路径。

## 图形界面

```bash
python speak-mic-ui.py
```

功能：多行输入、6 种中文神经音色、语速 −20%～+30%、勾选「同时播到耳机」、「从剪贴板粘贴」、「清空」、状态栏提示。
也可以直接双击 `tts-ui.bat`。

## 然后去应用里选麦克风

打开微信 / QQ / Discord → 设置 → 音视频 → **麦克风选 `CABLE Output (VB-Audio Virtual Cable)`**。
之后凡是跑这个脚本说的话，对方都能听到；你自己对着真实麦克风说话对方就听不到了（等于把"人声"让给了程序）。

想恢复：把麦克风改回你的真实麦克风即可。

## 常见问题

**Q: 报 `0x800401f0`（COM 未初始化）**
A: 在子线程里播放前必须 `CoInitializeEx`，本项目 `speak_mic_core.init_com()` 已处理；如果你自己写代码，记得调用它。

**Q: 播放没声音 / 对方听不到**
1. `python speak-mic.py --list` 确认有 `CABLE In 16ch`（播放）和 `CABLE Output`（录音）；
2. `--test` 看录回电平是否 > 0，为 0 说明没进虚拟声卡；
3. 应用里麦克风是否选了 `CABLE Output`；
4. 蓝牙耳机切换成「免提 HFP」会改变系统设备，建议用有线或切换后重新跑一次。

**Q: 提示合成失败**
A: `edge-tts` 需要联网访问微软语音服务；公司/校园网被拦时换网络或用代理。

**Q: 音色列表**
A: `edge-tts --list-voices` 可列全部；中文常用：
`zh-CN-XiaoxiaoNeural`（女·自然）、`zh-CN-XiaoyiNeural`（女·活泼）、`zh-CN-YunxiNeural`（男·阳光）、`zh-CN-YunjianNeural`（男·解说）、`zh-CN-YunyangNeural`（男·新闻）、`zh-CN-liaoning-XiaobeiNeural`（东北话女）。

## 文件说明

| 文件 | 说明 |
|---|---|
| `speak-mic.py` | 命令行入口（合成 + 定向播放 + 自测） |
| `speak_mic_core.py` | 公共函数（合成/解码/多设备并发播放/电平检测） |
| `speak-mic-ui.py` | Tkinter 图形界面 |
| `speak-mic.ps1` | PowerShell 包装（自动找 python，可读剪贴板） |
| `tts-ui.bat` / `speak-clipboard.bat` | 双击即用的批处理 |
| `requirements.txt` | Python 依赖 |

![screenshot](docs/screenshot.png)

## 已知限制

- 仅 Windows（依赖 WASAPI + 虚拟声卡设备名）
- 语音是**在线合成**，断网不可用（想离线可换 `piper` / `edge-tts` 的本地替代，但音色会差一档）
- 虚拟声卡驱动需要管理员安装，装完要重启一次

## License

MIT
