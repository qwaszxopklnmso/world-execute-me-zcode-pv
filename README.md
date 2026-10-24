# world.execute(me); — 终端处决风格 PV 渲染器

用 **LRC 歌词 + MP3 音频**程序化生成的 MV：整个画面是一场 `world.exe` 对进程 `[me]` 的处决日志。

歌曲：**《world.execute(me);》** — mili（vocal & lyrics: momocashew，专辑《Miracle Milk》）
试听：<https://music.163.com/#/song?id=435278010>

## 画面概念

- **Boot**：歌词即启动序列（power line / object creation / initialization 进度条）
- **Object "me"**：中央 540 点几何体随歌词变形——点集 → 圆 → 正弦 → 螺旋（"If I'm a set of points / circle / sine wave…"）
- **Isolation**：每唱一次 "You have left"，一圈同伴虚线环熄灭一个
- **ERROR**："Illegal arguments" → 红色 `ILLEGAL_ARGUMENT` 横幅
- **Execution ×12**：瞄准倒计时后，每声 "Execution" 砸下红色戳记并抹除一段圆环
- **lo-o-ove**：被处决的 "me" 带着损伤斑点重组，频谱换成心电图 EKG，尾奏 FLATLINE
- **Terminated**：`exit code 0`，`recompile? [Y/N]_`

全程音频反应：RMS / 三频段 / 64 频谱带 / 节拍点驱动频谱、RGB 分离、频带撕裂、屏幕抖动与反色闪帧；歌词按 LRC 时间戳逐字打出（终端解码效果）。

## 使用

依赖：Python 3.10+、`numpy`、`Pillow`、`ffmpeg`（在 PATH 中）。

```bash
pip install numpy pillow
# 把 song.mp3 和 lyrics.lrc 放在本目录（song.mp3 不入库，见 .gitignore）
python pv/extract_features.py   # 提取音频特征 → pv/features.npz
python pv/render_pv.py          # 渲染 → world_execute_me_pv.mp4（约 12 分钟）
python pv/render_pv.py --still 8 34.5 149.5   # 只出静帧检查
```

输出：1920×1080 / 30fps / H.264 + AAC。

## 文件

```
lyrics.lrc              歌词时间轴
pv/extract_features.py  音频特征提取（能量/频段/节拍）
pv/render_pv.py         帧渲染器（PIL 绘制 + numpy 后期 → ffmpeg 管道编码）
```

## License

[MIT](LICENSE) © qwaszxopklnm

歌曲版权归原作方所有；本仓库仅包含渲染代码与歌词时间轴。
