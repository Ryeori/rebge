"""Root clock wraps/controller epoch candidates; not callback-entry proof."""
import argparse
import json
from pathlib import Path
from jade_trace_consistency import pair_candidate
from jade_animation_transition import f32
from project_paths import report_path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('sequence',type=Path);args=parser.parse_args()
    samples=json.loads(args.sequence.read_text())['samples'];events=[]
    for a,b in zip(samples,samples[1:]):
        if not pair_candidate(a,b)['candidate']:continue
        if a['primary_clip']['resource_address']!=b['primary_clip']['resource_address']:continue
        x,y=a['primary_clip']['tracks'],b['primary_clip']['tracks']
        if y[0]['elapsed_seconds']>=x[0]['elapsed_seconds']:continue
        speed=bytes.fromhex(b['primary_header_hex'])[2]
        delta=f32(f32(speed*b['delta_time'])/60)
        duration=f32(x[0]['frame_headers'][x[0]['frame_index']]['tick_raw']/60)
        candidate=f32(delta-f32(duration-x[0]['elapsed_seconds']))
        prefix=lambda s:bytes.fromhex(s['component_aa_b5_hex']) if 'component_aa_b5_hex' in s else None
        pa,pb=prefix(a),prefix(b)
        events.append(dict(before=a['index'],after=b['index'],speed=speed,effective_delta_candidate=delta,
            root_before=x[0]['elapsed_seconds'],root_after=y[0]['elapsed_seconds'],remaining_candidate=candidate,
            remaining_error=abs(candidate-y[0]['elapsed_seconds']),all_track_indices_zero=all(t['frame_index']==0 for t in y),
            phase_repeat_before=pa[3] if pa else None,phase_repeat_after=pb[3] if pb else None,
            component_delta_before=a.get('component_delta_b8'),component_delta_after=b.get('component_delta_b8')))
    result=dict(events=events,metadata_observed=all('component_aa_b5_hex' in s for s in samples),
        limitations=['Clock drop is a controller epoch candidate, not unique native call identification.',
                    'Residual candidate uses sampled global delta; no callback-entry or exact root restart proof.'])
    path=report_path(args.sequence.stem+'-clip-epochs.json');path.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(events=len(events),metadata_observed=result['metadata_observed'],maximum_remaining_error=max((e['remaining_error'] for e in events),default=None))))


if __name__=='__main__':main()
