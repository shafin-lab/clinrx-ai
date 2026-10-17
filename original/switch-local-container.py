from pathlib import Path
import subprocess,json,os
p=Path(__file__).resolve().parent
env={**os.environ,'DOCKER_CONFIG':str(p/'docker-client')}
base=['docker','--host','unix:///Users/mohammedshafiqshajahan/.colima/clinrx-review-28496c4/docker.sock']
def docker(*args):return subprocess.check_output(base+list(args),env=env)
old=json.loads(docker('inspect','clinrx-expanded-2539eb6'))[0]
assert old['State']['Running'] and old['Config']['Labels']['org.opencontainers.image.revision']=='2539eb61292456706b3c358443a8fdb7a6ece144'
(p/'previous-container-preserved.json').write_text(json.dumps(old,indent=2)+'\n')
image=json.loads(docker('image','inspect','clinrx-expanded-demo:d0f94dc-local'))[0]
assert image['Architecture']=='arm64' and image['Os']=='linux'
assert image['Config']['Labels']['org.opencontainers.image.revision']=='d0f94dc142a2d99246aa3f31c1f0ff4cd0fa1982'
assert image['Config']['Labels']['org.opencontainers.image.source-tree']=='384bee3150f0428156549962da1147382f2f03f9'
(p/'image-inspect.json').write_text(json.dumps(image,indent=2)+'\n')
docker('stop','clinrx-expanded-2539eb6')
try:
 result=docker('run','--detach','--name','clinrx-expanded-d0f94dc','--publish','127.0.0.1:5183:8080','--cap-drop','ALL','--security-opt','no-new-privileges','clinrx-expanded-demo:d0f94dc-local')
except Exception:
 docker('start','clinrx-expanded-2539eb6');raise
(p/'run-container-id.txt').write_bytes(result)
print('Started local d0f94dc container at 127.0.0.1:5183; previous container preserved and stopped.')
