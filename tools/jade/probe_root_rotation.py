"""Explicit primary/transition reference bases vs saved slot0; no fitting."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature
from probe_transition_pose import channels
from jade_pose import rotation_matrix
from jade_target_hierarchy import raw_affine_product, IDENTITY
from jade_tracking_local import inverse_no_scale
from jade_matrix_quaternion import matrix_quaternion
from jade_pose_blend import blend_rotation
from project_paths import ASSET_ROOT, report_path


def referenced_basis(rotation, reference, reference_flags, actor, actor_flags):
    inverse, flags = inverse_no_scale(actor, actor_flags)
    relative, relative_flags = raw_affine_product(reference, inverse, reference_flags, flags)
    local = rotation_matrix(rotation)
    if relative_flags & 0x38:
        raise ValueError('Scale/alternate reference unsupported')
    return raw_affine_product(local, relative, 4, relative_flags)[0] if relative_flags & 0x3c else local


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sequence', type=Path)
    args = parser.parse_args()
    raw = args.sequence.read_bytes()
    sources = {}
    for path in sorted((ASSET_ROOT / 'animations/sally/local-samples').glob('*.json')):
        source = json.loads(path.read_text())
        sources.setdefault(json.dumps(signature(source['tracks'])), []).append((path.stem, source))
    cases, skipped = [], []
    for sample in json.loads(raw)['samples']:
        reasons = rejection_reasons(sample)
        if reasons:
            skipped.append(dict(sample=sample['index'], reasons=reasons))
            continue
        try:
            if not sample.get('actor_reference_unchanged'):
                raise ValueError('Primary reference changed/missing')
            if int(sample['actor']['flags'], 16) & 0x400000:
                raise ValueError('Actor linked local input missing')
            actor = sample['actor']['world_matrix']
            active = sample['component_flags_u16'] >> 8 & 15
            operands = []
            for name in ('primary', 'transition') if active == 3 else ('primary',):
                choices = sources.get(json.dumps(signature(sample[name + '_clip']['tracks'], True)), [])
                if len(choices) != 1:
                    raise ValueError('Unique source required')
                key, source = choices[0]
                values, missing = channels(source, sample[name + '_clip']['tracks'])
                if missing or 'quaternion_xyzw' not in values.get(0, {}):
                    raise ValueError('Unsupported/incomplete slot0 channels')
                if name == 'primary':
                    reference = struct.unpack('<16fI', bytes.fromhex(sample['actor_reference_matrix_hex']))
                else:
                    header = bytes.fromhex(sample['transition_header_hex'])
                    if header[0x57] & 128:
                        raise ValueError('Transition blend suppressed')
                    reference = struct.unpack('<16fI', header[16:84])
                q = values[0]['quaternion_xyzw']
                basis = referenced_basis(q, reference[:16], reference[16], actor[:16], int(actor[16]))
                operands.append(dict(instance=name, source=key, rotation=q, reference=list(reference[:16]),
                    reference_flags=reference[16], actor=actor[:16], actor_flags=int(actor[16]), basis=basis))
            expected = operands[0]['basis']
            weight = None
            if active == 3:
                weight = sample['transition_clip']['tracks'][0]['auxiliary_f32']
                expected = rotation_matrix(blend_rotation(matrix_quaternion(operands[1]['basis']),
                                                          matrix_quaternion(operands[0]['basis']), weight))
            obj = next(obj for obj in sample['objects'] if obj['slot'] == 0)
            observed = obj['linked_local_matrix']
            error = max(abs(expected[i] - observed[i]) for i in (0, 1, 2, 4, 5, 6, 8, 9, 10))
            cases.append(dict(sample=sample['index'], active_slots=active, operands=operands,
                              weight=weight, observed=observed, maximum_error=error))
        except (ValueError, NotImplementedError) as error:
            skipped.append(dict(sample=sample['index'], reasons=[str(error)]))
    summary = {str(active): dict(checked=len(rows), matched=sum(r['maximum_error'] <= 1e-5 for r in rows),
                               maximum_error=max((r['maximum_error'] for r in rows), default=None))
               for active in (1, 3) for rows in [[r for r in cases if r['active_slots'] == active]]}
    result = dict(source_record=str(args.sequence), source_sha256=hashlib.sha256(raw).hexdigest(),
        cases=cases, skipped=skipped, summary=summary,
        limitations=['Observed matrices are sequential post-update inputs, not atomic callback entries.',
                     'Only slot0 reference basis and rotation blend compared; no complete pose claim.',
                     'Host quaternion/trig remains numerical; no error-based sample selection.'])
    path = report_path(args.sequence.stem + '-root-rotation.json')
    path.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(dict(report=str(path), summary=summary, skipped=len(skipped))))


if __name__ == '__main__':
    main()
