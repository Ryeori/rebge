"""Local-only preview server using the project's private asset library."""
import argparse,http.server,pathlib,urllib.parse
ap=argparse.ArgumentParser();ap.add_argument('--assets',required=True);ap.add_argument('--port',type=int,default=8181);ap.add_argument('--viewer',choices=['scene','pose'],default='scene');args=ap.parse_args()
root=pathlib.Path(args.assets).resolve();viewer=pathlib.Path(__file__).with_name('pose_viewer.html' if args.viewer=='pose' else 'scene_viewer.html')
class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self,path):
        path=urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        if path in ('/','/scene_viewer.html'):return str(viewer)
        if path.startswith('/assets/'):
            candidate=(root/path[8:]).resolve()
            if candidate.is_relative_to(root):return str(candidate)
        return str(root/'__not_found__')
print(f'http://127.0.0.1:{args.port}',flush=True)
http.server.ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
