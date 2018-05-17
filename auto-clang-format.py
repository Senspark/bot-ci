# !/usr/bin/env python

import BaseHTTPServer
import json
import subprocess

clang_format_diff_path = '/usr/local/Cellar/clang-format/2018-01-11/share/clang/clang-format-diff.py'

# Run git -C {project_dir} diff HEAD^ HEAD | clang-format-diff -i -v -p1 -iregex {regex_pattern}
def run_clang_format(project_dir, regex_pattern):
    args0 = [
        'git',
        'diff',
        'HEAD^',
        'HEAD'
    ]
    args1 = [
        'python',
        clang_format_diff_path,
        '-i',
        '-p',
        '1',
        '-iregex',
        regex_pattern,
        '-sort-includes',
        '-v',
        '-style',
        'file'
    ]
    print 'cwd = %s' % project_dir
    print ' '.join(args0 + ['|'] + args1)

    p0 = subprocess.Popen(args0, cwd=project_dir, stdout=subprocess.PIPE)
    p0.wait()

    p1 = subprocess.Popen(args1, cwd=project_dir, stdin=p0.stdout, stdout=subprocess.PIPE)
    p0.stdout.close()
    p1.wait()

    print 'command line = %s' % subprocess.list2cmdline(args1)
    print 'result = %s' % p1.communicate()[0]

def process_data(data, repository, project_dir, regex_pattern):
    ref = data['ref']
    if 'master' not in ref:
        return

    message = '[AUTO] :triumph: clang-format'
    ignored = True
    for commit in data['commits']:
        if not message in commit['message']:
            ignored = False
    if ignored:
        return

    repo_name = data['repository']['full_name']
    if repo_name != repository:
        return;

    subprocess.Popen(['git', 'fetch'], cwd=project_dir).wait()
    subprocess.Popen(['git', 'merge'], cwd=project_dir).wait()
    run_clang_format(project_dir, regex_pattern)
    subprocess.Popen(['git', 'add', '-A'], cwd=project_dir).wait()
    subprocess.Popen([
        'git',
        'commit',
        '-m',
        '\'%s\'' % message
    ], cwd=project_dir).wait()
    subprocess.Popen(['git', 'push'], cwd=project_dir).wait()

def make_handler_class(callback):
    class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler, object):
        def __init__(self, *args, **kwargs):
            super(MyHandler, self).__init__(*args, **kwargs)

        def _set_headers(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

        def do_GET(self):
            print 'do_GET'
            self._set_headers()

        def do_HEAD(self):
            print 'do_HEAD'
            self._set_headers()

        def do_POST(self):
            print 'do_POST'
            content_length = int(self.headers['Content-Length'])
            payload = self.rfile.read(content_length)
            data = json.loads(payload)

            print 'length = %d' % content_length
            callback(data)
            response = {}
            self._set_headers()
            self.wfile.write(json.dumps(response))

    return MyHandler

def run_server(callback):
    try:
        server = BaseHTTPServer.HTTPServer(('', 2233), make_handler_class(callback))
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down the web server'
        pass
    server.server_close()

if __name__ == '__main__':
    run_server(lambda data:
        process_data(data, 'Senspark/ee-x', '/Volumes/DATA/Repository/senspark/ee-x', r'.*\.(cpp|hpp|h|mm|m)$')
    )
