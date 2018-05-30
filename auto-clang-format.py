# !/usr/bin/env python

import BaseHTTPServer
import json
import subprocess
import threading

BITBUCKET_PORT = 2232
GITHUB_PORT = 2233
CLANG_FORMAT_DIFF_PATH = '/usr/local/Cellar/clang-format/2018-01-11/share/clang/clang-format-diff.py'
COMMIT_MESSAGE = '[AUTO] :triumph: clang-format'

# Run git -C {project_dir} diff HEAD^ HEAD | clang-format-diff -i -v -p1 -iregex {regex_pattern}
def run_clang_format(project_dir, regex_pattern):
    args0 = [
        'git',
        '--no-pager',
        'diff',
        'HEAD^',
        'HEAD'
    ]
    args1 = [
        'python',
        CLANG_FORMAT_DIFF_PATH,
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
    print 'full command line = %s' % (' '.join(args0 + ['|'] + args1))

    p0 = subprocess.Popen(args0, cwd=project_dir, stdout=subprocess.PIPE)
    # print 'result = %s' % p0.communicate()[0]

    # Pass output from git diff to clang-format-diff.
    p1 = subprocess.Popen(args1, cwd=project_dir, stdin=p0.stdout, stdout=subprocess.PIPE)
    p0.stdout.close()
    p0.wait()
    p1.wait()

    print 'clang-format-diff command line = %s' % subprocess.list2cmdline(args1)
    print 'result = %s' % p1.communicate()[0]

def parse_github_data(data):
    branch = data['ref'] # ref/heads/master or ref/heads/dev
    message = data['commits'][0]['message']
    name = data['repository']['full_name']
    return branch, message, name

def parse_bitbucket_data(data):
    branch = data['push']['changes'][0]['new']['name'] # master or dev
    message = data['push']['changes'][0]['new']['target']['message']
    name = data['repository']['full_name']
    return branch, message, name

def process_data(data, parser, branch, repository, project_dir, regex_pattern):
    parsed_branch, parsed_message, parsed_repository = parser(data)
    if branch not in parsed_branch:
        return

    if COMMIT_MESSAGE in parsed_message:
        return

    if parsed_repository != repository:
        return;

    # Perform: fetch, merge, format, stage, commit and push.
    subprocess.Popen(['git', 'fetch'], cwd=project_dir).wait()
    subprocess.Popen(['git', 'merge'], cwd=project_dir).wait()
    run_clang_format(project_dir, regex_pattern)
    subprocess.Popen(['git', 'add', '-A'], cwd=project_dir).wait()
    subprocess.Popen([
        'git',
        'commit',
        '-m',
        '\'%s\'' % COMMIT_MESSAGE
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

def run_server(port, callback):
    try:
        server = BaseHTTPServer.HTTPServer(('', port), make_handler_class(callback))
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down the web server'
        pass
    server.server_close()

def process_github_repo(data):
    process_data(data, parse_github_data, 'master', 'Senspark/ee-x', '/Volumes/DATA/Repository/senspark/ee-x', r'.*\.(cpp|hpp|h|mm|m)$')

def process_bitbucket_repo(data):
    # process_data(data, parse_bitbucket_data, 'enrevol/hook-test',         '/Volumes/DATA/Repository/enrevol/hook-test',         r'.*\.(cpp|hpp|h|mm|m)$')
    process_data(data, parse_bitbucket_data, 'master',  'senspark/gold-miner-vegas', '/Volumes/DATA/Repository/senspark/gold-miner-vegas', r'.*\.(cpp|hpp|h|mm|m)$')
    process_data(data, parse_bitbucket_data, 'develop', 'senspark/tienlen',          '/Volumes/DATA/Repository/senspark/gold-miner-vegas', r'.*\.(cpp|hpp|h|mm|m)$')

def run_github_server():
    return threading.Thread(target=run_server, args=(2233, process_github_repo))

def run_bitbucket_server():
    return threading.Thread(target=run_server, args=(2232, process_bitbucket_repo))

if __name__ == '__main__':
    t0 = run_github_server()
    t1 = run_bitbucket_server()
    t0.start()
    t1.start()
    t0.join()
    t1.join()
