#!/bin/bash
# PyVista安装脚本 - 解决Python环境问题

echo "=========================================="
echo "PyVista 可视化库安装"
echo "=========================================="

# 检查Python环境
echo ""
echo "检查Python环境..."
PYTHON_VERSION=$(python3 --version 2>&1)
echo "当前Python: $PYTHON_VERSION"

# 检查是否有conda
if command -v conda &> /dev/null; then
    echo "检测到Conda环境"
    read -p "是否使用conda环境? (y/n) " USE_CONDA
    if [ "$USE_CONDA" = "y" ]; then
        conda create -n ai-structure-fea python=3.10
        conda activate ai-structure-fea
        pip install pyvista vtk
        exit 0
    fi
fi

# 使用Homebrew Python或系统Python
echo ""
echo "尝试安装到用户环境..."

# 查找正确的pip
if [ -f "/usr/local/bin/pip3" ]; then
    PIP="/usr/local/bin/pip3"
elif [ -f "/usr/bin/pip3" ]; then
    PIP="/usr/bin/pip3"
else
    PIP="pip3"
fi

echo "使用pip: $PIP"

# 卸载旧版本
echo ""
echo "清理旧版本..."
python3 -m pip uninstall -y pyvista vtk 2>/dev/null || true

# 重新安装
echo ""
echo "安装VTK和PyVista..."
python3 -m pip install --user --upgrade pip
python3 -m pip install --user --force-reinstall vtk pyvista

# 验证安装
echo ""
echo "验证安装..."
python3 -c "
import pyvista
print(f'PyVista版本: {pyvista.__version__}')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ PyVista安装成功!"
else
    echo ""
    echo "⚠️  PyVista导入失败,请尝试:"
    echo "   1. 使用虚拟环境: python3 -m venv venv && source venv/bin/activate"
    echo "   2. 或使用conda: conda create -n ai-fea python=3.10 && conda activate ai-fea"
    echo "   3. 然后运行: pip install pyvista"
fi

echo ""
echo "=========================================="