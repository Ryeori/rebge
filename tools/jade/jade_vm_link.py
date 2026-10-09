"""140b44150 source-to-runtime field linking; no VM execution."""
def link_record(record, category_ids, selector_ids):
    source_category = record['dispatch_u8']
    if source_category == 31:
        return {**record, 'terminal': True}
    if source_category not in category_ids:
        raise ValueError('Unknown source category')
    selector = record['selector_u16']
    if selector not in selector_ids:
        raise ValueError('Unknown source selector')
    result = {**record, 'runtime_category': category_ids[source_category],
              'runtime_selector': selector_ids[selector]}
    if source_category == 1 and selector in (0x27, 0x28, 0x2A, 0x2B):
        key = record['value_i32'] & 0xFFFFFFFF
        if key == 0 or selector == 0x28 and key in (1, 2):
            result['resolved_reference_u64'] = key
        else:
            result['unresolved'] = 'Literal pointer resolution140b40280 required'
    return result
