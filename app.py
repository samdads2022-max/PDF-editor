import streamlit as st
import fitz  # PyMuPDF
from io import BytesIO
import os

# --- 1. 全局配置 ---
st.set_page_config(page_title="PDF 编辑器 (多页叠加版)", layout="wide")

# --- 2. 常量定义 ---

# Word 字号对照表 (pt)
WORD_FONT_SIZES = {
    "初号": 42, "小初": 36,
    "一号": 26, "小一": 24,
    "二号": 22, "小二": 18,
    "三号": 16, "小三": 15,
    "四号": 14, "小四": 12,
    "五号": 10.5, "小五": 9,
    "六号": 7.5, "小六": 6.5,
    "七号": 5.5, "八号": 5
}

# 字体路径配置 (请确保 GitHub/本地 有对应文件)
# 建议使用方法一：把字体文件放在和 app.py 同级目录，这里直接写文件名
FONTS_MAP = {
    "默认黑体": "simhei.ttf",
    "标准楷体": "simkai.ttf",
    "标准宋体": "simsun.ttc",
    "Times New Roman": "times.ttf"
}

# --- 3. 辅助函数 ---

def get_available_fonts():
    """只返回存在的字体"""
    available = {}
    for name, path in FONTS_MAP.items():
        # 兼容两种路径：fonts/xxx.ttf 或 xxx.ttf
        if os.path.exists(path):
            available[name] = path
        elif os.path.exists(f"fonts/{path}"):
            available[name] = f"fonts/{path}"
    return available

# --- 4. 初始化 Session State (关键！用于记忆历史操作) ---
if 'history' not in st.session_state:
    st.session_state['history'] = []  # 存储所有添加的文字记录

# --- 5. 主程序 ---
st.title("📄 PDF 编辑器 (支持多页、多位置、Word字号)")

# 侧边栏：文件上传
with st.sidebar:
    st.header("1. 文件与字体")
    uploaded_file = st.file_uploader("上传 PDF", type=["pdf"])
    
    available_fonts = get_available_fonts()
    if not available_fonts:
        st.error("⚠️ 未检测到字体文件，中文将显示乱码或无法运行！")
        current_font_path = None
    else:
        selected_font_name = st.selectbox("选择字体", list(available_fonts.keys()))
        current_font_path = available_fonts[selected_font_name]

