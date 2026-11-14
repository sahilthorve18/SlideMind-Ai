"""Scene -> native, editable PowerPoint. Charts are real PowerPoint charts, diagrams are real shapes,
each block is grouped and animated (fade/wipe entrance), and slides carry a transition."""
import io
import logging

from lxml import etree
from pptx import Presentation as Pptx
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from . import images

log = logging.getLogger(__name__)
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
ALIGN = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}
VALIGN = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}


def _rgb(h):
    return RGBColor.from_string(h.upper())


def _no_effects(sp):
    st = sp._element.find(qn("p:style"))
    if st is not None:  # drop theme style refs: no inherited shadows/outlines, only what we set explicitly
        sp._element.remove(st)
    spPr = sp._element.spPr
    if spPr.find(qn("a:effectLst")) is None:
        etree.SubElement(spPr, qn("a:effectLst"))


def _set_alpha(shape, alpha):
    if alpha is None or alpha >= 1:
        return
    clr = shape._element.spPr.find(qn("a:solidFill"))
    if clr is not None:
        for c in clr:
            a = etree.SubElement(c, qn("a:alpha"))
            a.set("val", str(int(alpha * 100000)))


def _style(shape, p):
    if p.get("fill"):
        shape.fill.solid()
        shape.fill.fore_color.rgb = _rgb(p["fill"])
        _set_alpha(shape, p.get("alpha"))
    else:
        shape.fill.background()
    if p.get("line"):
        shape.line.color.rgb = _rgb(p["line"])
        shape.line.width = Pt(p.get("lw", 1))
    else:
        shape.line.fill.background()
    _no_effects(shape)


def _draw(shapes, p, ids):
    k = p["k"]
    if k in ("rect", "ellipse"):
        r = p.get("r", 0) if k == "rect" else 0
        kind = MSO_SHAPE.OVAL if k == "ellipse" else (MSO_SHAPE.ROUNDED_RECTANGLE if r > 0.001 else MSO_SHAPE.RECTANGLE)
        sh = shapes.add_shape(kind, Inches(p["x"]), Inches(p["y"]), Inches(p["w"]), Inches(p["h"]))
        if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = min(0.5, r / max(min(p["w"], p["h"]), 0.01))
        _style(sh, p)
        sh.text_frame.text = ""
        ids.append(sh.shape_id)
    elif k == "line":
        ln = shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(p["x1"]), Inches(p["y1"]), Inches(p["x2"]), Inches(p["y2"]))
        ln.line.color.rgb = _rgb(p["color"])
        ln.line.width = Pt(p.get("lw", 1.5))
        if p.get("dash"):
            ln.line.dash_style = MSO_LINE.DASH
        if p.get("arrow"):
            lnel = ln.line._get_or_add_ln()
            te = etree.SubElement(lnel, qn("a:tailEnd"))
            te.set("type", "triangle")
            te.set("w", "med")
            te.set("len", "med")
        st = ln._element.find(qn("p:style"))
        if st is not None:
            ln._element.remove(st)
        ids.append(ln.shape_id)
    elif k == "text":
        tb = shapes.add_textbox(Inches(p["x"]), Inches(p["y"]), Inches(p["w"]), Inches(p["h"]))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = VALIGN.get(p.get("valign", "t"), MSO_ANCHOR.TOP)
        from pptx.enum.text import MSO_AUTO_SIZE
        tf.auto_size = MSO_AUTO_SIZE.NONE
        para = tf.paragraphs[0]
        para.alignment = ALIGN.get(p.get("align", "l"), PP_ALIGN.LEFT)
        run = para.add_run()
        run.text = p["text"]
        f = run.font
        f.size = Pt(p["size"])
        f.bold = bool(p.get("bold"))
        f.italic = bool(p.get("italic"))
        f.name = p.get("font") or "Calibri"
        f.color.rgb = _rgb(p["color"])
        ids.append(tb.shape_id)
    elif k == "image":
        raw = images.image_bytes(p.get("src"))
        conv = images.to_png_or_jpeg(raw) if raw else None
        if not conv:
            return  # no fallback image: leave the area empty, the layout still stands
        data, iw, ih = conv
        x, y, w, h = p["x"], p["y"], p["w"], p["h"]
        pic = shapes.add_picture(io.BytesIO(data), Inches(x), Inches(y), Inches(w), Inches(h))
        ar_box, ar_img = w / h, iw / ih
        if ar_img > ar_box:
            cut = (1 - ar_box / ar_img) / 2
            pic.crop_left = pic.crop_right = cut
        else:
            cut = (1 - ar_img / ar_box) / 2
            pic.crop_top = pic.crop_bottom = cut
        if p.get("r", 0) > 0.001:
            pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
            av = pic._element.spPr.find(qn("a:prstGeom")).find(qn("a:avLst"))
            if av is None:
                av = etree.SubElement(pic._element.spPr.find(qn("a:prstGeom")), qn("a:avLst"))
            gd = etree.SubElement(av, qn("a:gd"))
            gd.set("name", "adj")
            gd.set("fmla", f"val {int(min(0.5, p['r'] / min(w, h)) * 100000)}")
        if p.get("line"):
            pic.line.color.rgb = _rgb(p["line"])
            pic.line.width = Pt(0.75)
        if p.get("alt"):
            pic._element.nvPicPr.cNvPr.set("descr", p["alt"])
        ids.append(pic.shape_id)


