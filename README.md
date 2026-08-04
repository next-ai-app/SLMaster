<h1 align="center">
  SLMaster
</h1>

![win-badge] ![release-badge] ![download-badge] ![download-latest]

<p align="center">
<a href="README_EN.md">English</a> | 简体中文
</p>

[win-badge]: https://github.com/Practice3DVision/SLMaster/workflows/Windows/badge.svg  "Windows"
[win-link]: https://github.com/Practice3DVision/SLMaster/actions/workflows/windows.yml  "Windows"
[release-badge]: https://img.shields.io/github/release/Practice3DVision/SLMaster.svg "Release status"
[release-link]: https://github.com/Practice3DVision/SLMaster/releases "Release status"
[download-badge]: https://img.shields.io/github/downloads/Practice3DVision/SLMaster/total.svg "Download status"
[download-link]: https://github.com/Practice3DVision/SLMaster/releases/latest "Download status"
[download-latest]: https://img.shields.io/github/downloads/Practice3DVision/SLMaster/latest/total.svg "latest status"

[SLMaster](https://github.com/Practice3DVision/SLMaster)是一个较为完整的结构光3D相机软件。您可以使用它对任意被测物体完成静态扫描或者实时动态扫描。

该软件相关博客可见公众号专栏：[从0到1搭建一套属于你自己的高精度实时结构光3D相机](https://mp.weixin.qq.com/s/E8K3892eNVJfgpMUHtf9Lw)，欢迎关注公众号。

请动动小手点击右上角的**Star**⭐，您的**Star**⭐和关注是博主源源不断的动力。

有任何问题和**bug**反馈请提**Issue**。谢绝不给**Star**⭐，反复咨询解决方案的情况。

**想先体验该软件？**

请在`Release`页面下载`exe`安装文件，但请注意`exe`安装方式不支持`GPU`加速。

更多使用与开发文档请查阅[Wiki Document](https://github.com/Practice3DVision/SLMaster/wiki)。

## 依赖 🍁
**SLMaster**依赖的库包含如下几点：
- [FluentUI](https://github.com/Practice3DVision/SLMaster/tree/master/FluentUI)`V1.5.6`（项目内包含）
- [QuickQanava](https://github.com/cneben/QuickQanava/tree/2.4.1)`V2.4.1`（项目内包含）
- [MVViewer](https://www.irayple.com/cn/serviceSupport/downloadCenter/18?p=17)`V2.3.5`
- [opencv_contribute](https://github.com/opencv/opencv_contrib.git)`V4.8.0`
- [OpenCV](https://github.com/opencv/opencv.git)`V4.8.0`
- [VTK](https://github.com/Kitware/VTK/tree/v9.2.0)`V9.2.0`
- [PCL](https://github.com/PointCloudLibrary/pcl/tree/pcl-1.12.1)`V1.12.1`
- [Qt5](https://doc.qt.io/qt-5/index.html)`V5.15.14`

> 如果电脑没有`NVIDIA GPU`，软件仍然能够使用CPU加速有效运行，此时可无需`opencv_contribute`依赖。

## 支持硬件 🧩
**SLMaster**对**相机**和**投影仪**进行了抽象，您可以根据现有硬件实现抽象类接口，快速适配本软件。当前已内置支持的硬件：
- 相机：华睿相机（通过`MVViewer` SDK）
- 投影仪：DLP34XX系列（`DLP3010`、`DLP4710`）

## 项目结构 📂
- `data`：离线数据集
  - `4_4710`：用于投影仪烧录的测试数据
  - `binocularCamera`：双目结构光相机真实数据集
  - `monocularCamera`：单目结构光相机真实数据集
  - `laserLine`：单线激光相机数据集
  - `interzoneFourGrayscale`：四灰度格雷码广义分区间相位展开方法仿真数据集
  - `shiftGraycode`：位移格雷码方法仿真数据集
  - `threeFrequencyHeterodyne`：三频外差方法仿真数据集
- `src`：算法源文件
  - `algorithm`：结构光算法（CPU + CUDA）　`calibration`：标定算法
  - `cameras`：结构光相机（单/双/三目）　`device`：硬件控制（相机/投影仪抽象）
- `gui`：软件界面
  - `qml`：Qt QML文件及资源（`qml/res/config`为相机配置文件）
  - `src`：UI源文件（含节点编辑器节点）
  - `thirdParty`：第三方库（FluentUI、QuickQanava）
- `test`：准确度测试（google_test）　`perf`：性能测试（google_benchmark）

## 编译 🚀
当您获取到本库代码之后，首先检查上述依赖，若不满足依赖条件，可通过点击上述依赖库跳转至对应的库，随后下载其代码并进行编译。以上面库皆没有编译安装的环境为例，编译顺序如下：
1. 下载[MVViewer](https://www.irayple.com/cn/serviceSupport/downloadCenter/18?p=17)并进行安装。
2. 下载[OpenCV](https://github.com/opencv/opencv.git)和[opencv_contribute](https://github.com/opencv/opencv_contrib.git)并进行编译（若`WITH_CUDA`未勾选请勾选上）
3. 下载[Qt5.15](https://doc.qt.io/qt-5/index.html)并选择`MSVC`编译套件安装
4. 下载[VTK](https://github.com/Kitware/VTK/tree/v9.2.0)并令`VTK_GROUP_ENABLE_Qt=YES`进行编译
5. 下载[PCL-1.12.1-AllInOne](https://github.com/PointCloudLibrary/pcl/releases)进行安装，安装完成后删除`PCL`安装文件夹下的除`3rdParty`外的其它任何文件，并将`3rdParty`文件夹中的`VTK`文件夹删除
6. 下载[PCL](https://github.com/PointCloudLibrary/pcl/tree/pcl-1.12.1)并选择好第三方库路径进行编译
7. 打开命令行窗口，键入`git clone --recursive https://github.com/Practice3DVision/SLMaster.git`克隆`SLMaster`
8. 打开您喜欢的编译器，使用`Ninja`生成器，将编译目录设置为`${work_space}/build`，编译运行`SLMasterGui`即可

> 注意！
> 每当编译好一个库都应当在系统环境变量中加入。例如，编译完成OpenCV后，设置好系统环境变量OpenCV_DIR路径。


您可以打开`SLMaster`中的`BUILD_TEST`和`BUILD_PERF`选项，这将编译**google_test**和**google_benchmark**中的测试用例，这些测试用例同样是一份非常不错的示例代码。
## 使用 🌈

离线使用情况下，可通过进入`扫描模式->离线扫描模式->选择左相机文件夹->选择右相机文件夹->开始扫描->单次扫描`测试离线重建效果，软件提供一组离线数据集位于`安装目录/data/`下。

如您需要更改算法参数以测试自己的离线数据集，请通过更改`安装目录/gui/qml/res/config`下的相机配置文件，该文件记录了**3D**相机所有的状态，包括硬件组成、算法参数等。

如您需要接入硬件并执行在线功能，请修改`安装目录/gui/qml/res/config`下的相机配置文件，确保硬件组成参数与您所用的硬件设备一致。

### 3D相机控制
进入`设备`页面可切换`单目结构光相机`、`双目结构光相机`、`三目结构光相机`类型；相机在线时可连接设备并进行投影测试（单次/连续/暂停/步进/停止投影及十字线功能），投影期间2D相机将被设置为曝光时间一致，可近实时查看相机捕获的条纹，验证当前相机配置。

### 条纹编码
进入`条纹编码`页面可切换编码方法并生成条纹，主要参数：
- **像素深度**：1位深度 / 8位深度
- **方向选择**：水平方向 / 垂直方向（相位变化方向）
- **条纹类型**：正弦互补格雷码、三频外差、多视立体几何约束、正弦移位格雷码、四灰度编码广义分区间相位展开
- **离焦编码**（仅1位深度可用）：简单二值化、二维误差扩散法、最佳脉冲宽度调制方法
- **幅面与裁剪**：图像超过投影仪幅面时多余像素被忽略，不足补0；当周期宽度不能被整除时，可生成略大幅面的整数周期条纹，再裁剪至实际投影仪幅面
- **周期数与相移次数**：周期数为`n`时生成`log₂(n)`张格雷码；若为互补格雷码方法则为`log₂(n)+1`张
- **烧录与保存**：选择`保留前序编码条纹`可分批烧录多组条纹序列（投影仪标定必需）；生成的条纹可于`设备`页面烧录至3D相机，或点击`保存`离线保存

## 部分功能  💡

|功能|示例|功能|示例|
|:-|-|:-|-|
|单双三目重建|![在线扫描功能](doc/online_scan.png)|实时重建|![实时扫描功能](doc/04.gif)|
|硬件在线调试|![十字线校准功能](doc/tenline.png)|条纹生成|![条纹生成功能](doc/stripe_create.png)|
|相机标定|![离线相机标定功能](doc/calibration.png)|误差分布显示|![标定误差分布图显示功能](doc/error_distribute.png)|
|投影仪标定|![在线投影仪标定功能](doc/online_calinbration.png)|点云后处理|![后处理功能](doc/post_process.png)|

## License 📕

SLMaster当前使用[AGPL-3.0](./LICENSE)许可证.

## Star History ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=Practice3DVision/SLMaster&type=Date)](https://star-history.com/#Practice3DVision/SLMaster&Date)

## Visitor count ⚡
![](https://profile-counter.glitch.me/Practice3DVision-SLMaster/count.svg)
