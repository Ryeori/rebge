"""Zero-delta publication relationship at observed clocks; not a frame replay."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from jade_trace_consistency import rejection_reasons
from match_sally_runtime_clip import signature
from project_paths import ASSET_ROOT, GHIDRA_RAW_ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sequence', type=Path)
    args = parser.parse_args()
    raw = args.sequence.read_bytes()
    identity_path=GHIDRA_RAW_ROOT/'stage43-refresh-identity-reference-20261009.json'
    identity_raw=identity_path.read_bytes()
    identity=struct.unpack('<16fI',bytes.fromhex(json.loads(identity_raw)['result']['structuredContent']['hex_data']))
    sources = {}
    for path in sorted((ASSET_ROOT/'animations/sally/local-samples').glob('*.json')):
        source = json.loads(path.read_text())
        sources.setdefault(json.dumps(signature(source['tracks'])), []).append((path.stem, source))
    cases, skipped = [], []
    for sample in json.loads(raw)['samples']:
        reasons = rejection_reasons(sample)
        if sample['component_flags_u16'] >> 8 & 15 != 1:
            reasons.append('transition_active')
        if not sample.get('actor_reference_unchanged'):
            reasons.append('reference_not_stable')
        if int(sample['actor']['flags'], 16) & 0x400000:
            reasons.append('linked_actor')
        choices = sources.get(json.dumps(signature(sample['primary_clip']['tracks'], True)), [])
        if len(choices) != 1:
            reasons.append('source_not_unique')
        if reasons:
            skipped.append(dict(sample=sample['index'], reasons=sorted(set(reasons))))
            continue
        key, source = choices[0]
        root_tracks = []
        for track, state in zip(source['tracks'][:2], sample['primary_clip']['tracks'][:2]):
            index = state['frame_index']
            if track['short1'] != 65535 or not state['track_flags'] & 0x8000:
                reasons.append('different_root_dispatch')
            if index >= len(track['frames'])-1 or not state['state_flags'] & 4:
                reasons.append('zero_delta_would_enter_or_reset')
            elif state['elapsed_seconds'] > track['frames'][index]['tick_raw']/60-struct.unpack('<f',struct.pack('<I',0x3727c5ac))[0]:
                reasons.append('zero_delta_would_cross_boundary')
            if any(f['flags'] & (0x20|0x800) for f in track['frames']):
                reasons.append('root_mirror_or_hold')
            if any(a['tick_raw'] != b['tick_raw'] or a['flags'] & ~4 != b['flags'] & ~4
                   for a,b in zip(track['frames'],state['frame_headers'])):
                reasons.append('runtime_source_frame_difference')
            root_tracks.append(dict(source=track,
                clock=dict(frames=state['frame_headers'],flags=state['track_flags'],
                           auxiliary_short=state['auxiliary_short_u16']),
                state=dict(index=index,elapsed=state['elapsed_seconds'],flags=state['state_flags'])))
        if reasons:
            skipped.append(dict(sample=sample['index'], reasons=sorted(set(reasons))))
            continue
        reference = struct.unpack('<16fI',bytes.fromhex(sample['actor_reference_matrix_hex']))
        cases.append(dict(sample=sample['index'],source_key=key,tracks=root_tracks,
            entry_gate=(sample.get('reference_entry_gate_u32') if 'reference_entry_gate_u32' in sample else
                        int(sample['reference_entry_manager_address'],16)&0xffffffff),
            gao_flags=int(sample['actor']['flags'],16),actor=sample['actor']['world_matrix'],
            reference=list(reference)))
    result = dict(source_sequence=str(args.sequence),source_sha256=hashlib.sha256(raw).hexdigest(),
        evaluation_reference=list(identity),evaluation_reference_record=str(identity_path),
        evaluation_reference_sha256=hashlib.sha256(identity_raw).hexdigest(),
        cases=cases,skipped=skipped,
        selection='Every qualified direct primary-only sample with entered nonterminal root clocks.',
        limitations=['Sequential post-frame reference and actor inputs; not callback-time proof.',
                     'Publication is explicitly enabled as a numerical hypothesis; runtime suppressor flags are not captured here.',
                     'Zero-delta evaluation only; no frame-to-frame reference/VM/entry chronology claim.',
                     'Observed actor supplies unwritten storage bytes; compare only the published basis and position.'])
    path=args.sequence.with_name(args.sequence.stem+'-root-pipeline.json')
    path.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(report=str(path),cases=len(cases),skipped=len(skipped))))


if __name__=='__main__':
    main()
