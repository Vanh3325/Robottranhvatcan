"""Fill the retained project-report template and create explanatory diagrams."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
TMP = ROOT / "tmp"
TEMPLATE = ROOT / ".tools/template.docx"
OUTPUT = ROOT / "Bao_cao_AMR_ESP32_hoan_thien.docx"
FONT = Path("C:/Windows/Fonts")


def font(size=28, bold=False):
    return ImageFont.truetype(str(FONT / ("segoeuib.ttf" if bold else "segoeui.ttf")), size)


def wrap(draw, text, width, f):
    result = []
    for line in text.split("\n"):
        words, current = line.split(), ""
        for word in words:
            candidate = (current + " " + word).strip()
            if draw.textlength(candidate, font=f) > width and current:
                result.append(current)
                current = word
            else:
                current = candidate
        result.append(current)
    return result


def text_block(draw, box, title, body="", fill="#f1f5f8", stroke="#667e8e", title_size=29, size=25):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=12, fill=fill, outline=stroke, width=2)
    title_lines = wrap(draw, title, x2-x1-32, font(title_size, True))
    body_lines = wrap(draw, body, x2-x1-32, font(size)) if body else []
    line_h = size + 9
    total = len(title_lines)*(title_size+9) + (16 if body_lines else 0) + len(body_lines)*line_h
    y = y1 + (y2-y1-total)/2
    for line in title_lines:
        draw.text(((x1+x2-draw.textlength(line, font=font(title_size,True)))/2, y), line,
                  font=font(title_size,True), fill="#142b3b")
        y += title_size+9
    y += 16 if body_lines else 0
    for line in body_lines:
        draw.text(((x1+x2-draw.textlength(line,font=font(size)))/2,y),line,font=font(size),fill="#223a49")
        y += line_h


def arrow(draw, a, b, both=False, color="#335b72", width=4):
    import math
    draw.line([a,b],fill=color,width=width)
    def head(p, q):
        angle=math.atan2(p[1]-q[1],p[0]-q[0]); size=15
        draw.polygon([p,(p[0]-size*math.cos(angle-.5),p[1]-size*math.sin(angle-.5)),
                       (p[0]-size*math.cos(angle+.5),p[1]-size*math.sin(angle+.5))],fill=color)
    head(b,a)
    if both: head(a,b)


def diagram_heading(draw, title, subtitle, width):
    draw.text((36, 20), title, font=font(35,True),fill="#152c3c")
    draw.text((36, 70), subtitle, font=font(23),fill="#526b7b")


def diagrams():
    ASSETS.mkdir(exist_ok=True)
    im = Image.new("RGB", (1600, 850), "white"); d=ImageDraw.Draw(im)
    diagram_heading(d,"KIẾN TRÚC ĐIỀU KHIỂN VÀ PHẢN HỒI","Hai ESP32 • giao tiếp cục bộ • liên động đặt trên robot",1600)
    text_block(d,(35,175,405,420),"APP PYTHON","Tkinter • manual / auto\nARM • STOP • CSV")
    text_block(d,(615,175,985,420),"ESP32 GATEWAY","USB serial 115200\nChuyển tiếp JSON")
    text_block(d,(1190,175,1560,420),"ESP32 ROBOT","Lệnh + watchdog\nThuật toán tránh vật cản")
    arrow(d,(415,290),(605,290),True); d.text((445,235),"USB / UART",font=font(24),fill="#35566b")
    arrow(d,(995,290),(1180,290),True); d.text((1027,235),"ESP-NOW",font=font(24),fill="#35566b")
    text_block(d,(850,535,1190,710),"SIÊU ÂM + SERVO","Đo theo góc\nMẫu hợp lệ + tuổi dữ liệu",title_size=26,size=23)
    text_block(d,(1230,535,1560,710),"TB6612 + 2 MOTOR","PWM trái / phải\nChiều quay / dừng",title_size=26,size=23)
    arrow(d,(1300,430),(1040,525),True); arrow(d,(1440,430),(1440,525))
    d.text((40,570),"LỆNH →",font=font(28,True),fill="#223b4c")
    d.text((40,620),"← ACK từ robot + telemetry",font=font(26),fill="#223b4c")
    d.text((40,760),"PC cần ESP32 gateway USB. Cloud không sử dụng trong phiên bản này.",font=font(26),fill="#3b5667")
    im.save(ASSETS/"architecture.png")

    im=Image.new("RGB",(1600,1120),"white"); d=ImageDraw.Draw(im)
    diagram_heading(d,"NỐI KHỐI VÀ PHÂN PHỐI NGUỒN","Bảng chân chỉ áp dụng cho ESP32-WROOM-32 dự kiến",1600)
    text_block(d,(40,150,410,410),"ESP32 ROBOT","GPIO25/26/27 → A\nGPIO32/33/14 → B\nGPIO13 → STBY")
    text_block(d,(620,150,1010,410),"TB6612FNG","VCC = 3,3 V\nVM theo động cơ\nSTBY kéo xuống 10 kΩ")
    text_block(d,(1220,150,1560,265),"MOTOR TRÁI","AO1 / AO2",title_size=27,size=25)
    text_block(d,(1220,295,1560,410),"MOTOR PHẢI","BO1 / BO2",title_size=27,size=25)
    arrow(d,(420,280),(610,280)); arrow(d,(1020,210),(1210,210)); arrow(d,(1020,350),(1210,350))
    text_block(d,(40,500,410,680),"SERVO","GPIO19 → signal\nNguồn theo loại servo",title_size=28,size=25)
    text_block(d,(620,500,1010,680),"SIÊU ÂM","GPIO18 → TRIG\nECHO → chia áp → GPIO34",title_size=28,size=24)
    text_block(d,(1220,500,1560,680),"CHIA ÁP ECHO","ECHO → 10 kΩ → GPIO34\nGPIO34 → 18 kΩ → GND",title_size=25,size=23)
    arrow(d,(225,420),(225,490))
    arrow(d,(420,395),(610,515),True)
    arrow(d,(1020,590),(1210,590))
    d.text((45,735),"HC-SR04: nguồn 5 V; Echo không nối trực tiếp GPIO ESP32.",font=font(26,True),fill="#354b59")
    text_block(d,(40,815,1560,1000),"PIN → CÔNG TẮC / BẢO VỆ → CÁC NHÁNH NGUỒN","VM theo motor • rail logic/cảm biến • rail servo theo linh kiện\nGND chung; tách đường dòng motor/servo; kiểm tra sụt áp và chống cấp ngược USB",title_size=29,size=27)
    d.text((45,1040),"Sơ đồ chức năng; chưa thay thế sơ đồ nguyên lý của board và module thực tế.",font=font(25),fill="#4f6675")
    im.save(ASSETS/"wiring.png")

    im=Image.new("RGB",(1600,1430),"white"); d=ImageDraw.Draw(im)
    diagram_heading(d,"MÁY TRẠNG THÁI ĐIỀU KHIỂN","Thiết kế firmware đề xuất • STOP / watchdog luôn được ưu tiên",1600)
    text_block(d,(470,140,1120,245),"KHỞI ĐỘNG / IDLE","PWM = 0 • manual • chưa ARM",title_size=28,size=25)
    text_block(d,(470,320,1120,450),"KIỂM TRA LIÊN ĐỘNG","Estop? Mất liên kết? Cảm biến lỗi/cũ?",title_size=28,size=24)
    arrow(d,(795,255),(795,310))
    text_block(d,(30,310,370,485),"DỪNG / KHÓA","Hủy ARM • PWM = 0\nBáo lỗi / chờ xử lý",fill="#f6e9e9",title_size=28,size=24)
    arrow(d,(460,385),(380,385)); d.text((388,340),"Có",font=font(24),fill="#6b3131")
    text_block(d,(470,530,1120,650),"ĐÃ ARM VÀ CHỌN CHẾ ĐỘ?","Mặc định vẫn đứng yên",title_size=28,size=24)
    arrow(d,(795,460),(795,520)); d.text((815,473),"Không có lỗi",font=font(24),fill="#36586d")
    text_block(d,(40,745,620,930),"MANUAL","Drive còn hạn → kiểm tra khoảng cách\nGiữ hướng để chạy • thả gửi 0/0",title_size=29,size=26)
    text_block(d,(890,745,1560,930),"AUTO_FORWARD","Mẫu trước hợp lệ và đủ khoảng trống\nTiến chậm; gặp vật thì dừng",title_size=29,size=26)
    arrow(d,(660,660),(340,735)); arrow(d,(960,660),(1220,735))
    text_block(d,(890,1000,1560,1145),"AUTO_SCAN","Dừng → quét trái / giữa / phải\nĐợi servo ổn định → lấy mẫu",title_size=28,size=25)
    arrow(d,(1220,940),(1220,990))
    text_block(d,(40,1020,620,1195),"KHÔNG CÓ HƯỚNG THOÁNG","Giữ dừng • không tự lùi\nTiếp tục quan sát / chờ người vận hành",title_size=27,size=24)
    arrow(d,(880,1080),(630,1080)); d.text((670,1030),"Bị chặn",font=font(25),fill="#36586d")
    text_block(d,(890,1230,1560,1370),"AUTO_TURN","Quay chậm từng bước → dừng → đo trước\nChỉ tiến tiếp khi đủ điều kiện",title_size=28,size=24)
    arrow(d,(1220,1155),(1220,1220))
    d.line([(1575,1300),(1585,1300),(1585,690),(1195,690)],fill="#355a70",width=4)
    arrow(d,(1195,690),(1195,735))
    d.text((45,1280),"Mọi vòng lặp đều kiểm tra lại liên động.",font=font(26),fill="#355367")
    d.text((45,1330),"Thời gian quay không phải góc đo thực.",font=font(25),fill="#355367")
    im.save(ASSETS/"flowchart.png")

    im=Image.new("RGB",(1600,1080),"white"); d=ImageDraw.Draw(im)
    d.rectangle((0,0,1600,130),fill="#17344a")
    d.text((40,24),"AMR / CONTROL STATION",font=font(42,True),fill="white")
    d.text((40,80),"Sơ đồ giao diện theo mã Tkinter • không phải ảnh đo thực nghiệm",font=font(26),fill="#cce3ed")
    text_block(d,(35,160,1565,260),"KẾT NỐI","Mô phỏng / COM • Kết nối • Trạng thái ACK / ARM",title_size=28,size=25)
    text_block(d,(35,300,740,850),"ĐIỀU KHIỂN","ARM\nManual / Tự tránh vật cản\nThanh PWM 0…255\nGiữ W/A/S/D hoặc nút hướng\nSTOP / Space • Estop / Esc\nXóa chốt • Góc servo",title_size=32,size=31)
    text_block(d,(780,300,1565,600),"TRẠNG THÁI ROBOT","Mode • ARM • cảm biến hợp lệ\nKhoảng cách (cm) • servo (độ)\nPWM trái/phải • tuổi dữ liệu",title_size=31,size=29)
    text_block(d,(780,640,1565,850),"ĐỒ THỊ / DỮ LIỆU","Lịch sử khoảng cách • Ghi CSV\nMô phỏng lỗi liên kết / cảm biến",title_size=31,size=29)
    text_block(d,(35,890,1565,1030),"NHẬT KÝ","Kết nối • xác nhận lệnh • lỗi • nguồn SIMULATION hoặc SERIAL",title_size=29,size=27)
    im.save(ASSETS/"app_layout.png")


def replace_text(paragraph, value):
    runs = paragraph.runs
    if runs:
        runs[0].text = value
        for r in runs[1:]:
            r.text = ""
    else:
        paragraph.add_run(value)


def field(p, instruction, cache=""):
    run=p.add_run()
    begin=OxmlElement("w:fldChar"); begin.set(qn("w:fldCharType"),"begin")
    text=OxmlElement("w:instrText"); text.set(qn("xml:space"),"preserve"); text.text=instruction
    separate=OxmlElement("w:fldChar"); separate.set(qn("w:fldCharType"),"separate")
    end=OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"),"end")
    run._r.extend([begin,text,separate])
    if cache: p.add_run(cache)
    p.add_run()._r.append(end)


def bookmark(p, name, identifier):
    start=OxmlElement("w:bookmarkStart"); start.set(qn("w:id"),str(identifier)); start.set(qn("w:name"),name)
    end=OxmlElement("w:bookmarkEnd"); end.set(qn("w:id"),str(identifier))
    p._p.insert(0,start); p._p.append(end)


def math_text(value):
    run=OxmlElement('m:r'); t=OxmlElement('m:t'); t.text=value; run.append(t)
    return run


def math_sub(base, sub):
    node=OxmlElement('m:sSub')
    e=OxmlElement('m:e'); e.append(math_text(base))
    s=OxmlElement('m:sub'); s.append(math_text(sub))
    node.extend([e,s]); return node


def math_fraction(numerator, denominator):
    node=OxmlElement('m:f')
    n=OxmlElement('m:num'); n.extend(numerator)
    d=OxmlElement('m:den'); d.extend(denominator)
    node.extend([n,d]); return node


def add_equation(document, name):
    p=document.add_paragraph()
    p.paragraph_format.space_before=Pt(7); p.paragraph_format.space_after=Pt(7)
    p.paragraph_format.keep_together=True
    para=OxmlElement('m:oMathPara'); props=OxmlElement('m:oMathParaPr')
    jc=OxmlElement('m:jc'); jc.set(qn('m:val'),'center'); props.append(jc); para.append(props)
    math=OxmlElement('m:oMath')
    if name=='stop_distance':
        power=OxmlElement('m:sSup'); e=OxmlElement('m:e'); e.append(math_text('v'))
        sup=OxmlElement('m:sup'); sup.append(math_text('2')); power.extend([e,sup])
        math.extend([math_sub('d','stop'),math_text(' ≥ v × '),math_sub('T','delay'),math_text(' + '),
                     math_fraction([power],[math_text('2'),math_sub('a','brake')]),
                     math_text(' + '),math_sub('d','margin')])
    elif name=='differential':
        math.extend([math_text('v = '),math_fraction([math_sub('v','R'),math_text(' + '),math_sub('v','L')],[math_text('2')]),
                     math_text('     ;     ω = '),
                     math_fraction([math_sub('v','R'),math_text(' − '),math_sub('v','L')],[math_text('b')])])
    else: raise ValueError(name)
    para.append(math); p._p.append(para)


def main(config=None):
    config=config or {}
    reference=Path(config.get('reference',TEMPLATE))
    output=Path(config.get('output',OUTPUT))
    content=Path(config.get('content',ROOT/'report/noi_dung_bao_cao.md'))
    config.get('diagrams',diagrams)()
    d=Document(reference)
    source_elements=list(d.element.body)
    # Preserve the current report's cover/front matter, including user edits.
    toc_index=next(i for i,e in enumerate(source_elements)
                   if ''.join(e.xpath('.//w:t/text()')).strip()=='MỤC LỤC')
    for el in source_elements[toc_index+1:-1]:
        d.element.body.remove(el)
    body=d.element.body
    if reference.resolve()==TEMPLATE.resolve():
        source_elements[8].addprevious(source_elements[9])
    replace_text(d.paragraphs[6],config.get('title',"ROBOT AMR DÙNG ESP32\nTRÁNH VẬT CẢN BẰNG SIÊU ÂM QUÉT SERVO\nĐIỀU KHIỂN BẰNG PYTHON QUA ESP-NOW"))
    title=d.paragraphs[6]; title.style=d.styles["Title"]
    title.alignment=WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.line_spacing=1.08
    title.paragraph_format.space_after=Pt(12)
    for r in title.runs:
        r.font.name="Times New Roman"; r.font.size=Pt(15); r.bold=True; r.font.color.rgb=RGBColor(0,0,0)
    for p in d.paragraphs:
        if p.text.startswith("HÀ NỘI"): replace_text(p,"HÀ NỘI 2026")
    # Keep name/ID placeholders exactly as requested by the user.
    cover=d.tables[0]
    if reference.resolve()==TEMPLATE.resolve():
        replace_text(cover.cell(5,1).paragraphs[0],"[Liên kết GitHub bổ sung sau]")
    abstract=config.get('abstract',"Đề tài xây dựng nguyên mẫu robot di động AMR sử dụng ESP32, hai động cơ DC qua driver TB6612FNG và cảm biến siêu âm gắn trên servo. Mục tiêu là điều khiển thủ công, tự tránh vật cản ở tốc độ thấp và giám sát bằng app Python. Phương án truyền thông dùng ESP32 gateway nối USB máy tính để chuyển lệnh và phản hồi qua ESP-NOW. Thuật toán đề xuất dừng khi gặp vật cản, quét nhiều hướng, chọn khoảng trống và quay từng bước trước khi đo lại. App có ARM, STOP, dừng khẩn phần mềm, đồ thị, ghi CSV và mô phỏng lỗi. Phần mềm máy tính đã được xây dựng và kiểm tra tự động; firmware ESP32 và kết quả thử nghiệm trên robot chưa được cung cấp. Báo cáo trình bày thiết kế, giao thức tích hợp và kế hoạch kiểm chứng, chưa khẳng định hiệu quả vận hành của phần cứng. Nguyên mẫu hiện tập trung vào tránh vật cản phản ứng, chưa có định vị, lập bản đồ hoặc dẫn đường tới tọa độ.")
    abs_cell=d.tables[1].cell(1,0)
    replace_text(abs_cell.paragraphs[0],abstract)
    for r in abs_cell.paragraphs[0].runs: r.italic=False; r.font.size=Pt(12); r.font.color.rgb=RGBColor(0,0,0)
    replace_text(d.tables[2].cell(1,0).paragraphs[0],"ESP32; AMR; ESP-NOW; TB6612FNG; siêu âm; servo; Python")
    for r in d.tables[2].cell(1,0).paragraphs[0].runs: r.italic=False; r.font.color.rgb=RGBColor(0,0,0); r.font.size=Pt(12)
    history=d.tables[3]
    values=config.get('history',["V1.0","08/11/2026","Nhóm thực hiện","Thiết kế và app Python; chờ tích hợp firmware và đo robot thật"])
    if config.get('append_history'):
        history._tbl.append(deepcopy(history.rows[-1]._tr))
        history_row=history.rows[-1]
    else:
        history_row=history.rows[1]
        for row in list(history.rows)[2:]: history._tbl.remove(row._tr)
    for cell,value in zip(history_row.cells,values): replace_text(cell.paragraphs[0],value)
    # Keep the short history with the abstract instead of a nearly empty page.
    for br in source_elements[13].findall('.//'+qn('w:br')):
        if br.get(qn('w:type'))=='page': br.getparent().remove(br)
    # Use source typography. Table/caption text uses black to match the printed template.
    for stname in ("Title","Heading 1","Heading 2","Heading 3","Caption"):
        d.styles[stname].font.color.rgb=RGBColor(0,0,0)
    for element in [d.styles['Title'].element, title._p]:
        for border in element.xpath('.//w:pBdr'):
            border.getparent().remove(border)
    for name in ('TOC 1','TOC 2','TOC 3'):
        st=next((s for s in d.styles if s.name.lower()==name.lower()),None)
        if st is None: st=d.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH,builtin=True)
        st.base_style=d.styles['Normal']
        st.font.name='Times New Roman'; st.font.size=Pt(11)
        st.paragraph_format.space_before=Pt(0); st.paragraph_format.space_after=Pt(1)
        st.paragraph_format.line_spacing=1.0
    d.styles["Normal"].paragraph_format.widow_control=True
    for i in range(1,4):
        d.styles[f"Heading {i}"].paragraph_format.keep_with_next=True
    # Source front matter deliberately has page breaks before history and TOC.
    # The TOC slot is its last paragraph.
    toc_p=d.add_paragraph()
    field(toc_p,' TOC \\o "1-3" \\h \\z \\u ',"Mục lục sẽ được cập nhật khi mở Word.")
    toc_p.paragraph_format.page_break_before=False
    captions=[]; table_captions=[]
    counter=1+max([int(e.get(qn('w:id'))) for e in d.element.xpath('.//w:bookmarkStart')]+[0])

    def caption(text, kind):
        nonlocal counter
        p=d.add_paragraph(text,style="Caption")
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before=Pt(5)
        p.paragraph_format.space_after=Pt(8)
        p.paragraph_format.keep_with_next=(kind=="table")
        for r in p.runs: r.font.name="Times New Roman"; r.font.size=Pt(11); r.font.color.rgb=RGBColor(0,0,0)
        name=f"cap_{counter}"; bookmark(p,name,counter); counter+=1
        (table_captions if kind=="table" else captions).append((text,name))
        return p

    def make_table(rows):
        n=len(rows[0]); t=d.add_table(rows=1,cols=n)
        t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
        t.style="Table Grid"
        widths={2:[2.0,4.25],3:[1.1,2.35,2.8],4:[1.05,1.8,2.4,1.0]}.get(n,[6.25/n]*n)
        if 'STBY' in rows[0]: widths=[1.3,.6,1.6,2.75]
        if n==4 and rows[0][1].startswith('PWM logic'): widths=[1.45,.9,.9,3.0]
        # Match source body content width, rather than adopting a new page preset.
        available=(d.sections[-1].page_width-d.sections[-1].left_margin-d.sections[-1].right_margin)/914400
        factor=available/sum(widths); widths=[x*factor for x in widths]
        for c,w in zip(t.columns,widths): c.width=Inches(w)
        for row_i,data in enumerate(rows):
            cells=t.rows[0].cells if row_i==0 else t.add_row().cells
            for col,(cell,value) in enumerate(zip(cells,data)):
                cell.width=Inches(widths[col]); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                p=cell.paragraphs[0]; p.text=value
                p.paragraph_format.space_before=Pt(3); p.paragraph_format.space_after=Pt(3)
                p.paragraph_format.line_spacing=1.08
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER if row_i==0 or (col==0 and n>=3 and len(value)<14) else WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    r.font.name="Times New Roman"; r.font.size=Pt(11); r.bold=(row_i==0); r.font.color.rgb=RGBColor(0,0,0)
                tcpr=cell._tc.get_or_add_tcPr()
                margins=OxmlElement("w:tcMar")
                for edge,val in [("top",60),("bottom",60),("left",90),("right",90)]:
                    e=OxmlElement("w:"+edge); e.set(qn("w:w"),str(val)); e.set(qn("w:type"),"dxa"); margins.append(e)
                tcpr.append(margins)
                if row_i==0:
                    shade=OxmlElement("w:shd"); shade.set(qn("w:fill"),"F2F2F2"); tcpr.append(shade)
            trpr=t.rows[-1]._tr.get_or_add_trPr()
            nosplit=OxmlElement("w:cantSplit"); trpr.append(nosplit)
            if row_i==0:
                repeat=OxmlElement("w:tblHeader"); trpr.append(repeat)
        borders=OxmlElement("w:tblBorders")
        for edge in ("top","left","bottom","right","insideH","insideV"):
            b=OxmlElement("w:"+edge); b.set(qn("w:val"),"single"); b.set(qn("w:sz"),"4"); b.set(qn("w:color"),"B6B6B6"); borders.append(b)
        t._tbl.tblPr.append(borders)
        p=d.add_paragraph(); p.paragraph_format.space_after=Pt(2); p.paragraph_format.space_before=Pt(0); p.paragraph_format.line_spacing=0.4

    lines=content.read_text(encoding="utf-8").splitlines()
    i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line: i+=1; continue
        if line.startswith("#"):
            level=len(line)-len(line.lstrip("#")); text=line[level:].strip()
            p=d.add_paragraph(text,style=f"Heading {min(level,3)}")
            if level==1 and (text.startswith('1. ') or text.startswith('Tài liệu') or text.startswith('Phụ lục')):
                p.paragraph_format.page_break_before=True
            i+=1
        elif line.startswith("@table "):
            caption(line[7:],"table"); i+=1
        elif line.startswith('@equation '):
            add_equation(d,line.split()[1]); i+=1
        elif line.startswith("|"):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith("|"):
                cells=[x.strip() for x in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?",c) for c in cells): rows.append(cells)
                i+=1
            make_table(rows)
        elif line.startswith("!["):
            m=re.fullmatch(r"!\[(.+)\]\((.+)\)",line)
            p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next=True
            p.paragraph_format.space_before=Pt(7); p.paragraph_format.space_after=Pt(0)
            picture=p.add_run().add_picture(str(ASSETS/m[2]),width=Inches(6.15))
            picture._inline.docPr.set("descr",m[1])
            caption(m[1],"figure"); i+=1
        elif line.startswith("```"):
            i+=1; code=[]
            while i<len(lines) and not lines[i].startswith("```"):
                code.append(lines[i]); i+=1
            for code_line in code:
                # Break long JSON at comma boundaries so all fields remain readable.
                pieces=[code_line]
                if len(code_line)>85:
                    pieces=[]; current=""
                    for part in re.split(r"(?<=,)",code_line):
                        if len(current+part)>85 and current: pieces.append(current); current="  "+part
                        else: current+=part
                    if current: pieces.append(current)
                for piece in pieces:
                    p=d.add_paragraph(piece)
                    p.paragraph_format.space_after=Pt(2); p.paragraph_format.line_spacing=1.05
                    for r in p.runs: r.font.name="Consolas"; r.font.size=Pt(9.5)
            i+=1
        else:
            parts=[line]; i+=1
            while i<len(lines) and lines[i].strip() and not re.match(r"^(#|\||!\[|@table|@equation|```)",lines[i].strip()):
                parts.append(lines[i].strip()); i+=1
            p=d.add_paragraph(" ".join(parts))
            p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
            if re.match(r'^\[\d+\]',p.text):
                p.alignment=WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.left_indent=Inches(.24)
                p.paragraph_format.first_line_indent=Inches(-.24)
                p.paragraph_format.space_after=Pt(9)
            p.paragraph_format.keep_together=False
    # A spacer after a final full-page table can spill onto a blank page.
    # The following heading already provides the required paragraph after it.
    trailing=d.paragraphs[-1]
    previous=trailing._p.getprevious()
    if not trailing.text and previous is not None and previous.tag==qn('w:tbl'):
        trailing._p.getparent().remove(trailing._p)
    p=d.add_paragraph("MỤC LỤC HÌNH ẢNH",style="Heading 1"); p.paragraph_format.page_break_before=True
    for text,name in captions:
        p=d.add_paragraph(text+"\t"); p.paragraph_format.tab_stops.add_tab_stop(Inches(6.1),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS)
        field(p,f" PAGEREF {name} \\h ","0")
    p=d.add_paragraph("DANH MỤC BẢNG BIỂU",style="Heading 1"); p.paragraph_format.space_before=Pt(18)
    for text,name in table_captions:
        p=d.add_paragraph(text+"\t")
        p.paragraph_format.tab_stops.add_tab_stop(Inches(6.1),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS)
        field(p,f" PAGEREF {name} \\h ","0")
    update=OxmlElement("w:updateFields"); update.set(qn("w:val"),"true"); d.settings.element.append(update)
    d.core_properties.title="Robot AMR dùng ESP32 tránh vật cản và điều khiển bằng Python qua ESP-NOW"
    d.core_properties.subject="Báo cáo hệ thống nhúng và ứng dụng điều khiển"
    d.core_properties.author="Nhóm thực hiện"
    d.core_properties.last_modified_by="Nhóm thực hiện"
    d.core_properties.comments=""
    d.core_properties.keywords="ESP32; AMR; ESP-NOW; TB6612FNG; Python"
    d.save(output)
    print(json.dumps({"output":str(output),"paragraphs":len(d.paragraphs),"tables":len(d.tables),"figures":len(captions),"abstract_words":len(abstract.split()),"source_unchanged_sha256":hashlib.sha256(reference.read_bytes()).hexdigest()},ensure_ascii=False))


if __name__=="__main__":
    main()