def _chart(slide, p):
    cd = CategoryChartData()
    cd.categories = p["labels"]
    for s in p["series"]:
        cd.add_series(s["name"] or "Series", s["values"])
    kind = {"bar": XL_CHART_TYPE.COLUMN_CLUSTERED, "hbar": XL_CHART_TYPE.BAR_CLUSTERED, "line": XL_CHART_TYPE.LINE_MARKERS,
            "pie": XL_CHART_TYPE.PIE, "donut": XL_CHART_TYPE.DOUGHNUT}[p["kind"]]
    gf = slide.shapes.add_chart(kind, Inches(p["x"]), Inches(p["y"]), Inches(p["w"]), Inches(p["h"]), cd)
    ch = gf.chart
    ch.font.size = Pt(p.get("size", 14))
    ch.font.color.rgb = _rgb(p["fg"])
    ch.has_title = False
    multi = len(p["series"]) > 1
    pie = p["kind"] in ("pie", "donut")
    ch.has_legend = multi or pie
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM if not pie else XL_LEGEND_POSITION.RIGHT
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(14)
        ch.legend.font.color.rgb = _rgb(p["fg"])
    plot = ch.plots[0]
    if pie:
        for i, pt in enumerate(p["series"][0]["values"]):
            point = plot.series[0].points[i]
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = _rgb(p["colors"][i % len(p["colors"])])
            point.format.line.color.rgb = _rgb(p["bg"])
        plot.has_data_labels = True
        plot.data_labels.font.size = Pt(14)
        plot.data_labels.font.bold = True
        plot.data_labels.number_format = "0.#"
        plot.data_labels.number_format_is_linked = False
    else:
        for i, s in enumerate(plot.series):
            col = _rgb(p["colors"][i % len(p["colors"])])
            if p["kind"] == "line":
                s.format.line.color.rgb = col
                s.format.line.width = Pt(3)
                s.smooth = False
                s.marker.format.fill.solid()
                s.marker.format.fill.fore_color.rgb = col
            else:
                s.format.fill.solid()
                s.format.fill.fore_color.rgb = col
        if p["kind"] != "line":
            plot.gap_width = 70
        if not multi:
            plot.has_data_labels = True
            plot.data_labels.font.size = Pt(14)
            plot.data_labels.font.color.rgb = _rgb(p["fg"])
            plot.data_labels.number_format = '0.#' + ((' "' + p["unit"] + '"') if p.get("unit") else "")
            plot.data_labels.number_format_is_linked = False
        va = ch.value_axis
        va.major_gridlines.format.line.color.rgb = _rgb(p["grid"])
        va.format.line.fill.background()
        va.tick_labels.font.size = Pt(12)
        ch.category_axis.tick_labels.font.size = Pt(13)
        ch.category_axis.format.line.color.rgb = _rgb(p["grid"])
    return gf.shape_id


