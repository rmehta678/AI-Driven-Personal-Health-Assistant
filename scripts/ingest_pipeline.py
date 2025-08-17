from kfp import dsl
import kfp.components as comp

def ingest_component():
    return dsl.ContainerOp(
        name='ingest_whoop_data',
        image='python:3.9-slim',
        command=['python', '-c'],
        arguments=['import requests; print(requests.get("http://localhost:5000/whoop/ingest").text)']
    )

@dsl.pipeline(
    name='WHOOP Ingest Pipeline',
    description='Pipeline to ingest WHOOP data'
)
def whoop_pipeline():
    ingest_task = ingest_component()

if __name__ == '__main__':
    import kfp.compiler as compiler
    compiler.Compiler().compile(whoop_pipeline, 'ingest_pipeline.yaml')