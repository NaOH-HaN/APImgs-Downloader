# APImgs Downloader

一个~~高性能~~的ACG图片下载工具，支持多线程下载、实时统计。

## 功能特性

- 🖼️ 智能API调用 - 自动适配桌面/移动端UA获取最佳图片(需要API支持)

- ⚡ 多线程下载 - 支持1-16线程并发控制

> [!CAUTION]
> 请勿滥用！
>
> [默认API][links.defaultAPI] 是免费API服务站点，如果可以，请考虑[捐助][links.defaultAPI.donate]

- 📊 实时监控 - 彩色进度条显示速度/成功率/下载量

- ⚙️ 动态配置 - 运行时修改下载路径/线程数等参数

- 📝 日志系统 - 支持按时间分文件记录操作日志

- 🔄 错误恢复 - 自动重试失败任务并记录错误详情

- 🌐 浏览器集成 - 一键打开当前使用的API网页

## 使用

- 加载完成后输入 ```/download [数量]```, 回车走起！

## 命令大全

### 核心命令

|   命令    |   参数    |   示例    |   说明    |
| -------- | -------- | -------- | -------- |
|/download | [数量]    | /download 50 | 启动下载任务 |
|/stats	   |          |             | 显示统计信息 |

### 配置管理
|   命令    |   参数    |   示例    |   说明    |
| -------- | -------- | -------- | -------- |
| /env | [key] query | /env multithreading query | 查询配置
| /env | [key] set [value] | /env requestUA set mobile | 修改配置

#### 支持配置项：

```downloadPath```: 存储路径

```multithreading```: 并发线程(1-16)

```fetchPerRequest```: 单次请求数量(1-100)

```requestUA```: 自定义User-Agent

```apiURL```: API服务地址

### 系统命令
|   命令    |   参数    |   示例    |   说明    |
| --------- | --------- | --------- | --------- |
| /logcat | start/stop | /logcat start | 启停日志
| /logcat | path [query/set] | /logcat path set ./logs | 日志路径管理
| /apiweb | 无 | /apiweb | 浏览器打开API
| /about | 无 | /about | 显示程序信息

## 统计指标

```/stats``` 命令显示：

- 📥 总请求数

- ✅ 成功下载数

- 📈 成功率

- 📦 总数据量

- 🚀 平均速度

- ⏱ 峰值速度

统计信息示例：

>=== Statistics ===
>
>Total Requests:    158
>
>Total Downloaded:  142 (89.87%)
>
>Total Size:        214.75 MB
>
>Average Speed:     1.24 MB/s
>
>Peak Speed:        5.68 MB/s
>

## 安装

1. 克隆本仓库

```bash
git@github.com:NaOH-HaN/FetchAPImgs.git
```

2. 安装

```bash
pip install -r requirements.txt
```

## 开源说明

Copyright © 2025 NaOH_HaN

Licensed under the Apache License, Version 2.0 (the "License");

You may not use this file except in compliance with the License.

## 附加说明

该程序是在 **Deepseek R1** 的帮助下开发的。

90% 的代码由 Deepseek R1 编写。

当然，还有一些神奇的错误需要手动修复

感谢AI，我得到了一些时间来快速学习代码。虽然我还是个新手



[links.defaultAPI]: https://www.loliapi.cn/
[links.defaultAPI.donate]: https://www.loliapi.cn/donate.html