# 主界面逻辑
if uploaded_file is not None:
    # 读取文件流
    pdf_bytes = uploaded_file.read()
    
    # 我们需要两个 doc 对象：
    # 1. doc_preview: 用于在屏幕上显示（包含历史记录 + 当前正在调整的预览文字）
    # 2. doc_final: 用于下载（包含历史记录）
    
    # 先打开一个基础文档用于获取信息
    doc_base = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc_base)
    
    col1, col2 = st.columns([1, 2])
    
    # --- 左侧：编辑控制区 ---
    with col1:
        st.subheader("🛠️ 编辑操作台")
        
        # 1. 页面选择
        page_num = st.number_input("当前操作页码", 1, total_pages, 1)
        current_page_index = page_num - 1
        
        # 获取当前页尺寸，用于滑块范围
        page_ref = doc_base[current_page_index]
        page_w = page_ref.rect.width
        page_h = page_ref.rect.height
        
        st.markdown("---")
        
        # 2. 文本内容与样式
        input_text = st.text_area("输入文字内容", "点击此处输入...", height=80)
        
        c1, c2 = st.columns(2)
        with c1:
            # 使用 Word 字号选择器
            size_name = st.selectbox("字号大小", list(WORD_FONT_SIZES.keys()), index=9) # 默认选中"四号"
            font_size = WORD_FONT_SIZES[size_name]
            
            line_spacing = st.slider("行间距", 0.8, 3.0, 1.2, 0.1)
        with c2:
            color_hex = st.color_picker("文字颜色", "#000000") # 默认黑色
            
        # 颜色转换
        r = int(color_hex[1:3], 16) / 255
        g = int(color_hex[3:5], 16) / 255
        b = int(color_hex[5:7], 16) / 255
        
        st.markdown("---")
        
        # 3. 位置定位
        st.write("📍 **调整位置**")
        pos_x = st.slider("横向位置 (X)", 0.0, page_w, 50.0)
        pos_y = st.slider("纵向位置 (Y)", 0.0, page_h, 100.0)
        
        st.markdown("---")
        
        # 4. 动作按钮
        btn_col1, btn_col2 = st.columns(2)
        
        # 确认添加按钮
        if btn_col1.button("➕ 确认添加"):
            if input_text and current_font_path:
                # 把当前的所有参数打包存入 session_state
                new_edit = {
                    "page": current_page_index,
                    "text": input_text,
                    "x": pos_x,
                    "y": pos_y,
                    "font_path": current_font_path,
                    "size": font_size,
                    "color": (r, g, b),
                    "line_spacing": line_spacing
                }
                st.session_state['history'].append(new_edit)
                st.success("已添加！可更换位置继续添加。")
                st.rerun() # 强制刷新页面以更新预览

        # 撤销按钮
        if btn_col2.button("↩️ 撤销上一步"):
            if st.session_state['history']:
                st.session_state['history'].pop()
                st.warning("已撤销最后一次操作")
                st.rerun()
            else:
                st.info("没有可撤销的操作")

        # 显示已添加的列表（简略）
        if st.session_state['history']:
            st.markdown(f"📊 **当前已添加 {len(st.session_state['history'])} 处文本**")
            with st.expander("查看所有编辑记录"):
                for i, edit in enumerate(st.session_state['history']):
                    st.text(f"{i+1}. 第{edit['page']+1}页: {edit['text'][:10]}...")

    # --- 右侧：实时渲染逻辑 ---
    
    # 函数：将单次编辑应用到页面上
    def apply_edit_to_page(page_obj, edit_data):
        # 注册字体
        font_key = "custom_" + os.path.basename(edit_data['font_path'])
        page_obj.insert_font(fontname=font_key, fontfile=edit_data['font_path'])
        
        # 绘制
        lines = edit_data['text'].split('\n')
        cy = edit_data['y']
        for line in lines:
            page_obj.insert_text(
                (edit_data['x'], cy),
                line,
                fontname=font_key,
                fontsize=edit_data['size'],
                color=edit_data['color']
            )
            cy += edit_data['size'] * edit_data['line_spacing']

    # 1. 准备预览用的文档
    # 必须每次重新从 bytes 打开，保证底板是干净的
    doc_preview = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # 2. 先把历史记录画上去
    for edit in st.session_state['history']:
        # 只处理存在的页码
        if edit['page'] < len(doc_preview):
            apply_edit_to_page(doc_preview[edit['page']], edit)
            
    # 3. 再把“当前正在调整”的预览画上去（仅画在当前页，标红显示，方便定位）
    if input_text and current_font_path:
        # 为了区分，预览状态我们稍微用个半透明或者亮色边框（fitz不支持透明文字，我们用红色替代）
        # 这里完全模拟真实效果，但使用红色，提示用户这是"未保存"的状态
        preview_edit = {
            "page": current_page_index,
            "text": input_text,
            "x": pos_x,
            "y": pos_y,
            "font_path": current_font_path,
            "size": font_size,
            "color": (1, 0, 0), # 红色预览
            "line_spacing": line_spacing
        }
        apply_edit_to_page(doc_preview[current_page_index], preview_edit)
        
    with col2:
        st.subheader(f"👀 效果预览 (第 {page_num} 页)")
        st.caption("红色文字为当前预览位置，点击左侧【确认添加】后变为黑色并固定。")
        
        # 渲染当前页
        preview_page = doc_preview[current_page_index]
        pix = preview_page.get_pixmap(dpi=150)
        st.image(pix.tobytes(), use_container_width=True)

    # --- 侧边栏：最终下载 ---
    st.sidebar.markdown("---")
    st.sidebar.header("2. 导出文件")
    
    if st.sidebar.button("💾 生成最终 PDF"):
        # 重新生成一个干净的 doc 用于保存，不包含红色的预览字
        doc_final = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # 写入历史记录
        for edit in st.session_state['history']:
            if edit['page'] < len(doc_final):
                apply_edit_to_page(doc_final[edit['page']], edit)
        
        out_buffer = BytesIO()
        doc_final.save(out_buffer)
        out_buffer.seek(0)
        
        st.sidebar.download_button(
            label="📥 下载 PDF 文件",
            data=out_buffer,
            file_name="finished_document.pdf",
            mime="application/pdf"
        )
        
else:
    st.info("请在左侧上传 PDF 文件以开始编辑。")