def _fx(spid, cid, node, entrance, delay=0):
    if entrance == "wipe":
        pid, sub, filt = 22, 8, "wipe(left)"
    else:
        pid, sub, filt = 10, 0, "fade"
    return (
        f'<p:par><p:cTn id="{cid}" presetID="{pid}" presetClass="entr" presetSubtype="{sub}" fill="hold" nodeType="{node}">'
        f'<p:stCondLst><p:cond delay="{delay}"/></p:stCondLst><p:childTnLst>'
        f'<p:set><p:cBhvr><p:cTn id="{cid + 1}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
        f'<p:to><p:strVal val="visible"/></p:to></p:set>'
        f'<p:animEffect transition="in" filter="{filt}"><p:cBhvr><p:cTn id="{cid + 2}" dur="450"/>'
        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect></p:childTnLst></p:cTn></p:par>'
    )


def _add_animation(slide, blocks_ids, entrance):
    """blocks_ids: list of lists of shape ids. Each block fades/wipes in after the previous one, automatically."""
    if not blocks_ids:
        return
    cid = [3]

    def nid(n=3):
        v = cid[0]
        cid[0] += n
        return v

    inner = ""
    t = 0
    for ids in blocks_ids:
        eid_cn = nid(1)
        effects = ""
        for j, sid in enumerate(ids):
            effects += _fx(sid, nid(3), "afterEffect" if j == 0 else "withEffect", entrance)
        inner += (f'<p:par><p:cTn id="{eid_cn}" fill="hold"><p:stCondLst><p:cond delay="{t}"/></p:stCondLst>'
                  f'<p:childTnLst>{effects}</p:childTnLst></p:cTn></p:par>')
        t += 650
    xml = (
        f'<p:timing xmlns:p="{NS_P}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        f'<p:par><p:cTn id="{nid(1)}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
        f'<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>{inner}</p:childTnLst></p:cTn></p:par>'
        f'</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        f'<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
        f'</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')
    slide._element.append(etree.fromstring(xml))


def _transition(slide, kind):
    inner = {"fade": "<p:fade/>", "push": '<p:push dir="l"/>', "wipe": '<p:wipe dir="l"/>'}.get(kind)
    if not inner:
        return
    xml = f'<p:transition xmlns:p="{NS_P}" spd="med">{inner}</p:transition>'
    slide._element.append(etree.fromstring(xml))


def scenes_to_pptx(scenes: list[dict], title: str, animations: bool = True) -> bytes:
    prs = Pptx()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    prs.core_properties.title = title[:200]
    blank = prs.slide_layouts[6]
    for sc in scenes:
        s = prs.slides.add_slide(blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = _rgb(sc["bg"])
        groups: dict[int, list] = {}
        for p in sc["items"]:
            groups.setdefault(p.get("g", 0), []).append(p)
        anim_blocks = []
        for g in sorted(groups):
            items = groups[g]
            animated = 1 <= g < 90
            ids = []
            charts = [p for p in items if p["k"] == "chart"]
            drawn = [p for p in items if p["k"] != "chart"]
            if animated and len(drawn) > 1:
                grp = s.shapes.add_group_shape()
                for p in drawn:
                    _draw(grp.shapes, p, [])
                ids.append(grp.shape_id)
            else:
                for p in drawn:
                    _draw(s.shapes, p, ids)
            for p in charts:
                ids.append(_chart(s, p))
            if animated and ids:
                anim_blocks.append(ids)
        if sc.get("notes"):
            s.notes_slide.notes_text_frame.text = sc["notes"]
        _transition(s, sc.get("transition"))
        if animations:
            _add_animation(s, anim_blocks, sc.get("entrance", "fade"))
    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()
