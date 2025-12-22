import streamlit as st
import fitz  # PyMuPDF
from io import BytesIO
import os

# --- 1. 全局配置 (必须放在第一行) ---
st.set_page_config(page_title="PDF 全能工具箱", layout="wide")

# --- 2. 全局常量与辅助函数 ---

# 字体配置
FONTS_MAP = {
    "默认黑体": "fonts/simhei.ttf",
    "标准楷体": "fonts/simkai.ttf",
    "标准宋体": "fonts/simsun.ttc", # 注意这里是 ttc
    "Times New Roman": "fonts/times.ttf" 
}

# 获取有效字体列表
def get_available_fonts():
    available = {}
    for name, path in FONTS_MAP.items():
        if os.path.exists(path):
            available[name] = path
    return available

# 解析页码字符串 (例如 "1, 3-5")
def parse_page_selection(page_str, max_page):
    selected_pages = set()
    try:
        parts = page_str.replace("，", ",").split(",") 
        for part in parts:
            part = part.strip()
            if not part: continue
            if "-" in part: 
                start, end = map(int, part.split("-"))
                start = max(1, start)
                end = min(max_page, end)
                for p in range(start, end + 1):
                    selected_pages.add(p - 1)
            else: 
                p = int(part)
                if 1 <= p <= max_page:
                    selected_pages.add(p - 1)
        return sorted(list(selected_pages))
    except:
        return []

# --- 3. 侧边栏导航 ---
st.sidebar.title("🛠️ PDF 工具箱")
mode = st.sidebar.radio("请选择功能：", ["🖊️ 编辑文字", "🖇️ 合并 PDF", "✂️ 拆分/删除页面"])

# ========================================================
# 模式一：编辑文字
# ========================================================
if mode == "🖊️ 编辑文字":
    st.title("🖊️ PDF 编辑器 (文字添加)")
    
    # 侧边栏：文件与字体设置
    st.sidebar.header("1. 文件设置")
    uploaded_file = st.file_uploader("上传 PDF", type=["pdf"], key="edit_uploader")
    
    available_fonts = get_available_fonts()
    current_font_path = None

    if not available_fonts:
        st.sidebar.warning("⚠️ fonts文件夹下未检测到字体，中文将无法显示。")
    else:
        st.sidebar.header("2. 字体选择")
        selected_font_name = st.sidebar.selectbox("选择字体", list(available_fonts.keys()))
        current_font_path = available_fonts[selected_font_name]

    # 主体逻辑
    if uploaded_file is not None:
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)

        col1, col2 = st.columns([1, 2])
        
        # 左侧：编辑参数
        with col1:
            st.subheader("内容编辑")
            page_number = st.number_input("选择页码", min_value=1, max_value=total_pages, value=1)
            page_index = page_number - 1
            page = doc[page_index]
            page_w = page.rect.width
            page_h = page.rect.height

            text_input = st.text_area("输入文字 (回车换行)", "在这里输入文字...", height=100)
            
            c1, c2 = st.columns(2)
            with c1:
                font_size = st.number_input("字号", value=30)
                line_spacing = st.slider("行间距", 0.8, 3.0, 1.2, 0.1)
            with c2:
                color_hex = st.color_picker("颜色", "#FF0000")
                r = int(color_hex[1:3], 16) / 255
                g = int(color_hex[3:5], 16) / 255
                b = int(color_hex[5:7], 16) / 255

            x_pos = st.slider("X 轴位置", 0.0, page_w, 50.0)
            y_pos = st.slider("Y 轴位置", 0.0, page_h, 100.0)

        # 绘制逻辑
        def draw_multiline_text(page_obj):
            if not text_input: return
            font_key = "custom_font"
            # 只有当字体路径存在时才注册
            if current_font_path:
                page_obj.insert_font(fontname=font_key, fontfile=current_font_path)
                final_font = font_key
            else:
                final_font = "helv" # 默认英文字体

            lines = text_input.split('\n')
            current_y = y_pos
            for line in lines:
                page_obj.insert_text(
                    (x_pos, current_y),
                    line,
                    fontsize=font_size,
                    fontname=final_font,
                    color=(r, g, b)
                )
                current_y += font_size * line_spacing

        draw_multiline_text(page)

        # 右侧：预览
        with col2:
            st.subheader("预览")
            pix = page.get_pixmap(dpi=150)
            st.image(pix.tobytes(), use_container_width=True)

        # 导出
        st.sidebar.markdown("---")
        output_buffer = BytesIO()
        doc.save(output_buffer)
        output_buffer.seek(0)
        st.sidebar.download_button("📥 下载结果", output_buffer, "edited.pdf", "application/pdf")
    
    else:
        st.info("请在左侧上传 PDF 文件。")

# ========================================================
# 模式二：合并 PDF
# ========================================================
elif mode == "🖇️ 合并 PDF":
    st.title("🖇️ PDF 合并工具")
    
    uploaded_files = st.file_uploader("请按顺序上传多个 PDF", type=["pdf"], accept_multiple_files=True, key="merge_uploader")

    if uploaded_files and len(uploaded_files) > 1:
        st.success(f"已选中 {len(uploaded_files)} 个文件。")
        if st.button("开始合并"):
            merged_doc = fitz.open()
            for file in uploaded_files:
                file_bytes = file.read()
                with fitz.open(stream=file_bytes, filetype="pdf") as temp_doc:
                    merged_doc.insert_pdf(temp_doc)
            
            out_buf = BytesIO()
            merged_doc.save(out_buf)
            out_buf.seek(0)
            st.download_button("📥 下载合并后文件", out_buf, "merged.pdf", "application/pdf")
    elif uploaded_files:
        st.warning("请至少上传 2 个文件。")

# ========================================================
# 模式三：拆分与删除
# ========================================================
elif mode == "✂️ 拆分/删除页面":
    st.title("✂️ 页面管理")
    
    uploaded_file = st.file_uploader("上传 PDF", type=["pdf"], key="split_uploader")
    
    if uploaded_file:
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = len(doc)
        
        st.info(f"文档共 {total_pages} 页。")
        
        col1, col2 = st.columns(2)
        with col1:
            action = st.radio("操作模式", ["删除指定页", "仅提取保留指定页"])
        with col2:
            page_input = st.text_input("输入页码 (如: 1, 3-5)", "1")
        
        selected_indices = parse_page_selection(page_input, total_pages)
        human_readable = [p+1 for p in selected_indices]
        
        if selected_indices:
            st.write(f"选中页码: {human_readable}")
            if st.button("执行操作"):
                if action == "仅提取保留指定页":
                    doc.select(selected_indices)
                    msg = "提取成功"
                else:
                    # 计算剩余页面的索引
                    all_indices = set(range(total_pages))
                    keep = sorted(list(all_indices - set(selected_indices)))
                    if not keep:
                        st.error("不能删除所有页面！")
                        st.stop()
                    doc.select(keep)
                    msg = "删除成功"
                
                out_buf = BytesIO()
                doc.save(out_buf)
                out_buf.seek(0)
                st.success(f"{msg}！当前剩余 {len(doc)} 页。")
                st.download_button("📥 下载结果", out_buf, "processed.pdf", "application/pdf")
        else:
            st.warning("请输入有效的页码。")