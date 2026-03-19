#!/bin/bash
# Void Linux 中日文环境及雾凇拼音配置脚本 (适用于 XFce)

# 遇到错误立即停止
set -e

echo "=== 开始配置中日文环境 ==="

echo "=> 1. 更新软件源并安装 Noto CJK 字体及必要工具..."
# 安装中日韩字体，以及用于下载雾凇拼音的 git 工具
sudo xbps-install -Sy noto-fonts-cjk noto-fonts-emoji git

echo "=> 2. 生成中日文 Locale 库 (不改变系统默认英文界面)..."
# 取消注释 en_US, zh_CN, ja_JP 以生成对应的字符处理支持
if [ -f /etc/default/libc-locales ]; then
    sudo sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/default/libc-locales
    sudo sed -i 's/^#zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/default/libc-locales
    sudo sed -i 's/^#ja_JP.UTF-8 UTF-8/ja_JP.UTF-8 UTF-8/' /etc/default/libc-locales
    sudo xbps-reconfigure -f glibc-locales
else
    echo "未检测到 libc-locales，你可能使用的是 musl 版本的 Void，跳过 Locale 生成。"
fi

echo "=> 3. 安装 Fcitx5 框架、日文 Mozc 以及中州韵 (Rime) 引擎..."
# 将原先的拼音引擎替换为 fcitx5-rime
sudo xbps-install -y fcitx5 fcitx5-gtk fcitx5-qt fcitx5-configtool fcitx5-rime fcitx5-mozc

echo "=> 4. 下载并部署雾凇拼音 (rime-ice)..."
RIME_DIR="$HOME/.local/share/fcitx5/rime"
mkdir -p "$RIME_DIR"

echo "正在从 GitHub 拉取雾凇拼音词库，请稍候 (可能需要一小段时间)..."
# 使用浅克隆拉取最新版雾凇拼音到临时目录，然后移动到 Rime 配置文件夹
rm -rf /tmp/rime-ice
git clone --depth=1 https://github.com/iDvel/rime-ice.git /tmp/rime-ice
cp -R /tmp/rime-ice/* "$RIME_DIR"/
rm -rf /tmp/rime-ice

# 生成 custom 配置文件，让 Rime 默认激活雾凇拼音方案
cat << EOF > "$RIME_DIR/default.custom.yaml"
patch:
  __include: rime_ice_suggestion:/
  schema_list:
    - schema: rime_ice
EOF
echo "雾凇拼音部署完毕！"

echo "=> 5. 配置当前用户的环境变量..."
# 写入 ~/.xprofile 供 XFce 启动时读取
if ! grep -q "GTK_IM_MODULE=fcitx" ~/.xprofile 2>/dev/null; then
    cat << 'EOF' >> ~/.xprofile

# Fcitx5 环境变量
export GTK_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx
EOF
    echo "环境变量已成功追加到 ~/.xprofile"
else
    echo "~/.xprofile 中已存在输入法变量，跳过。"
fi

echo "=== 配置基本完成！ ==="
echo "请执行注销 (Log Out) 并重新登录 XFce。"
echo "	"
echo "=== 运行完毕后的操作指南 ==="
echo "设置开机自启：在 XFce 的“会话和启动”中添加 fcitx5 -d 为自启动项(触发器：on login)。"
echo "1. 在 Fcitx5 中添加输入法："
echo "	打开 fcitx5-configtool。"
echo "	取消勾选“仅显示当前语言 (Only Show Current Language)”。"
echo "	在可用列表中找到 Rime (中州韵) 和 Mozc，添加到左侧。"
echo "	"
echo "2. 启用雾凇拼音："
echo "切换到 Rime 输入法。"
echo "随便找个文本框（比如终端），按下 F4 或 Ctrl+~，呼出 Rime 的方案菜单。"
echo "选择 雾凇拼音 即可。以后它就会作为默认的中文输入方案了。"
