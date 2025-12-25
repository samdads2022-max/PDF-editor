import streamlit as st
import fitz  # PyMuPDF
from io import BytesIO
import os

# --- 1. 全局配置 ---
st.set_page_config(page_title="PDF 全能工具箱 Pro", layout="wide")

# --- 2. 常量与辅助函数 ---

# Word 字号对照表
WORD_FONT_SIZES = {
    "初号": 42, "小初": 36,
    "一号": 26, "小一": 24,
    "二号": 22, "小二": 18,
    "三号": 16, "小三": 15,
    "四号": 14, "小四": 12,
    "五号": 10.5, "小五": 9
}

# 字体路径
FONTS_MAP = {
    "默认黑体": "simhei.ttf",
    "标准楷体": "simkai.ttf",
    "标准宋体": "simsun.ttc",
    "Times New Roman": "times.ttf"
}

def get_available_fonts():
    available = {}
    for name, path in FONTS_MAP.items():
        if os.path.exists(path):
            available[name] = path
        elif os.path.exists(f"fonts/{path}"):
            available[name] = f"fonts/{path}"
    return available

def parse_page_selection(page_str, max_page):
    selected = set()
    try:
        parts = page_str.replace("，", ",").split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                s, e = map(int, part.split("-"))
                for p in range(max(1, s), min(max_page, e) + 1):
                    selected.add(p - 1)
            else:
                p = int(part)
                if 1 <= p <= max_page: selected.add(p - 1)
        return sorted(list(selected))
    except:
        return []

if 'edit_history' not in st.session_state:
    st.session_state['edit_history'] = []

# --- 3. 侧边栏菜单 ---
st.sidebar.title("🛠️ PDF 工具箱")
mode = st.sidebar.radio("功能选择", ["🖊️ 高级编辑 (添加文字)", "🖇️ 合并 PDF", "✂️ 拆分/删除页面"])

