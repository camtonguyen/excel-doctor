from lxml import etree


def ensure_xf(root: etree._Element, ns: str, base_xf_index: int, num_fmt_code: str) -> int:
    """
    Safely adds or reuses a cell format (xf) with the given number format code,
    without mutating the original xf (which would wreck sibling cells).
    """
    # 1. Resolve or create numFmtId
    num_fmts = root.find(f"{ns}numFmts")
    if num_fmts is None:
        # Some simple Excel files don't have a numFmts block at all. We might need to insert it.
        # It must go before fonts, fills, borders, cellStyleXfs, cellXfs etc. according to schema.
        # For simplicity, we just insert it at the beginning.
        num_fmts = etree.Element(f"{ns}numFmts", count="0")
        root.insert(0, num_fmts)

    num_fmt_id = None
    max_id = 163
    for nf in num_fmts.findall(f"{ns}numFmt"):
        fmt_code = nf.get("formatCode")
        nf_id = int(nf.get("numFmtId", "0"))
        if fmt_code == num_fmt_code:
            num_fmt_id = nf_id
            break
        max_id = max(max_id, nf_id)
            
    if num_fmt_id is None:
        num_fmt_id = max_id + 1
        new_nf = etree.SubElement(num_fmts, f"{ns}numFmt")
        new_nf.set("numFmtId", str(num_fmt_id))
        new_nf.set("formatCode", num_fmt_code)
        
        # update count
        count = int(num_fmts.get("count", "0"))
        num_fmts.set("count", str(count + 1))

    # 2. Clone the base xf
    cell_xfs = root.find(f"{ns}cellXfs")
    if cell_xfs is None:
        return 0 # Fallback if styles.xml is completely malformed

    xfs = cell_xfs.findall(f"{ns}xf")
    if 0 <= base_xf_index < len(xfs):
        base_xf = xfs[base_xf_index]
    else:
        # Fallback to the first xf if out of bounds
        base_xf = xfs[0] if xfs else etree.Element(f"{ns}xf")
        
    import copy
    new_xf = copy.deepcopy(base_xf)
    new_xf.set("numFmtId", str(num_fmt_id))
    new_xf.set("applyNumberFormat", "1")

    # 3. Deduplicate
    def elements_equal(e1, e2):
        if e1.tag != e2.tag: return False
        if e1.text != e2.text: return False
        if e1.attrib != e2.attrib: return False
        if len(e1) != len(e2): return False
        return all(elements_equal(c1, c2) for c1, c2 in zip(e1, e2))

    for i, existing_xf in enumerate(xfs):
        if elements_equal(existing_xf, new_xf):
            return i

    # 4. Append and return new index
    cell_xfs.append(new_xf)
    
    count = int(cell_xfs.get("count", "0"))
    cell_xfs.set("count", str(count + 1))
    
    return len(xfs)
