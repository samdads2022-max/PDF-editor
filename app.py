import streamlit as st
import fitz  # PyMuPDF
from io import BytesIO
import os
# 新增库：用于 PDF 转 Word
from pdf2docx import Converter

# --- 1. 全局配置 ---
st.set_page_config(page_title="PDF 全能工具箱 Pro Max", layout="wide")

# --- 2. 常量与辅助函数 ---
WORD_FONT_SIZES = {
    "初号": 42, "小初": 36, "一号": 26, "小一": 24, "二号": 22, "小二": 18,
    "三号": 16, "小三": 15, "四号": 14, "小四": 12, "五号": 10.5, "小五": 9
}

FONTS_MAP = {
    "默认黑体": "simhei.ttf", "标准楷体": "simkai.ttf",
    "标准宋体": "simsun.ttc", "Times New Roman": "times.ttf"
}

def get_available_fonts():
    available = {}
    for name, path in FONTS_MAP.items():
        if os.path.exists(path): available[name] = path
        elif os.path.exists(f"fonts/{path}"): available[name] = f"fonts/{path}"
    return available

def parse_page_selection(page_str, max_page):
    selected = set()
    try:
        parts = page_str.replace("，", ",").split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                s, e = map(int, part.split("-"))
                for p in range(max(1, s), min(max_page, e) + 1): selected.add(p - 1)
            else:
                p = int(part)
                if 1 <= p <= max_page: selected.add(p - 1)
        return sorted(list(selected))
    except: return []

if 'edit_history' not in st.session_state:
    st.session_state['edit_history'] = []

# --- 3. 侧边栏菜单 ---
st.sidebar.title("🛠️ PDF 工具箱")
mode = st.sidebar.radio("功能选择", [
    "🖊️ 高级编辑 (添加文字)", 
    "🔄 PDF 转 Word", 
    "🖇️ 合并 PDF", 
    "✂️ 拆分/删除页面"
])

# ========================================================
# 功能一：高级编辑 (含选择性删除)
# ========================================================
if mode == "🖊️ 高级编辑 (添加文字)":
    st.title("🖊️ PDF 编辑器 (图层管理版)")

    with st.sidebar:
        st.header("1. 文件与字体")
        uploaded_file = st.file_uploader("上传 PDF", type=["pdf"], key="edit_up")
        
        fonts = get_available_fonts()
        if not fonts:
            st.error("⚠️ 未检测到字体！")
            font_path = None
        else:
            fname = st.selectbox("选择字体", list(fonts.keys()))
            font_path = fonts[fname]

        # --- 新增：选择性删除区域 ---
        st.markdown("---")
        st.header("📝 已添加图层 (可删除)")
        
        if not st.session_state['edit_history']:
            st.caption("暂无添加记录")
        else:
            # 遍历列表显示，注意要倒序显示(最新的在最上面)，还是正序？通常最新的在下。
            # 这里我们用 enumerate 获取索引，用于删除
            
            # 为了防止删除时索引错位，创建一个副本进行遍历，或者直接根据索引删除
            for i, item in enumerate(st.session_state['edit_history']):
                # 使用列布局：文字信息 + 删除按钮
                c_info, c_del = st.columns([5, 1])
                with c_info:
                    st.text(f"#{i+1} [P{item['page']+1}] {item['text'][:6]}...")
                with c_del:
                    # key 必须唯一，否则报错
                    if st.button("🗑️", key=f"del_btn_{i}", help="删除此条记录"):
                        st.session_state['edit_history'].pop(i)
                        st.rerun() # 立即刷新

    if uploaded_file:
        pdf_bytes = uploaded_file.read()
        doc_base = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc_base)

        col1, col2 = st.columns([1, 2])
        
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
                color = st.color_picker("颜色", "#000000")
                r = int(color[1:3], 16)/255
                g = int(color[3:5], 16)/255
                b = int(color[5:7], 16)/255
                current_rgb = (r, g, b)
            
            x = st.slider("X轴", 0.0, w, 50.0)
            y = st.slider("Y轴", 0.0, h, 100.0)
            
            if st.button("➕ 确认添加", type="primary"):
                if txt and font_path:
                    st.session_state['edit_history'].append({
                        "page": p_idx, "text": txt, "x": x, "y": y,
                        "font": font_path, "size": f_size, 
                        "color": current_rgb, "spacing": l_space
                    })
                    st.success("已添加！")
                    st.rerun()

        # 绘制函数
        def draw(page, item):
            key = "font_" + os.path.basename(item['font'])
            page.insert_font(fontname=key, fontfile=item['font'])
            lines = item['text'].split('\n')
            cy = item['y']
            for line in lines:
                page.insert_text((item['x'], cy), line, fontname=key, fontsize=item['size'], color=item['color'])
                cy += item['size'] * item['spacing']

        doc_view = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # 1. 画历史
        for item in st.session_state['edit_history']:
            if item['page'] < len(doc_view):
                draw(doc_view[item['page']], item)
                
        # 2. 画预览
        if txt and font_path:
            preview_item = {
                "text": txt, "x": x, "y": y, "font": font_path,
                "size": f_size, "spacing": l_space, "color": current_rgb
            }
            draw(doc_view[p_idx], preview_item)

        with col2:
            st.subheader("👀 效果预览")
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
# 功能二：PDF 转 Word (新增)
# ========================================================
elif mode == "🔄 PDF 转 Word":
    st.title("🔄 PDF 转 Word (docx)")
    st.info("💡 提示：此功能适合转换非扫描版的 PDF（即可以选择文字的 PDF）。扫描件转换效果可能不佳。")
    
    uploaded_file = st.file_uploader("上传 PDF 文件", type=["pdf"])
    
    if uploaded_file:
        if st.button("🚀 开始转换"):
            with st.spinner("正在转换中，请稍候... (页数多会比较慢)"):
                try:
                    # pdf2docx 需要物理文件路径，所以我们要创建临时文件
                    # 1. 保存上传的 PDF 到临时文件
                    with open("temp_input.pdf", "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 2. 执行转换
                    cv = Converter("temp_input.pdf")
                    cv.convert("temp_output.docx", start=0, end=None)
                    cv.close()
                    
                    # 3. 读取结果文件
                    with open("temp_output.docx", "rb") as f:
                        docx_bytes = f.read()
                    
                    # 4. 清理临时文件 (保持环境整洁)
                    os.remove("temp_input.pdf")
                    os.remove("temp_output.docx")
                    
                    st.success("✅ 转换成功！")
                    st.download_button(
                        label="📥 下载 Word 文档",
                        data=docx_bytes,
                        file_name="converted.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"转换失败: {str(e)}")

# ========================================================
# 功能三：合并 PDF
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
# 功能四：拆分/删除
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
            if act == "仅保留页码": doc.select(sel)
            else:
                keep = sorted(list(set(range(len(doc))) - set(sel)))
                if not keep: st.error("不能删除所有页")
                else: doc.select(keep)
            out = BytesIO()
            doc.save(out)
            out.seek(0)
            st.download_button("📥 下载结果", out, "processed.pdf", "application/pdf")




