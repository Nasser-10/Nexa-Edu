import json, urllib.request
BASE='http://127.0.0.1:11434'
MODEL='qwen2.5:7b'
print('Checking Ollama...')
try:
    with urllib.request.urlopen(BASE+'/api/tags', timeout=5) as r:
        data=json.load(r)
    models=[m.get('name') for m in data.get('models',[])]
    print('Ollama: OK')
    print('Models:', ', '.join(models) or 'NONE')
    if MODEL not in models:
        print(f'WARNING: {MODEL} is not installed.')
        print(f'Run: ollama pull {MODEL}')
        raise SystemExit(2)
    payload=json.dumps({'model':MODEL,'messages':[{'role':'user','content':'Reply with exactly: LOCAL AI OK'}],'stream':False}).encode()
    req=urllib.request.Request(BASE+'/api/chat',data=payload,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as r:
        out=json.load(r)
    print('Chat test:', out.get('message',{}).get('content','').strip())
except Exception as e:
    print('FAILED:', repr(e))
    raise SystemExit(1)
