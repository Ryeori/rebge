"""Bounded typed literal/context interpreter, without guessed game calls."""
import struct


class UnsupportedVM(ValueError):
    pass


class VMState:
    def __init__(self, *, context_sentinel, objects, sentinel_references=None, default_actor=None, default_component=None):
        self.stack = []
        self.context_sentinel = context_sentinel
        self.objects = objects
        self.sentinel_references = sentinel_references or {}
        self.object_context = None
        self.component_context = None
        self.default_actor, self.default_component = default_actor, default_component

    def execute(self, record):
        if record.get('terminal'):
            return False
        if 'unresolved' in record:
            raise UnsupportedVM(record['unresolved'])
        category, selector = record['runtime_category'], record['runtime_selector']
        if category == 0:
            bits = record['value_i32'] & 0xFFFFFFFF
            if selector == 1:
                value = struct.unpack('<i', struct.pack('<I', bits))[0]
            elif selector == 2:
                #1411dbb20 copies bits; it does not numerically cast the source int.
                value = struct.unpack('<f', struct.pack('<I', bits))[0]
            elif selector == 6:
                if 'resolved_reference_u64' not in record:
                    raise UnsupportedVM('Unresolved object reference')
                value = record['resolved_reference_u64']
                if value in (1, 2):
                    if value not in self.sentinel_references:
                        raise UnsupportedVM('Missing runtime sentinel reference')
                    value = self.sentinel_references[value]
            else:
                raise UnsupportedVM(f'Literal type {selector} unsupported')
            self.stack.append({'type': selector, 'value': value})
        elif category == 2 and selector == 16:
            #1414ceaa0 pops z,y,x, converts scalar tags1/2 and pushes float3 tag3.
            #Third type check: DWORD151c405d6 xor08ec834a ==2, verified PE bytes.
            if len(self.stack) < 3:
                raise ValueError('Vector constructor stack underflow')
            items = self.stack[-3:]
            if any(item['type'] not in (1, 2) for item in items):
                raise UnsupportedVM('Vector constructor scalar conversion unavailable')
            values = [struct.unpack('<f', struct.pack('<f', float(item['value'])))[0] for item in items]
            del self.stack[-3:]
            self.stack.append({'type': 3, 'value': values})
        elif category == 2 and selector == 248:
            #140b39180 consumes set mask then clear mask; operates on old context.
            if len(self.stack) < 2:
                raise ValueError('Component mask operator stack underflow')
            if any(item['type'] != 1 for item in self.stack[-2:]):
                raise UnsupportedVM('Float-to-mask conversion helper unresolved')
            obj = self.objects.get(self.object_context)
            if obj is None or 'flags_u16_50' not in obj:
                raise UnsupportedVM('Component flags missing from runtime snapshot')
            set_mask, clear_mask = (item['value'] & 0xFFFF for item in self.stack[-2:])
            obj['flags_u16_50'] = (obj['flags_u16_50'] & ~clear_mask | set_mask) & 0xFFFF
            del self.stack[-2:]
            self.object_context, self.component_context = self.default_actor, self.default_component
        elif category == 1 and selector == 6:
            if not self.stack:
                raise ValueError('Context operator stack underflow')
            item = self.stack[-1]
            if item['type'] != 6:
                raise UnsupportedVM('Context operator requires reference value')
            value = item['value']
            if value == self.context_sentinel:
                obj, component = 0, self.context_sentinel
            else:
                if value not in self.objects:
                    raise UnsupportedVM('Context object unavailable in runtime snapshot')
                obj, component = value, self.objects[value].get('component_context', 0)
            self.stack.pop()
            self.object_context, self.component_context = obj, component
        else:
            raise UnsupportedVM(f'Runtime handler {category}:{selector} unsupported')
        return True
