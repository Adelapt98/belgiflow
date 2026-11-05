"""Optional S3 publication. Uses the standard AWS credential chain."""
from pathlib import Path
from .storage import read_current


def upload(root,bucket,prefix='belgiflow/dashboard'):
    import boto3
    root=Path(root)
    read_current(root)
    digest=(root/'CURRENT').read_text(encoding='utf-8')
    client=boto3.client('s3')
    client.upload_file(str(root/f'{digest}.json'),bucket,f'{prefix}/{digest}.json')
    if (root/'index.html').exists():
        client.upload_file(str(root/'index.html'),bucket,f'{prefix}/index.html',ExtraArgs={'ContentType':'text/html'})
    client.put_object(Bucket=bucket,Key=f'{prefix}/CURRENT',Body=digest.encode(),ContentType='text/plain')
    return digest
