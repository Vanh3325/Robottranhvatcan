"""Add automatic captions to the user's edited report, preserving its images."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import zipfile

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.text.paragraph import Paragraph

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'.tools/photos_source.docx'
OUTPUT=ROOT/'Bao_cao_AMR_ESP32_da_danh_so_anh_va_muc_luc.docx'

FIGURES={
    'image2.png': 'Kiến trúc bản tự hành và phần mở rộng app ESP-NOW',
    'image3.png': 'Sơ đồ khối phần cứng và phân phối nguồn của robot',
    'image4.png': 'Robot AMR sau khi lắp ráp với ESP32, TB6612 và cụm siêu âm trên servo',
    'image5.png': 'Sơ đồ nối khối theo GPIO thực tế của firmware',
    'image6.png': 'Lưu đồ tự động theo setup(), loop() và avoidObstacle()',
    'image7.png': 'Ảnh chụp giao diện app Python ở trạng thái chưa kết nối',
    'image8.png': 'Sơ đồ bố trí app Python dành cho phần mở rộng điều khiển',
}
OLD_NUMBERS={1:1,2:4,3:5,4:7}


def add_field(p, instruction, cached=''):
    begin=OxmlElement('w:fldChar'); begin.set(qn('w:fldCharType'),'begin')
    instr=OxmlElement('w:instrText'); instr.set(qn('xml:space'),'preserve'); instr.text=' '+instruction+' '
    separate=OxmlElement('w:fldChar'); separate.set(qn('w:fldCharType'),'separate')
    end=OxmlElement('w:fldChar'); end.set(qn('w:fldCharType'),'end')
    p.add_run()._r.append(begin)
    p.add_run()._r.append(instr)
    p.add_run()._r.append(separate)
    if cached: p.add_run(cached)
    p.add_run()._r.append(end)


def remove_runs(p):
    # Keep paragraph formatting and existing bookmarks used by references.
    for child in list(p._p):
        if child.tag not in (qn('w:pPr'),qn('w:bookmarkStart'),qn('w:bookmarkEnd')):
            p._p.remove(child)


def insert_after(p):
    element=OxmlElement('w:p'); p._p.addnext(element)
    return Paragraph(element,p._parent)


def as_inline(drawing):
    for anchor in list(drawing):
        if anchor.tag!=qn('wp:anchor'): continue
        anchor.tag=qn('wp:inline')
        keep_attrs={'distT','distB','distL','distR'}
        for attr in list(anchor.attrib):
            if attr not in keep_attrs: del anchor.attrib[attr]
        for key in ('distT','distB','distL','distR'): anchor.set(key,'0')
        allowed={qn('wp:extent'),qn('wp:effectExtent'),qn('wp:docPr'),
                 qn('wp:cNvGraphicFramePr'),qn('a:graphic')}
        for child in list(anchor):
            if child.tag not in allowed: anchor.remove(child)


def main():
    d=Document(SOURCE)
    body=d.element.body
    max_id=max([int(x.get(qn('w:id'))) for x in d.element.xpath('.//w:bookmarkStart')]+[0])
    next_id=max_id+1

    def replace_cell_text(cell,text):
        p=cell.paragraphs[0]
        if not p.runs: p.add_run(text)
        else:
            p.runs[0].text=text
            for run in p.runs[1:]: run.text=''

    def bookmark_start(p,name):
        nonlocal next_id
        identifier=next_id; next_id+=1
        start=OxmlElement('w:bookmarkStart'); start.set(qn('w:id'),str(identifier)); start.set(qn('w:name'),name)
        p._p.append(start)
        return identifier

    def bookmark_end(p,identifier):
        end=OxmlElement('w:bookmarkEnd'); end.set(qn('w:id'),str(identifier)); p._p.append(end)

    # Discover content figures in reading order; exclude the university logo.
    figure_nodes=[]
    for element in list(body):
        if element.tag!=qn('w:p'): continue
        for drawing in element.xpath('.//w:drawing'):
            targets=[]
            for blip in drawing.xpath('.//a:blip'):
                rid=blip.get(qn('r:embed'))
                if rid in d.part.rels:
                    name=Path(d.part.rels[rid].target_ref).name
                    if name in FIGURES: targets.append(name)
            if targets:
                assert len(targets)==1
                figure_nodes.append((element,drawing,targets[0]))
    assert [name for _,_,name in figure_nodes]==list(FIGURES)

    captions=[]
    for number,(element,drawing,name) in enumerate(figure_nodes,1):
        paragraph=Paragraph(element,d._body)
        # User pictures anchored to a heading/text paragraph get their own line.
        if paragraph.text.strip():
            image_paragraph=insert_after(paragraph)
            image_paragraph.style=d.styles['Normal']
            source_run=drawing.getparent()
            run=image_paragraph.add_run()
            if source_run.find(qn('w:rPr')) is not None:
                run._r.append(deepcopy(source_run.find(qn('w:rPr'))))
            source_run.remove(drawing)
            run._r.append(drawing)
        else:
            image_paragraph=paragraph
            image_paragraph.style=d.styles['Normal']
        as_inline(drawing)
        image_paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
        image_paragraph.paragraph_format.keep_with_next=True
        image_paragraph.paragraph_format.keep_together=True
        image_paragraph.paragraph_format.space_before=Pt(7)
        image_paragraph.paragraph_format.space_after=Pt(0)
        image_paragraph.paragraph_format.line_spacing=1.0

        following=image_paragraph._p.getnext()
        if (following is not None and following.tag==qn('w:p')
                and re.match(r'^Hình\s+\d+[.]', ''.join(following.xpath('.//w:t/text()')).strip())):
            caption=Paragraph(following,d._body)
        else:
            caption=insert_after(image_paragraph)
        remove_runs(caption)
        caption.style=d.styles['Caption']
        caption.alignment=WD_ALIGN_PARAGRAPH.CENTER
        pf=caption.paragraph_format
        pf.keep_together=True; pf.keep_with_next=False
        pf.space_before=Pt(5); pf.space_after=Pt(8); pf.line_spacing=1.0
        caption.add_run('Hình ')
        identifier=bookmark_start(caption,f'amr_figure_number_{number:02d}')
        add_field(caption,r'SEQ Hinh \* ARABIC',str(number))
        bookmark_end(caption,identifier)
        caption.add_run('. '+FIGURES[name])
        for run in caption.runs:
            run.font.name='Times New Roman'; run.font.size=Pt(11)
            run.bold=True; run.italic=False; run.font.color.rgb=RGBColor(0,0,0)
        for prop in drawing.xpath('.//wp:docPr'):
            prop.set('descr',FIGURES[name])
        captions.append({'number':number,'image':name,'caption':FIGURES[name]})

    # Update in-text figure references, excluding captions and old figure index.
    index_heading=next(p for p in d.paragraphs if p.text.strip()=='MỤC LỤC HÌNH ẢNH' and p.style.name=='Heading 1')
    before_index=True
    for p in d.paragraphs:
        if p._p is index_heading._p: before_index=False
        if not before_index or p.style.name=='Caption' or p.style.name.lower().startswith('toc'): continue
        text=p.text
        matches=list(re.finditer(r'Hình\s+([1-4])\b',text))
        if not matches or p._p.xpath('.//w:drawing'): continue
        remove_runs(p)
        pos=0
        for match in matches:
            p.add_run(text[pos:match.start()]+'Hình ')
            target=OLD_NUMBERS[int(match.group(1))]
            add_field(p,f'REF amr_figure_number_{target:02d} \\h',str(target))
            pos=match.end()
        p.add_run(text[pos:])

    # Replace the stale manual figure list with an automatic table of figures.
    next_table_heading=next(p for p in d.paragraphs if p.text.strip()=='DANH MỤC BẢNG BIỂU' and p.style.name=='Heading 1')
    current=index_heading._p.getnext()
    while current is not None and current is not next_table_heading._p:
        nxt=current.getnext(); body.remove(current); current=nxt
    index_paragraph=insert_after(index_heading)
    index_paragraph.style=d.styles['Normal']
    add_field(index_paragraph,r'TOC \h \z \c "Hinh"','Danh mục hình ảnh')
    style=next((s for s in d.styles if s.name.lower()=='table of figures'),None)
    if style is None: style=d.styles.add_style('Table of Figures',WD_STYLE_TYPE.PARAGRAPH,builtin=True)
    style.base_style=d.styles['Normal']
    style.font.name='Times New Roman'; style.font.size=Pt(12)
    style.paragraph_format.space_before=Pt(0); style.paragraph_format.space_after=Pt(3)
    style.paragraph_format.line_spacing=1.0
    style.paragraph_format.tab_stops.add_tab_stop(Inches(6.1),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS)

    # Related evidence notes should reflect the pictures now present.
    for p in d.paragraphs:
        if 'Mức xác nhận là chức năng; chưa có dữ liệu số, ảnh hoặc log gốc đính kèm' in p.text:
            updated=p.text.replace('chưa có dữ liệu số, ảnh hoặc log gốc đính kèm','chưa có bộ dữ liệu đo định lượng hoặc log gốc đính kèm')
            formatting=deepcopy(p.runs[0]._r.find(qn('w:rPr'))) if p.runs and p.runs[0]._r.find(qn('w:rPr')) is not None else None
            remove_runs(p)
            run=p.add_run(updated)
            if formatting is not None: run._r.insert(0,formatting)
    for table in d.tables:
        for row in table.rows:
            if row.cells[0].text.strip()=='Ảnh, CSV và video':
                replace_cell_text(row.cells[1],'Đã bổ sung ảnh mô hình và giao diện app; CSV/video chưa đính kèm')
                replace_cell_text(row.cells[2],'Ảnh minh họa tại phần cứng và app; bổ sung dữ liệu thử nghiệm khi có')
            elif row.cells[0].text.strip()=='Ảnh và đường dẫn video':
                replace_cell_text(row.cells[1],'Đã bổ sung ảnh mô hình/app; bổ sung đường dẫn video khi có')

    settings=d.settings.element
    for tag in ('w:updateFields','w:doNotAutoCompressPictures'):
        node=settings.find(qn(tag))
        if node is None: node=OxmlElement(tag); settings.append(node)
        node.set(qn('w:val'),'true')
    d.save(OUTPUT)

    # Verify the original picture payloads and the user's component edits survived.
    def media_hashes(path):
        with zipfile.ZipFile(path) as z:
            return {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
    assert media_hashes(SOURCE)==media_hashes(OUTPUT)
    check=Document(OUTPUT)
    assert len(check.inline_shapes)==8
    assert len(check.element.xpath('.//wp:anchor'))==0
    assert len([p for p in check.paragraphs if p.style.name=='Caption' and p.text.startswith('Hình ')])==7
    assert 'MG90' in '\n'.join(c.text for t in check.tables for r in t.rows for c in r.cells)
    manifest={'source':str(SOURCE),'output':str(OUTPUT),'figures':captions,
              'media_payloads_unchanged':True,'user_component_edits_preserved':True}
    (ROOT/'tmp/caption-audit/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(manifest,ensure_ascii=False))


if __name__=='__main__': main()
