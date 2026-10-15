# 网易云 W10M 登录文件生成器

输入网易云账号的 **用户 ID** 和 **MUSIC_U**，生成 `settings.dat`，替换到手机后即可登录。

已在网易云 UWP 1.4.1.0 的电脑端和 W10M 手机端测试通过。

## 使用方法

在Windows电脑上运行

1. 下载 `Netease-W10M-Login-Generator.exe`。
2. 双击打开，输入用户 ID 和 MUSIC_U。
3. 点击“生成 settings.dat”，选择保存位置。

用户 ID 是网易云个人主页链接中 `id=` 后面的数字。MUSIC_U 支持直接填写值或粘贴完整 Cookie，没有长度限制。

## 替换到手机

1. 完全退出手机上的网易云音乐。
2. 找到当前安装的网易云应用数据目录，打开其中的 `Settings` 文件夹。
3. 备份整个 `Settings` 文件夹。
4. 用生成的 `settings.dat` 覆盖原文件。
5. 重新打开网易云。

应用数据目录：

- Windows 桌面端：`%LOCALAPPDATA%\Packages\`（可粘贴到文件资源管理器地址栏打开）
- W10M 手机端：`C:\Data\Users\DefApps\AppData\Local\Packages\`

在上述目录中查找网易云文件夹，再进入 `Settings`，替换其中的 `settings.dat`。

替换可以通过大容量模式完成，也可以使用手机上具有完整文件访问权限的文件管理器。

生成的文件包含登录凭据，请勿公开分享。需要还原时，退出网易云并恢复备份的 `Settings` 文件夹。

## 从源码运行

需要 Python 3.10+，双击 `启动生成器.cmd`，或运行：

```powershell
python .\gui.py
```

命令行生成：

```powershell
python .\generate_settings.py --userid '用户ID' --musicu 'MUSIC_U' --out '.\settings.dat'
```


## 原理

程序在本机将登录凭据和账号 ID 写入空白 UWP 设置文件，昵称、歌单等资料由网易云客户端联网获取。

## 许可证

MIT