# ========================================================
# 功能一：高级编辑
# ========================================================
if mode == "🖊️ 高级编辑 (添加文字)":
    st.title("🖊️ 高级 PDF 编辑器")

    with st.sidebar:
        st.header("1. 文件与字体")
        uploaded_file = st.file_uploader("上传 PDF", type=["pdf"], key="edit_up")
        
        fonts = get_available_fonts()
        if not fonts:
            st.error("⚠️ 未检测到字体文件！")
            font_path = None
        else:
            fname = st.selectbox("选择字体", list(fonts.keys()))
            font_path = fonts[fname]
    
    if uploaded_file:
        pdf_bytes = uploaded_file.read()
        doc_base = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc_base)

        col1, col2 = st.columns([1, 2])
        
        # 左侧操作台
        with col1:
            st.subheader("🛠️ 参数调整")
            p_num = st.number_input("当前页码", 1, total_pages, 1)
            p_idx = p_num - 1
            
            page_ref = doc_base[p_idx]
            w, h = page_ref.rect.width, page_ref.rect.height
            
            txt = st.text_area("输入文字", "在此输入...", height=80)
            
            c1, c2 = st.columns(2)
            with c1:
                sz_name = st.selectbox("字号", list(WORD_FONT_SIZES.keys()), index=8)
                f_size = WORD_FONT_SIZES[sz_name]
                l_space = st.slider("行间距", 0.5, 3.0, 1.2, 0.1)
            with c2:
                # 颜色选择器
                color = st.color_picker("颜色", "#000000")
                # 将 Hex 转换为 RGB (0~1的小数)
                r = int(color[1:3], 16)/255
                g = int(color[3:5], 16)/255
                b = int(color[5:7], 16)/255
                current_rgb = (r, g, b)
            
            st.write("📍 **位置调整**")
            x = st.slider("X轴", 0.0, w, 50.0)
            y = st.slider("Y轴", 0.0, h, 100.0)
            
            b1, b2 = st.columns(2)
            if b1.button("➕ 确认添加", type="primary"):
                if txt and font_path:
                    st.session_state['edit_history'].append({
                        "page": p_idx, "text": txt, "x": x, "y": y,
                        "font": font_path, "size": f_size, 
                        "color": current_rgb, "spacing": l_space
                    })
                    st.success("已添加！")
                    st.rerun()

            if b2.button("↩️ 撤销一步"):
                if st.session_state['edit_history']:
                    st.session_state['edit_history'].pop()
                    st.warning("已撤销")
                    st.rerun()
            
            if st.session_state['edit_history']:
                with st.expander(f"已添加 {len(st.session_state['edit_history'])} 处文本"):
                    for i, item in enumerate(st.session_state['edit_history']):
                        st.text(f"{i+1}. 第{item['page']+1}页: {item['text'][:8]}...")

        # --- 核心修改点：绘制逻辑 ---
        def draw(page, item):
            key = "font_" + os.path.basename(item['font'])
            page.insert_font(fontname=key, fontfile=item['font'])
            lines = item['text'].split('\n')
            cy = item['y']
            # 直接使用 item 里的颜色，不再强制变红
            for line in lines:
                page.insert_text((item['x'], cy), line, fontname=key, fontsize=item['size'], color=item['color'])
                cy += item['size'] * item['spacing']

        doc_view = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # 1. 画历史记录
        for item in st.session_state['edit_history']:
            if item['page'] < len(doc_view):
                draw(doc_view[item['page']], item)
                
        # 2. 画当前预览 (使用当前选中的颜色)
        if txt and font_path:
            preview_item = {
                "text": txt, "x": x, "y": y, "font": font_path,
                "size": f_size, "spacing": l_space, 
                "color": current_rgb # 这里直接传入你选的颜色
            }
            # 画在当前页
            draw(doc_view[p_idx], preview_item)

        with col2:
            st.subheader("👀 效果预览")
            # 渲染图片
            pix = doc_view[p_idx].get_pixmap(dpi=150)
            st.image(pix.tobytes(), use_container_width=True)

        st.sidebar.markdown("---")
        if st.sidebar.button("💾 下载最终 PDF"):
            doc_final = fitz.open(stream=pdf_bytes, filetype="pdf")
            for item in st.session_state['edit_history']:
                if item['page'] < len(doc_final):
                    draw(doc_final[item['page']], item)
            out = BytesIO()
            doc_final.save(out)
            out.seek(0)
            st.sidebar.download_button("📥 点击下载", out, "edited.pdf", "application/pdf")

# ========================================================
# 功能二：合并 PDF
# ========================================================
elif mode == "🖇️ 合并 PDF":
    st.title("🖇️ PDF 合并")
    files = st.file_uploader("上传多个文件", type=["pdf"], accept_multiple_files=True)
    if files and len(files) > 1:
        if st.button("开始合并"):
            m_doc = fitz.open()
            for f in files:
                with fitz.open(stream=f.read(), filetype="pdf") as t_doc:
                    m_doc.insert_pdf(t_doc)
            out = BytesIO()
            m_doc.save(out)
            out.seek(0)
            st.download_button("📥 下载合并文件", out, "merged.pdf", "application/pdf")

# ========================================================
# 功能三：拆分/删除
# ========================================================
elif mode == "✂️ 拆分/删除页面":
    st.title("✂️ 页面管理")
    up_file = st.file_uploader("上传 PDF", type=["pdf"], key="split_up")
    if up_file:
        doc = fitz.open(stream=up_file.read(), filetype="pdf")
        st.info(f"共 {len(doc)} 页")
        act = st.radio("模式", ["删除页码", "仅保留页码"])
        p_str = st.text_input("页码 (如 1, 3-5)", "1")
        sel = parse_page_selection(p_str, len(doc))
        
        if sel and st.button("执行"):
            if act == "仅保留页码":
                doc.select(sel)
            else:
                keep = sorted(list(set(range(len(doc))) - set(sel)))
                if not keep: st.error("不能删除所有页")
                else: doc.select(keep)
            
            out = BytesIO()
            doc.save(out)
            out.seek(0)
            st.success("完成！")
            st.download_button("📥 下载结果", out, "processed.pdf", "application/pdf")



